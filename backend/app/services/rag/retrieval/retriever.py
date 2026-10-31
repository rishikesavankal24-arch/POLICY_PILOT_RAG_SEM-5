import uuid
from typing import Optional

from sqlalchemy import func, or_, text
from sqlalchemy.orm import Session

from app.db.models import (
    Policy,
    PolicyApplicability,
    PolicyChunk,
    PolicyStatus,
)
from app.db.session import SessionLocal
from app.services.rag.retrieval.embedding import PolicyEmbedder


class PolicyRetriever:
    def __init__(
        self,
        collection=None,
        embedder: Optional[PolicyEmbedder] = None,
    ):
        # collection parameter retained for backward compatibility
        self.embedder = embedder or PolicyEmbedder()

    def retrieve(
        self,
        query: str,
        top_k: int = 5,
        where: Optional[dict] = None,
        db: Optional[Session] = None,
    ) -> dict:
        if not isinstance(query, str) or not query.strip():
            raise ValueError("query must be a non-empty string")

        if not isinstance(top_k, int) or top_k <= 0:
            raise ValueError("top_k must be a positive integer")

        where_copy = dict(where) if where else {}

        db_session = db or where_copy.pop("_db", None)
        owns_session = False

        if db_session is None:
            db_session = SessionLocal()
            owns_session = True

        try:
            query_embedding = self.embedder.embed_text(query)

            distance_expr = PolicyChunk.embedding.cosine_distance(
                query_embedding
            ).label("distance")

            # ---------------------------------------------------------------
            # IMPORTANT RETRIEVAL INVARIANT
            #
            # Only retrieve chunks belonging to:
            #   1. ACTIVE policies
            #   2. The policy's CURRENT version
            #
            # This prevents stale/inactive policy versions from being
            # returned even if their embeddings still exist in pgvector.
            # ---------------------------------------------------------------
            q = (
                db_session.query(PolicyChunk, distance_expr)
                .join(
                    Policy,
                    Policy.id == PolicyChunk.policy_id,
                )
                .filter(
                    Policy.status == PolicyStatus.ACTIVE,
                    Policy.current_version_id
                    == PolicyChunk.policy_version_id,
                )
            )

            # ---------------------------------------------------------------
            # Process filters from the where-clause.
            # ---------------------------------------------------------------
            filters_to_apply = []

            if "$and" in where_copy:
                for clause in where_copy.get("$and", []):
                    if isinstance(clause, dict):
                        filters_to_apply.append(clause)
            else:
                filters_to_apply.append(where_copy)

            loan_type_value: Optional[str] = None

            for filter_dict in filters_to_apply:
                for key, value in filter_dict.items():

                    if not value or key == "_db":
                        continue

                    if key == "policy_id":
                        try:
                            q = q.filter(
                                PolicyChunk.policy_id
                                == uuid.UUID(str(value))
                            )
                        except (ValueError, AttributeError):
                            q = q.filter(
                                PolicyChunk.policy_id == str(value)
                            )

                    elif key == "policy_version_id":
                        try:
                            q = q.filter(
                                PolicyChunk.policy_version_id
                                == uuid.UUID(str(value))
                            )
                        except (ValueError, AttributeError):
                            q = q.filter(
                                PolicyChunk.policy_version_id == str(value)
                            )

                    elif key == "institution":
                        q = q.filter(
                            func.lower(PolicyChunk.institution)
                            == str(value).strip().lower()
                        )

                    elif key == "jurisdiction":
                        q = q.filter(
                            func.lower(PolicyChunk.jurisdiction)
                            == str(value).strip().lower()
                        )

                    elif key == "loan_type":
                        loan_type_value = (
                            str(value).strip().lower()
                        )

            # ---------------------------------------------------------------
            # APPLICABILITY FILTER
            #
            # A policy is eligible when:
            #
            #   - it has no applicability rows
            #       OR
            #   - it has an applicability row matching the requested
            #     loan type.
            #
            # This follows the same semantics used by the existing
            # PolicyApplicability / EmployeePolicyService logic.
            # ---------------------------------------------------------------
            if loan_type_value:
                q = q.filter(
                    or_(
                        ~Policy.applicabilities.any(),
                        Policy.applicabilities.any(
                            func.lower(
                                PolicyApplicability.loan_type
                            )
                            == loan_type_value
                        ),
                    )
                )

            # ---------------------------------------------------------------
            # Vector similarity ranking
            # ---------------------------------------------------------------
            q = (
                q.order_by(text("distance ASC"))
                .limit(top_k)
            )

            rows = q.all()

            # ---------------------------------------------------------------
            # Build evidence.
            #
            # PolicyApplicability is loaded separately per policy so that
            # evidence exposes the applicability context required by the
            # EvidenceContract.
            # ---------------------------------------------------------------
            evidence = []

            applicability_cache = {}

            for chunk, dist in rows:

                policy_id = chunk.policy_id

                if policy_id not in applicability_cache:
                    applicability_cache[policy_id] = (
                        db_session.query(PolicyApplicability)
                        .filter(
                            PolicyApplicability.policy_id
                            == policy_id
                        )
                        .all()
                    )

                applicability_rows = applicability_cache[policy_id]

                # -----------------------------------------------------------
                # A policy can have multiple applicability rows.
                #
                # For the evidence contract we expose the matching
                # applicability when a loan_type filter was requested.
                # Otherwise expose the first applicable context when one
                # exists.
                # -----------------------------------------------------------
                selected_applicability = None

                if applicability_rows:
                    if loan_type_value:
                        for applicability in applicability_rows:
                            if (
                                applicability.loan_type
                                and applicability.loan_type.strip().lower()
                                == loan_type_value
                            ):
                                selected_applicability = applicability
                                break

                    if selected_applicability is None:
                        selected_applicability = applicability_rows[0]

                source_url = chunk.source_url or chunk.source

                if (
                    not source_url
                    or not source_url.strip()
                ):
                    source_url = "policy.pdf"

                evidence.append(
                    {
                        "chunk_id": str(chunk.id),
                        "text": chunk.text,
                        "distance": float(dist),

                        "document_id": str(chunk.document_id),
                        "document": chunk.document,
                        "source": chunk.source,
                        "source_type": chunk.source_type,
                        "source_url": source_url,

                        "chapter": chunk.chapter or "",
                        "section": chunk.section or "",
                        "page": chunk.page,

                        "location": chunk.location or "",

                        "chunk_index": chunk.chunk_index,
                        "part_index": chunk.part_index,
                        "unit_index": chunk.unit_index,

                        "policy_id": str(chunk.policy_id),
                        "policy_version_id": str(
                            chunk.policy_version_id
                        ),

                        "version_number": (
                            chunk.version_number or ""
                        ),

                        "institution": (
                            chunk.institution
                            or (
                                selected_applicability.institution
                                if selected_applicability
                                else ""
                            )
                        ),

                        "jurisdiction": (
                            chunk.jurisdiction
                            or (
                                selected_applicability.jurisdiction
                                if selected_applicability
                                else ""
                            )
                        ),

                        "loan_type": (
                            selected_applicability.loan_type
                            if selected_applicability
                            else None
                        ),

                        "department": (
                            selected_applicability.department
                            if selected_applicability
                            else None
                        ),

                        "applicability_json": (
                            chunk.applicability_json or "[]"
                        ),

                        "effective_from": (
                            str(chunk.effective_from)
                            if chunk.effective_from
                            else ""
                        ),

                        "effective_to": (
                            str(chunk.effective_to)
                            if chunk.effective_to
                            else ""
                        ),

                        "file_hash": (
                            chunk.file_hash or ""
                        ),
                    }
                )

            return {
                "query": query,
                "results": evidence,
            }

        finally:
            if owns_session:
                db_session.close()
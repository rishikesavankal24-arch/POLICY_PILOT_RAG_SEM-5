import re
from typing import Optional

from sqlalchemy.orm import Session

from app.services.rag.adaptive.evaluator import EvidenceEvaluator
from app.services.rag.adaptive.query_rewriter import QueryRewriter
from app.services.rag.config.settings import (
    DEFAULT_TOP_K,
    SECOND_TOP_K,
    MAX_RETRIEVAL_ATTEMPTS,
)
from app.services.rag.schemas.evidence import EvidenceContract, PolicyEvidence


class AdaptivePolicyRetriever:
    """Retrieval-only adaptive controller; never makes a compliance decision."""

    def __init__(
        self,
        retriever,
        evaluator=None,
        query_rewriter=None,
        first_top_k: int = DEFAULT_TOP_K,
        second_top_k: int = SECOND_TOP_K,
        max_attempts: int = MAX_RETRIEVAL_ATTEMPTS,
    ):
        self.retriever = retriever
        self.evaluator = evaluator or EvidenceEvaluator()
        self.query_rewriter = query_rewriter or QueryRewriter()

        self.first_top_k = first_top_k
        self.second_top_k = second_top_k
        self.max_attempts = max_attempts

    def retrieve(
        self,
        query: str,
        where: dict | None = None,
        db: Optional[Session] = None,
    ) -> dict:
        if not isinstance(query, str) or not query.strip():
            raise ValueError("query must be a non-empty string")

        if self.max_attempts < 1:
            raise ValueError("max_attempts must be at least 1")

        trace = []

        first = self.retriever.retrieve(
            query=query,
            top_k=self.first_top_k,
            where=where,
            db=db,
        )

        evaluation1 = self.evaluator.evaluate(
            query=query,
            retrieval_result=first,
        )

        trace.append(
            self._trace(
                1,
                query,
                self.first_top_k,
                first,
                evaluation1,
                where,
            )
        )

        if evaluation1["evidence_status"] == "sufficient":
            return self._response(
                query,
                query,
                1,
                first,
                evaluation1,
                trace,
            )

        if self.max_attempts < 2:
            return self._response(
                query,
                query,
                1,
                first,
                evaluation1,
                trace,
            )

        rewritten = self.query_rewriter.rewrite(query)

        second = self.retriever.retrieve(
            query=rewritten,
            top_k=self.second_top_k,
            where=where,
            db=db,
        )

        evaluation2 = self.evaluator.evaluate(
            query=query,
            retrieval_result=second,
        )

        trace.append(
            self._trace(
                2,
                rewritten,
                self.second_top_k,
                second,
                evaluation2,
                where,
            )
        )

        return self._response(
            query,
            rewritten,
            2,
            second,
            evaluation2,
            trace,
        )

    def _response(
        self,
        original,
        final,
        attempts,
        result,
        evaluation,
        trace,
    ):
        evidence = []
        supporting_chunk_ids = {
            chunk_id
            for requirement in evaluation.get("requirement_details", [])
            for chunk_id in requirement.get("supporting_chunk_ids", [])
        }

        if evaluation["evidence_status"] == "sufficient":
            for item in result.get("results", []):
                if item.get("chunk_id") not in supporting_chunk_ids:
                    continue

                if self._substantive(item) and self._provenance(item):
                    evidence.append(
                        PolicyEvidence(
                            chunk_id=item["chunk_id"],
                            text=item["text"],
                            document=item["document"],
                            document_id=item["document_id"],
                            source=item["source"],
                            source_type=item["source_type"],
                            source_url=item["source_url"],

                            # Policy lineage
                            policy_id=item.get("policy_id"),
                            policy_version_id=item.get(
                                "policy_version_id"
                            ),
                            version_number=item.get(
                                "version_number"
                            ),

                            # Document location
                            chapter=item.get("chapter"),
                            section=item.get("section"),
                            page=self._page(item.get("page")),

                            # Retrieval
                            distance=item["distance"],

                            # Applicability / policy context
                            institution=item.get("institution"),
                            jurisdiction=item.get("jurisdiction"),
                            loan_type=item.get("loan_type"),
                            department=item.get("department"),

                            # Policy provenance / lifecycle
                            effective_from=item.get(
                                "effective_from"
                            ),
                            effective_to=item.get(
                                "effective_to"
                            ),
                            file_hash=item.get(
                                "file_hash"
                            ),
                        )
                    )

        contract = EvidenceContract(
            query=original,
            final_query=final,
            evidence_status=evaluation["evidence_status"],
            attempts=attempts,
            evidence=evidence,
            trace={
                "attempts": trace,
                "final_reason": evaluation["reason"],
                "covered_requirements": evaluation[
                    "covered_requirements"
                ],
                "missing_requirements": evaluation[
                    "missing_requirements"
                ],
            },
        )

        return contract.to_dict()

    @staticmethod
    def _page(value):
        if value is None:
            return None

        try:
            page = int(value)
        except (TypeError, ValueError):
            return None

        return page if page >= 1 else None

    @staticmethod
    def _substantive(item):
        text = str(item.get("text") or "").strip()

        if not text:
            return False

        normalized = re.sub(r"\s+", " ", text)

        if len(normalized) >= 100:
            return True

        policy_terms = (
            "must",
            "required",
            "requirement",
            "shall",
            "eligible",
            "eligibility",
            "applicable",
            "applicability",
            "permitted",
            "prohibited",
            "not allowed",
            "only if",
            "subject to",
            "documents",
            "document",
            "loan",
            "borrower",
            "applicant",
            "customer",
            "processing",
            "approval",
            "identity",
            "certificate",
        )

        lowered = normalized.lower()

        return (
            len(normalized) >= 35
            and any(term in lowered for term in policy_terms)
        )

    @staticmethod
    def _provenance(item):
        required = (
            "chunk_id",
            "text",
            "document_id",
            "document",
            "source",
            "source_type",
            "source_url",
            "policy_id",
            "policy_version_id",
        )

        return all(
            item.get(field) not in (None, "")
            for field in required
        )

    @staticmethod
    def _trace(
        attempt,
        query,
        top_k,
        result,
        evaluation,
        where,
    ):
        return {
            "attempt": attempt,
            "query": query,
            "top_k": top_k,
            "result_count": len(
                result.get("results", [])
            ),
            "evidence_status": evaluation[
                "evidence_status"
            ],
            "reason": evaluation["reason"],
            "covered_requirements": evaluation[
                "covered_requirements"
            ],
            "missing_requirements": evaluation[
                "missing_requirements"
            ],
            "where": where or {},
        }
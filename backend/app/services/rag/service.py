import json
from typing import Optional
from sqlalchemy.orm import Session

from app.db.session import SessionLocal
from app.services.m09_handoff_service import M09HandoffService
from app.services.rag.ingestion.parser import PolicyDocumentParser
from app.services.rag.ingestion.chunker import chunk_document
from app.services.rag.retrieval.indexer import PolicyVectorIndexer
from app.services.rag.retrieval.embedding import PolicyEmbedder
from app.services.rag.retrieval.retriever import PolicyRetriever
from app.services.rag.adaptive.adaptive_retriever import AdaptivePolicyRetriever


class RAGService:
    """Application boundary between authoritative PolicyPilot policy data and PostgreSQL RAG."""
    def __init__(self):
        self.indexer = PolicyVectorIndexer()
        self.retriever = AdaptivePolicyRetriever(
            PolicyRetriever(embedder=self.indexer.embedder)
        )

    @staticmethod
    def _chunk_metadata(handoff):
        return {
            "policy_id": handoff.policy.policy_id,
            "policy_version_id": handoff.version.policy_version_id,
            "version_number": handoff.version.version_number,
            "institution": handoff.policy.institution,
            "jurisdiction": handoff.policy.jurisdiction,
            "applicability": [a.model_dump() for a in handoff.applicabilities],
            "effective_from": handoff.version.effective_from,
            "effective_to": handoff.version.effective_to,
            "file_hash": handoff.version.file_hash,
        }

    def ingest_active_policy(self, db: Session, policy_id: str) -> dict:
        handoff = M09HandoffService.get_policy_version_handoff_payload(db, policy_id)
        source_path, version = M09HandoffService.get_policy_version_source_file(db, policy_id)
        if str(version.id) != handoff.version.policy_version_id:
            raise ValueError("M09 handoff version does not match source version")

        pages = PolicyDocumentParser.extract_pages(source_path)
        chunks = []
        for page in pages:
            source_url = handoff.version.file_url or handoff.source_filename
            page_chunks = chunk_document(
                text=page["text"],
                document_id=handoff.version.policy_version_id,
                document=handoff.policy.title,
                source=handoff.source_filename,
                source_type="policy_pdf",
                source_url=source_url,
            )
            for chunk in page_chunks:
                chunk["page"] = page["page"]
                chunk.update(self._chunk_metadata(handoff))
                chunks.append(chunk)

        count = self.indexer.replace_policy_version(db=db, policy_id=handoff.policy.policy_id, chunks=chunks)
        return {
            "policy_id": handoff.policy.policy_id,
            "policy_version_id": handoff.version.policy_version_id,
            "version_number": handoff.version.version_number,
            "indexed_chunks": count,
            "source_filename": handoff.source_filename
        }

    def remove_policy(self, policy_id_or_db, policy_id: Optional[str] = None):
        if isinstance(policy_id_or_db, (str, type(None))) and policy_id is None:
            target_policy_id = policy_id_or_db
            db_sess = None
        elif isinstance(policy_id_or_db, Session):
            db_sess = policy_id_or_db
            target_policy_id = policy_id
        else:
            target_policy_id = str(policy_id_or_db)
            db_sess = None

        if db_sess is None:
            session = SessionLocal()
            try:
                self.indexer.remove_policy(db=session, policy_id=target_policy_id)
            finally:
                session.close()
        else:
            self.indexer.remove_policy(db=db_sess, policy_id=target_policy_id)

        return {"policy_id": str(target_policy_id), "removed": True}

    def query(
        self,
        query: str,
        policy_id: Optional[str] = None,
        institution: Optional[str] = None,
        jurisdiction: Optional[str] = None,
        loan_type: Optional[str] = None,
        db: Optional[Session] = None
    ) -> dict:
        """
        Retrieve policy evidence for a query, optionally constrained by
        applicability context (institution, jurisdiction, loan_type).

        Applicability filtering is deterministic relational logic applied
        BEFORE vector similarity scoring.  The caller must derive these values
        from authoritative application/policy data, not from raw user input.

        Filter semantics:
          institution  — matched against PolicyChunk.institution (exact, case-sensitive)
          jurisdiction — matched against PolicyChunk.jurisdiction (exact, case-sensitive)
          loan_type    — matched against PolicyApplicability.loan_type (case-insensitive);
                         policies with no applicability rows are considered universal
                         and always pass this filter.
        """
        where = {}
        if db is not None:
            where["_db"] = db

        clauses = []
        for key, value in (
            ("policy_id", policy_id),
            ("institution", institution),
            ("jurisdiction", jurisdiction),
            ("loan_type", loan_type),
        ):
            if value:
                clauses.append({key: value})

        if len(clauses) == 1:
            where.update(clauses[0])
        elif clauses:
            where["$and"] = clauses

        return self.retriever.retrieve(query, where=where)

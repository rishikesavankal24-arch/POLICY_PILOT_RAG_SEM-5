import json
import uuid
from typing import Optional
from sqlalchemy.orm import Session

from app.db.models import PolicyChunk
from app.services.rag.retrieval.embedding import PolicyEmbedder


def build_metadata(chunk: dict) -> dict:
    """Build metadata structure preserving authoritative M08/M09 lineage."""
    return {
        "document_id": str(chunk["document_id"]),
        "document": str(chunk["document"]),
        "source": str(chunk["source"]),
        "source_type": str(chunk.get("source_type", "policy_pdf")),
        "source_url": str(chunk.get("source_url") or chunk["source"]),
        "chapter": str(chunk.get("chapter") or ""),
        "section": str(chunk.get("section") or ""),
        "page": str(chunk.get("page") or ""),
        "location": str(chunk.get("location") or ""),
        "chunk_index": int(chunk["chunk_index"]),
        "part_index": int(chunk["part_index"]),
        "unit_index": int(chunk["unit_index"]),
        "policy_id": str(chunk["policy_id"]),
        "policy_version_id": str(chunk["policy_version_id"]),
        "version_number": str(chunk.get("version_number") or ""),
        "institution": str(chunk.get("institution") or ""),
        "jurisdiction": str(chunk.get("jurisdiction") or ""),
        "applicability_json": json.dumps(chunk.get("applicability", []), default=str),
        "effective_from": str(chunk.get("effective_from") or ""),
        "effective_to": str(chunk.get("effective_to") or ""),
        "file_hash": str(chunk.get("file_hash") or ""),
    }


class PolicyVectorIndexer:
    def __init__(self, embedder: Optional[PolicyEmbedder] = None):
        self.embedder = embedder or PolicyEmbedder()

    def replace_policy_version(self, db: Session, policy_id: str, chunks: list[dict]) -> int:
        """
        Transactional index replacement in PostgreSQL policy_chunks table.
        Prepares embeddings first; only mutates DB if embedding generation succeeds.
        """
        if not isinstance(policy_id, (str, uuid.UUID)):
            raise TypeError("policy_id must be a string or UUID")

        policy_uuid = uuid.UUID(str(policy_id))

        if not chunks:
            db.query(PolicyChunk).filter(PolicyChunk.policy_id == policy_uuid).delete(synchronize_session=False)
            db.commit()
            return 0

        texts = [chunk["text"] for chunk in chunks]
        embeddings = self.embedder.embed_texts(texts)

        chunk_objects = []
        for chunk, emb in zip(chunks, embeddings):
            source_url = str(chunk.get("source_url") or chunk.get("source") or "policy.pdf")

            page_val = chunk.get("page")
            if isinstance(page_val, str) and page_val.strip().isdigit():
                page_int = int(page_val.strip())
            elif isinstance(page_val, int) and not isinstance(page_val, bool):
                page_int = page_val
            else:
                page_int = None

            chunk_obj = PolicyChunk(
                id=str(chunk["chunk_id"]),
                policy_id=uuid.UUID(str(chunk["policy_id"])),
                policy_version_id=uuid.UUID(str(chunk["policy_version_id"])),
                chunk_index=int(chunk["chunk_index"]),
                part_index=int(chunk["part_index"]),
                unit_index=int(chunk["unit_index"]),
                text=str(chunk["text"]),
                document_id=str(chunk["document_id"]),
                document=str(chunk["document"]),
                source=str(chunk["source"]),
                source_type=str(chunk.get("source_type", "policy_pdf")),
                source_url=source_url,
                chapter=str(chunk.get("chapter") or ""),
                section=str(chunk.get("section") or ""),
                page=page_int,
                location=str(chunk.get("location") or ""),
                version_number=str(chunk.get("version_number") or ""),
                institution=str(chunk.get("institution") or ""),
                jurisdiction=str(chunk.get("jurisdiction") or ""),
                applicability_json=json.dumps(chunk.get("applicability", []), default=str) if isinstance(chunk.get("applicability"), (list, dict)) else str(chunk.get("applicability") or ""),
                effective_from=chunk.get("effective_from") if not isinstance(chunk.get("effective_from"), str) else None,
                effective_to=chunk.get("effective_to") if not isinstance(chunk.get("effective_to"), str) else None,
                file_hash=str(chunk.get("file_hash") or ""),
                embedding=emb,
            )
            chunk_objects.append(chunk_obj)

        # Transactional replacement
        db.query(PolicyChunk).filter(PolicyChunk.policy_id == policy_uuid).delete(synchronize_session=False)
        db.add_all(chunk_objects)
        db.commit()

        return len(chunk_objects)

    def remove_policy(self, db: Session, policy_id: str) -> None:
        policy_uuid = uuid.UUID(str(policy_id))
        db.query(PolicyChunk).filter(PolicyChunk.policy_id == policy_uuid).delete(synchronize_session=False)
        db.commit()

from datetime import datetime, timezone
from pathlib import Path
import shutil
import uuid

from app.db.models import Policy, PolicyStatus, PolicyChunk
from app.db.session import SessionLocal
from app.services.policy_file_service import PolicyFileService
from app.services.policy_lifecycle_service import PolicyLifecycleService
from app.services.rag.service import RAGService

PDF_PATH = Path(__file__).resolve().parent / "test_data" / "SCHEME16012026_A.pdf"
QUERY = "What is the purpose of the RBI Integrated Ombudsman Scheme?"


def main():
    if not PDF_PATH.exists():
        raise FileNotFoundError(f"Missing PDF: {PDF_PATH}")

    db = SessionLocal()
    policy = None
    source_path = None

    try:
        policy_id = uuid.uuid4()
        policy_code = f"LIVE-RAG-REAL-{policy_id.hex[:10].upper()}"

        policy = Policy(
            id=policy_id,
            policy_code=policy_code,
            title="RBI Integrated Ombudsman Scheme 2026 - RAG E2E Test",
            description="Temporary local end-to-end RAG verification using the real RBI 2026 Scheme PDF.",
            category="Regulatory",
            policy_type="External Policy",
            status=PolicyStatus.DRAFT,
            institution="RBI",
            jurisdiction="IN",
        )
        db.add(policy)
        db.commit()
        db.refresh(policy)

        pdf_bytes = PDF_PATH.read_bytes()
        version = PolicyFileService.attach_policy_version_document(
            db=db,
            policy_id=policy.id,
            filename=PDF_PATH.name,
            file_bytes=pdf_bytes,
            changelog="Temporary RAG E2E test using RBI Integrated Ombudsman Scheme 2026.",
            effective_from=datetime(2026, 7, 1, tzinfo=timezone.utc),
        )

        PolicyLifecycleService.publish_policy(
            db=db,
            policy_id=policy.id,
            version_id=version.id,
        )
        PolicyLifecycleService.activate_policy_version(
            db=db,
            policy_id=policy.id,
            version_id=version.id,
        )
        db.refresh(policy)

        print(f"POLICY_ID={policy.id}")
        print(f"POLICY_VERSION_ID={version.id}")
        print(f"STATUS={policy.status.value}")
        print(f"CURRENT_VERSION={policy.current_version_id}")

        rag = RAGService()
        ingestion = rag.ingest_active_policy(db=db, policy_id=str(policy.id))
        print(f"INGESTION={ingestion}")

        chunk_count = db.query(PolicyChunk).filter(
            PolicyChunk.policy_id == policy.id,
            PolicyChunk.policy_version_id == version.id,
        ).count()
        print(f"CHUNKS={chunk_count}")

        result = rag.query(
            query=QUERY,
            policy_id=str(policy.id),
            institution="RBI",
            jurisdiction="IN",
            db=db,
        )
        print(f"EVIDENCE_STATUS={result.get('evidence_status')}")
        print(f"EVIDENCE_COUNT={len(result.get('evidence') or [])}")
        print("CUSTOMER_SAFE_RESPONSE=" + str(result.get("customer_safe_response", "")))
        if result.get("evidence"):
            first = result["evidence"][0]
            print("FIRST_EVIDENCE_TEXT=" + str(first.get("text", "")))
            print("FIRST_EVIDENCE_PAGE=" + str(first.get("page")))
            print("FIRST_EVIDENCE_VERSION=" + str(first.get("version_number")))

        if result.get("evidence_status") != "sufficient" or not result.get("evidence"):
            raise RuntimeError("RAG did not return sufficient evidence for the real RBI PDF.")

        print("RAG_REAL_PDF_E2E=PASSED")

    finally:
        if policy is not None:
            try:
                db.query(PolicyChunk).filter(PolicyChunk.policy_id == policy.id).delete(synchronize_session=False)
                db.commit()

                db.refresh(policy)
                policy.current_version_id = None
                db.commit()

                db.delete(policy)
                db.commit()
            except Exception as cleanup_error:
                db.rollback()
                print(f"CLEANUP_WARNING={cleanup_error}")

            # PolicyFileService stores documents under policies/<policy_id>/<version_id>/.
            # Remove the temporary policy storage folder after DB cleanup.
            try:
                storage_base = PolicyFileService.get_storage_base()
                temp_policy_dir = Path(storage_base) / str(policy.id)
                if temp_policy_dir.exists():
                    shutil.rmtree(temp_policy_dir, ignore_errors=True)
            except Exception as storage_error:
                print(f"STORAGE_CLEANUP_WARNING={storage_error}")

        db.close()


if __name__ == "__main__":
    main()

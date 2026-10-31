"""
M08 -> M09 -> RAG integration test.

Validates that an ACTIVE policy can switch from V1 to V2 while remaining
ACTIVE, and that M09 and RAG immediately follow the new current version.
"""

import shutil
import uuid
from datetime import datetime, timezone, timedelta

import pytest

import app.services.policy_file_service as policy_file_service

from app.db.session import SessionLocal
from app.db.models import (
    Policy,
    PolicyVersion,
    PolicyStatus,
)
from app.services.policy_file_service import PolicyFileService
from app.services.policy_lifecycle_service import PolicyLifecycleService
from app.services.m09_handoff_service import M09HandoffService
from app.services.rag.service import RAGService

from tests.pdf_fixtures import make_test_pdf_bytes


@pytest.fixture
def test_storage(tmp_path):
    storage_dir = tmp_path / "policies"
    storage_dir.mkdir(parents=True, exist_ok=True)

    yield storage_dir

    if storage_dir.exists():
        shutil.rmtree(storage_dir, ignore_errors=True)


@pytest.fixture
def db():
    session = SessionLocal()

    try:
        yield session

    finally:
        session.rollback()

        test_policies = session.query(Policy).filter(
            Policy.policy_code.like("POL-M09-RAG-%")
        ).all()

        for policy in test_policies:
            policy.current_version_id = None

        session.commit()

        for policy in test_policies:
            session.query(PolicyVersion).filter(
                PolicyVersion.policy_id == policy.id
            ).delete(synchronize_session=False)

            session.delete(policy)

        session.commit()
        session.close()


def _create_policy(db, storage_dir):
    policy_id = uuid.uuid4()

    policy = Policy(
        id=policy_id,
        policy_code=f"POL-M09-RAG-{policy_id.hex[:8].upper()}",
        title="M08 M09 RAG Version Switch Test",
        description="Integration test for active policy version switching",
        category="Lending",
        status=PolicyStatus.DRAFT,
        institution="TEST_BANK",
        jurisdiction="IN",
    )

    db.add(policy)
    db.commit()
    db.refresh(policy)

    now = datetime.now(timezone.utc)

    v1_pdf = make_test_pdf_bytes(
        page_count=1,
        text=(
            "VERSION ONE POLICY REQUIREMENT. "
            "Loan applications must include a vehicle registration certificate."
        ),
    )

    v1 = PolicyFileService.attach_policy_version_document(
        db=db,
        policy_id=policy.id,
        filename="m09_rag_v1.pdf",
        file_bytes=v1_pdf,
        changelog="Initial policy version",
        effective_from=now,
        effective_to=now + timedelta(days=365),
        storage_dir=storage_dir,
    )

    return policy, v1


def test_active_version_switch_flows_through_m09_and_rag(
    db,
    test_storage,
    monkeypatch,
):
    """
    Full lifecycle:

    DRAFT
      -> PUBLISHED
      -> ACTIVE V1
      -> attach V2
      -> ACTIVE V2
      -> M09 resolves V2
      -> RAG ingests V2
      -> RAG retrieves V2 evidence
    """

    # ------------------------------------------------------------------
    # Test storage alignment
    # ------------------------------------------------------------------
    # M08 writes the test policy documents into pytest's isolated
    # temporary storage using storage_dir=test_storage.
    #
    # M09 resolves policy files through PolicyFileService without
    # explicitly receiving storage_dir, so it falls back to the
    # module-level DEFAULT_POLICY_STORAGE_DIR.
    #
    # Point that default at the same isolated directory for this test.
    # monkeypatch automatically restores the original value after the test.
    # ------------------------------------------------------------------

    monkeypatch.setattr(
        policy_file_service,
        "DEFAULT_POLICY_STORAGE_DIR",
        test_storage,
    )

    # ------------------------------------------------------------------
    # 1. Create and activate V1
    # ------------------------------------------------------------------

    policy, v1 = _create_policy(db, test_storage)

    PolicyLifecycleService.publish_policy(
        db,
        policy.id,
    )

    PolicyLifecycleService.activate_policy_version(
        db,
        policy.id,
        version_id=v1.id,
    )

    db.refresh(policy)

    assert policy.status == PolicyStatus.ACTIVE
    assert policy.current_version_id == v1.id

    # ------------------------------------------------------------------
    # 2. M09 initially sees V1
    # ------------------------------------------------------------------

    handoff_v1 = M09HandoffService.get_policy_version_handoff_payload(
        db=db,
        policy_id=policy.id,
    )

    assert handoff_v1.policy.status == "ACTIVE"
    assert handoff_v1.version.policy_version_id == str(v1.id)
    assert handoff_v1.version.version_number == "1"
    assert handoff_v1.source_filename == "m09_rag_v1.pdf"

    source_path_v1, bound_v1 = (
        M09HandoffService.get_policy_version_source_file(
            db=db,
            policy_id=policy.id,
        )
    )

    assert bound_v1.id == v1.id
    assert source_path_v1.name == "m09_rag_v1.pdf"

    # ------------------------------------------------------------------
    # 3. Attach V2
    # ------------------------------------------------------------------

    now = datetime.now(timezone.utc)

    v2_pdf = make_test_pdf_bytes(
        page_count=1,
        text=(
            "VERSION TWO POLICY REQUIREMENT. "
            "For all vehicle loan applications, the applicant must provide "
            "a valid vehicle insurance certificate before the loan can be "
            "processed. The insurance certificate must correspond to the "
            "vehicle identified in the loan application."
        ),
    )

    v2 = PolicyFileService.attach_policy_version_document(
        db=db,
        policy_id=policy.id,
        filename="m09_rag_v2.pdf",
        file_bytes=v2_pdf,
        changelog="Updated vehicle-document requirement",
        effective_from=now + timedelta(days=1),
        effective_to=now + timedelta(days=366),
        storage_dir=test_storage,
    )

    db.refresh(policy)

    # Uploading a version alone must NOT change the active current version.
    assert policy.status == PolicyStatus.ACTIVE
    assert policy.current_version_id == v1.id

    # ------------------------------------------------------------------
    # 4. Activate V2 while keeping the policy ACTIVE
    # ------------------------------------------------------------------

    activated = PolicyLifecycleService.activate_policy_version(
        db,
        policy.id,
        version_id=v2.id,
    )

    assert activated.status == PolicyStatus.ACTIVE
    assert activated.current_version_id == v2.id

    db.refresh(policy)

    assert policy.status == PolicyStatus.ACTIVE
    assert policy.current_version_id == v2.id

    # V1 still exists as historical version.
    v1_recheck = db.query(PolicyVersion).filter(
        PolicyVersion.id == v1.id
    ).first()

    assert v1_recheck is not None
    assert v1_recheck.version_number == "1"

    # ------------------------------------------------------------------
    # 5. M09 must now resolve V2, not V1
    # ------------------------------------------------------------------

    handoff_v2 = M09HandoffService.get_policy_version_handoff_payload(
        db=db,
        policy_id=policy.id,
    )

    assert handoff_v2.policy.status == "ACTIVE"
    assert handoff_v2.version.policy_version_id == str(v2.id)
    assert handoff_v2.version.policy_id == str(policy.id)
    assert handoff_v2.version.version_number == "2"
    assert handoff_v2.source_filename == "m09_rag_v2.pdf"

    source_path_v2, bound_v2 = (
        M09HandoffService.get_policy_version_source_file(
            db=db,
            policy_id=policy.id,
        )
    )

    assert bound_v2.id == v2.id
    assert source_path_v2.name == "m09_rag_v2.pdf"

    # ------------------------------------------------------------------
    # 6. RAG ingestion must use M09's current V2
    # ------------------------------------------------------------------

    rag = RAGService()

    ingestion_result = rag.ingest_active_policy(
        db=db,
        policy_id=policy.id,
    )

    assert ingestion_result is not None

    # The exact return shape can evolve, so the authoritative verification
    # below is performed through retrieval metadata.

    # ------------------------------------------------------------------
    # 7. Query RAG for the V2-only requirement
    # ------------------------------------------------------------------

    results = rag.query(
        query="What vehicle document must the loan application include?",
        policy_id=str(policy.id),
        institution="TEST_BANK",
        jurisdiction="IN",
    )

    assert results is not None
    assert results["evidence_status"] == "sufficient"
    assert results["evidence"]

    evidence = results["evidence"]

    # ------------------------------------------------------------------
    # 8. Every returned evidence item must belong to V2
    # ------------------------------------------------------------------

    assert all(
        item["policy_version_id"] == str(v2.id)
        for item in evidence
    )

    # ------------------------------------------------------------------
    # 9. V2-specific content must be retrievable
    # ------------------------------------------------------------------

    combined_text = " ".join(
        item["text"].lower()
        for item in evidence
    )

    assert "insurance certificate" in combined_text

    # ------------------------------------------------------------------
    # 10. V1-specific requirement must not be returned
    # ------------------------------------------------------------------

    assert "registration certificate" not in combined_text
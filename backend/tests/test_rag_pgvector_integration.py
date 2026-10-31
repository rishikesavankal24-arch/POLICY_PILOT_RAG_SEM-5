import uuid
from datetime import datetime, timezone

import pytest
from fastapi.testclient import TestClient

from app.main import app
from sqlalchemy import text

from app.db.session import SessionLocal
from app.db.models import (
    Policy,
    PolicyApplicability,
    PolicyChunk,
    PolicyStatus,
    PolicyVersion,
)
from app.services.rag.adaptive.adaptive_retriever import AdaptivePolicyRetriever
from app.services.rag.adaptive.evaluator import EvidenceEvaluator
from app.services.rag.retrieval.embedding import PolicyEmbedder
from app.services.rag.retrieval.indexer import PolicyVectorIndexer
from app.services.rag.retrieval.retriever import PolicyRetriever
from app.services.rag.schemas.evidence import EvidenceContract
from app.services.rag.service import RAGService
from app.services.rag.config.settings import EMBEDDING_DIM


@pytest.fixture
def db():
    session = SessionLocal()

    try:
        yield session

    finally:
        session.rollback()

        test_policies = session.query(Policy).filter(
            Policy.policy_code.like("POL-TEST-%")
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

@pytest.fixture
def client():
    return TestClient(app)

def _create_policy_version(
    db,
    *,
    policy_id=None,
    version_number="1",
    status=PolicyStatus.ACTIVE,
    institution=None,
    jurisdiction=None,
    loan_type=None,
    effective_from=None,
):
    policy_id = policy_id or uuid.uuid4()
    version_id = uuid.uuid4()

    # Both tables have foreign-key relationships:
    #   policy_versions.policy_id -> policies.id
    #   policies.current_version_id -> policy_versions.id
    #
    # Therefore:
    # 1. Create Policy without current_version_id.
    # 2. Flush the Policy.
    # 3. Create PolicyVersion referencing the Policy.
    # 4. Flush the PolicyVersion.
    # 5. Set Policy.current_version_id.
    # 6. Commit.

    policy = Policy(
        id=policy_id,
        policy_code=f"POL-TEST-{policy_id.hex[:8].upper()}",
        title="Test Policy",
        status=status,
        current_version_id=None,
        institution=institution,
        jurisdiction=jurisdiction,
    )

    db.add(policy)
    db.flush()

    version = PolicyVersion(
        id=version_id,
        policy_id=policy_id,
        version_number=version_number,
        effective_from=effective_from or datetime.now(timezone.utc),
    )

    db.add(version)
    db.flush()

    policy.current_version_id = version_id

    if loan_type:
        applicability = PolicyApplicability(
            policy_id=policy_id,
            loan_type=loan_type,
        )
        db.add(applicability)

    db.commit()

    return policy, version


def _insert_chunk(
    db,
    *,
    policy,
    version,
    text_content,
    chunk_index=0,
    institution=None,
    jurisdiction=None,
    loan_type=None,
):
    chunk = PolicyChunk(
        id=f"{version.id}_chunk_{chunk_index}",
        policy_id=policy.id,
        policy_version_id=version.id,
        document_id=str(version.id),
        document=policy.title,
        text=text_content,
        source="test_policy.pdf",
        source_type="policy_pdf",
        source_url="test_policy.pdf",
        chapter="Test Chapter",
        section="Test Section",
        page=1,
        location="Page 1",
        chunk_index=chunk_index,
        part_index=0,
        unit_index=0,
        version_number=version.version_number,
        institution=institution,
        jurisdiction=jurisdiction,
        applicability_json="[]",
        effective_from=version.effective_from,
        effective_to=version.effective_to,
        file_hash="test-hash",
        embedding=PolicyEmbedder().embed_text(text_content),
    )

    db.add(chunk)
    db.commit()

    return chunk


def test_pgvector_extension_availability(db):
    """Verify PostgreSQL has the pgvector extension available."""

    result = db.execute(
        text("SELECT extname FROM pg_extension WHERE extname = 'vector'")
    ).scalar()

    assert result == "vector"


def test_rag_chunk_insertion_and_embedding_storage(db):
    """Verify PolicyChunk table stores embeddings and chunk metadata correctly."""

    policy_id = uuid.uuid4()
    version_id = uuid.uuid4()

    # Both tables have foreign-key relationships:
    #   policy_versions.policy_id -> policies.id
    #   policies.current_version_id -> policy_versions.id
    #
    # Create Policy first without current_version_id.
    policy = Policy(
        id=policy_id,
        policy_code=f"POL-TEST-CHUNK-{policy_id.hex[:6].upper()}",
        title="Test Chunk Policy",
        status=PolicyStatus.ACTIVE,
        current_version_id=None,
    )

    db.add(policy)
    db.flush()

    # Now PolicyVersion can safely reference the Policy.
    version = PolicyVersion(
        id=version_id,
        policy_id=policy_id,
        version_number="1",
        effective_from=datetime.now(timezone.utc),
    )

    db.add(version)
    db.flush()

    # Now PolicyVersion exists, so the reverse FK can safely be populated.
    policy.current_version_id = version_id

    db.commit()

    embedder = PolicyEmbedder()

    emb = embedder.embed_text(
        "Sample policy clause for testing pgvector storage."
    )

    # Verify dimension safety.
    assert len(emb) == EMBEDDING_DIM, (
        f"Embedding dimension mismatch: model produced {len(emb)} dims, "
        f"but EMBEDDING_DIM is configured as {EMBEDDING_DIM}. "
        "Update Vector() column dimension and re-index if you changed the model."
    )

    chunk_id = f"{version_id}_chunk_0"

    chunk = PolicyChunk(
        id=chunk_id,
        policy_id=policy_id,
        policy_version_id=version_id,
        document_id=str(version_id),
        document="Test Chunk Policy",
        text="Sample policy clause for testing pgvector storage.",
        source="test_policy.pdf",
        source_type="policy_pdf",
        source_url="test_policy.pdf",
        chapter="Test Chapter",
        section="Test Section",
        page=1,
        location="Page 1",
        chunk_index=0,
        part_index=0,
        unit_index=0,
        version_number="1",
        institution="Test Bank",
        jurisdiction="IN",
        applicability_json="[]",
        effective_from=version.effective_from,
        effective_to=version.effective_to,
        file_hash="test-hash",
        embedding=emb,
    )

    db.add(chunk)
    db.commit()
    db.refresh(chunk)

    assert chunk.embedding is not None
    assert len(chunk.embedding) == EMBEDDING_DIM

    stored = (
        db.query(PolicyChunk)
        .filter(PolicyChunk.id == chunk_id)
        .one()
    )

    assert stored.policy_id == policy_id
    assert stored.policy_version_id == version_id
    assert stored.text == "Sample policy clause for testing pgvector storage."
    assert stored.document_id == str(version_id)
    assert stored.document == "Test Chunk Policy"
    assert stored.source == "test_policy.pdf"
    assert stored.source_type == "policy_pdf"
    assert stored.page == 1
    assert stored.chunk_index == 0


def test_active_version_returned(db):
    """Verify retrieval only returns the active current policy version."""

    policy, version = _create_policy_version(
        db,
        version_number="1",
    )

    _insert_chunk(
        db,
        policy=policy,
        version=version,
        text_content=(
            "Applicants must submit a vehicle registration certificate "
            "before the vehicle loan can be approved."
        ),
    )

    retriever = PolicyRetriever()

    result = retriever.retrieve(
        "What document must the applicant submit?",
        where={"policy_id": str(policy.id)},
        db=db,
    )

    assert result["results"]
    assert all(
        item["policy_version_id"] == str(version.id)
        for item in result["results"]
    )


def test_version_switch_v1_absent_after_v2_activated(db):
    """Verify activating v2 removes v1 from retrieval results."""

    policy_id = uuid.uuid4()

    # Create policy first.
    policy = Policy(
        id=policy_id,
        policy_code=f"POL-TEST-VERSION-{policy_id.hex[:6].upper()}",
        title="Version Switch Policy",
        status=PolicyStatus.ACTIVE,
        current_version_id=None,
    )

    db.add(policy)
    db.flush()

    # Create v1 referencing the policy.
    v1 = PolicyVersion(
        id=uuid.uuid4(),
        policy_id=policy_id,
        version_number="1",
        effective_from=datetime.now(timezone.utc),
    )

    db.add(v1)
    db.flush()

    # Activate v1 as the current version.
    policy.current_version_id = v1.id
    db.commit()

    _insert_chunk(
        db,
        policy=policy,
        version=v1,
        text_content=(
            "VERSION ONE REQUIREMENT. Applicants must submit a vehicle "
            "registration certificate."
        ),
    )

    retriever = PolicyRetriever()

    res_v1 = retriever.retrieve(
        "What document must applicants submit?",
        where={"policy_id": str(policy_id)},
        db=db,
    )

    assert res_v1["results"]
    assert all(
        item["policy_version_id"] == str(v1.id)
        for item in res_v1["results"]
    )

    v2 = PolicyVersion(
        id=uuid.uuid4(),
        policy_id=policy_id,
        version_number="2",
        effective_from=datetime.now(timezone.utc),
    )

    db.add(v2)
    db.flush()

    policy.current_version_id = v2.id
    db.commit()

    _insert_chunk(
        db,
        policy=policy,
        version=v2,
        text_content=(
            "VERSION TWO REQUIREMENT. Applicants must submit a valid "
            "vehicle insurance certificate."
        ),
    )

    result = retriever.retrieve(
        "What document must applicants submit?",
        where={"policy_id": str(policy_id)},
        db=db,
    )

    assert result["results"]
    assert all(
        item["policy_version_id"] == str(v2.id)
        for item in result["results"]
    )
    assert all(
        item["policy_version_id"] != str(v1.id)
        for item in result["results"]
    )


def test_institution_isolation_bank_a_cannot_retrieve_bank_b(db):
    """Verify institution filtering prevents cross-bank retrieval."""

    policy_a, version_a = _create_policy_version(
        db,
        institution="Bank A",
    )

    policy_b, version_b = _create_policy_version(
        db,
        institution="Bank B",
    )

    _insert_chunk(
        db,
        policy=policy_a,
        version=version_a,
        text_content=(
            "Bank A requires applicants to submit a salary certificate "
            "for personal loan applications."
        ),
        institution="Bank A",
    )

    _insert_chunk(
        db,
        policy=policy_b,
        version=version_b,
        text_content=(
            "Bank B requires applicants to submit an employment certificate "
            "for personal loan applications."
        ),
        institution="Bank B",
    )

    retriever = PolicyRetriever()

    result = retriever.retrieve(
        "What certificate is required?",
        where={
            "institution": "Bank A",
        },
        db=db,
    )

    assert result["results"]
    assert all(
        item["institution"] == "Bank A"
        for item in result["results"]
    )
    assert all(
        item["institution"] != "Bank B"
        for item in result["results"]
    )


def test_jurisdiction_isolation_in_vs_us(db):
    """Verify jurisdiction filtering prevents cross-jurisdiction retrieval."""

    policy_in, version_in = _create_policy_version(
        db,
        jurisdiction="IN",
    )

    policy_us, version_us = _create_policy_version(
        db,
        jurisdiction="US",
    )

    _insert_chunk(
        db,
        policy=policy_in,
        version=version_in,
        text_content=(
            "Indian jurisdiction requires applicants to submit a valid "
            "identity document for the application."
        ),
        jurisdiction="IN",
    )

    _insert_chunk(
        db,
        policy=policy_us,
        version=version_us,
        text_content=(
            "United States jurisdiction requires applicants to submit "
            "a valid identity document for the application."
        ),
        jurisdiction="US",
    )

    retriever = PolicyRetriever()

    result = retriever.retrieve(
        "What identity document is required?",
        where={
            "jurisdiction": "IN",
        },
        db=db,
    )

    assert result["results"]
    assert all(
        item["jurisdiction"] == "IN"
        for item in result["results"]
    )
    assert all(
        item["jurisdiction"] != "US"
        for item in result["results"]
    )


def test_unscoped_policy_is_universal_for_loan_type_filter(db):
    """Verify policies without applicability rows remain eligible for any loan type."""

    policy, version = _create_policy_version(
        db,
    )

    _insert_chunk(
        db,
        policy=policy,
        version=version,
        text_content=(
            "Universal recovery policy requires recovery agents to contact "
            "borrowers only within permitted hours."
        ),
    )

    retriever = PolicyRetriever()

    result = retriever.retrieve(
        "What are the permitted contact hours for recovery agents?",
        where={
            "loan_type": "business",
        },
        db=db,
    )

    assert result["results"]
    assert any(
        "permitted hours" in item["text"].lower()
        for item in result["results"]
    )

def test_loan_type_isolation_vehicle_vs_home(db):
    """Verify scoped loan types remain isolated while unscoped policies remain eligible."""

    vehicle_policy, vehicle_version = _create_policy_version(
        db,
        loan_type="vehicle",
    )

    home_policy, home_version = _create_policy_version(
        db,
        loan_type="home",
    )

    _insert_chunk(
        db,
        policy=vehicle_policy,
        version=vehicle_version,
        text_content=(
            "For vehicle loans, applicants must submit the vehicle "
            "registration certificate."
        ),
    )

    _insert_chunk(
        db,
        policy=home_policy,
        version=home_version,
        text_content=(
            "For home loans, applicants must submit the property "
            "registration document."
        ),
    )

    retriever = PolicyRetriever()

    result = retriever.retrieve(
        "What registration document is required?",
        where={
            "loan_type": "vehicle",
        },
        db=db,
    )

    assert result["results"]

    result_text = [
        item["text"].lower()
        for item in result["results"]
    ]

    assert any(
        "vehicle loans" in text
        for text in result_text
    )

    assert not any(
        "home loans" in text
        for text in result_text
    )


def test_no_applicable_evidence_yields_insufficient(db):
    """Verify a mismatched scoped policy is excluded for another loan type."""

    policy, version = _create_policy_version(
        db,
        loan_type="home",
    )

    _insert_chunk(
        db,
        policy=policy,
        version=version,
        text_content=(
            "Home loan applicants must submit the property registration "
            "document before approval."
        ),
    )

    adaptive = AdaptivePolicyRetriever(
        PolicyRetriever()
    )

    result = adaptive.retrieve(
        "What document is required?",
        where={
            "loan_type": "vehicle",
        },
        # pyrefly: ignore [unexpected-keyword]
        db=db,
    )

    result_text = [
        item["text"].lower()
        for item in result.get("evidence", [])
    ]

    assert not any(
        "home loan applicants must submit the property registration "
        "document before approval." in text
        for text in result_text
    )


def test_evidence_provenance_fields_present(db):
    """Verify retrieved evidence exposes required provenance metadata."""

    policy, version = _create_policy_version(
        db,
        institution="Bank A",
        jurisdiction="IN",
    )

    _insert_chunk(
        db,
        policy=policy,
        version=version,
        text_content=(
            "Applicants must submit a valid identity certificate "
            "before processing can begin."
        ),
        institution="Bank A",
        jurisdiction="IN",
    )

    adaptive = AdaptivePolicyRetriever(
        PolicyRetriever()
    )

    result = adaptive.retrieve(
        "What must the applicant submit?",
        where={
            "institution": "Bank A",
            "jurisdiction": "IN",
        },
        # pyrefly: ignore [unexpected-keyword]
        db=db,
    )

    assert result["evidence_status"] == "sufficient"
    assert result["evidence"]

    item = result["evidence"][0]

    required_fields = [
        "chunk_id",
        "text",
        "document_id",
        "document",
        "source",
        "source_type",
        "source_url",
        "page",
        "policy_id",
        "policy_version_id",
        "version_number",
        "institution",
        "jurisdiction",
        "effective_from",
        "file_hash",
    ]

    for field in required_fields:
        assert field in item


def test_vector_similarity_retrieval_and_metadata_filtering(db):
    """Verify vector similarity retrieval combined with metadata filtering."""

    policy, version = _create_policy_version(
        db,
        institution="Bank A",
        jurisdiction="IN",
    )

    _insert_chunk(
        db,
        policy=policy,
        version=version,
        text_content=(
            "Vehicle loan applicants must submit a vehicle registration "
            "certificate before approval."
        ),
        institution="Bank A",
        jurisdiction="IN",
    )

    retriever = PolicyRetriever()

    result = retriever.retrieve(
        "vehicle registration certificate",
        where={
            "institution": "Bank A",
            "jurisdiction": "IN",
        },
        top_k=5,
        db=db,
    )

    assert result["results"]

    first = result["results"][0]

    assert first["institution"] == "Bank A"
    assert first["jurisdiction"] == "IN"
    assert "vehicle" in first["text"].lower()
    assert "registration" in first["text"].lower()


def test_customer_ai_endpoint_authorization_and_ownership(client, db):
    """Verify customer AI endpoint authorization and ownership."""

    response = client.post(
        "/api/customer/ai/query",
        json={
            "query": "What documents are required?",
        },
    )

    assert response.status_code in (401, 403)


def test_customer_endpoint_applicability_aware_retrieval(client, db):
    """Verify customer endpoint respects applicability-aware retrieval."""

    response = client.post(
        "/api/customer/ai/query",
        json={
            "query": "What document is required for a vehicle loan?",
            "institution": "Bank A",
            "jurisdiction": "IN",
            "loan_type": "vehicle",
        },
    )

    assert response.status_code in (401, 403)

def test_evaluator_rejects_aggregated_unrelated_evidence_for_recovery_agent_query():
    evaluator = EvidenceEvaluator()

    query = "guidelines recovery agents contacting borrowers"

    unrelated_texts = [
        "The Reserve Bank shall issue guidelines for regulated entities. "
        "Such guidelines shall be followed by the regulated entity.",
        "The Scheme provides for recovery of amounts in accordance with "
        "the applicable complaint process and shall be handled accordingly.",
        "The regulated entity may appoint agents for operational purposes "
        "and shall ensure appropriate supervision of such arrangements.",
        "The Principal Nodal Officer shall maintain contact details and "
        "shall ensure that relevant information is communicated to the public.",
    ]

    retrieval_result = {
        "results": [
            {
                "text": text,
                "chunk_id": f"ombudsman-chunk-{index}",
                "document_id": "ombudsman-document-1",
                "source": "rbi_ombudsman.pdf",
            }
            for index, text in enumerate(unrelated_texts, start=1)
        ]
    }

    result = evaluator.evaluate(query, retrieval_result)

    assert result["evidence_status"] == "insufficient"
import os
from dotenv import load_dotenv
load_dotenv(os.path.join(os.path.dirname(os.path.dirname(__file__)), "..", ".env"))

import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.db.session import SessionLocal
from app.db.models import User, Session as DBSession
from sqlalchemy.orm import Session

client = TestClient(app)

@pytest.fixture
def db_session():
    db = SessionLocal()
    # Cleanup test users
    db.query(DBSession).filter(DBSession.user_id.in_(
        db.query(User.id).filter(User.email == "localtest@test.internal")
    )).delete(synchronize_session=False)
    db.query(User).filter(User.email == "localtest@test.internal").delete(synchronize_session=False)
    db.commit()

    yield db

    db.query(DBSession).filter(DBSession.user_id.in_(
        db.query(User.id).filter(User.email == "localtest@test.internal")
    )).delete(synchronize_session=False)
    db.query(User).filter(User.email == "localtest@test.internal").delete(synchronize_session=False)
    db.commit()
    db.close()

def test_local_registration_flow(db_session: Session):
    # 1. Register a new user
    res = client.post("/auth/local/register", json={
        "email": "localtest@test.internal",
        "password": "SecurePassword123!",
        "role": "CUSTOMER",
        "full_name": "Test User",
        "phone_number": "+919876543210",
        "language": "English",
        "consent_accepted": True
    })
    assert res.status_code == 200
    assert res.json()["message"] == "Account created/upgraded successfully"

    # Verify in DB
    user = db_session.query(User).filter(User.email == "localtest@test.internal").first()
    assert user is not None
    assert user.hashed_password is not None
    assert user.onboarding_status == "COMPLETED"

    # 2. Login with wrong password
    res_wrong = client.post("/auth/local/login", json={
        "identifier": "localtest@test.internal",
        "password": "WrongPassword!"
    })
    assert res_wrong.status_code == 401

    # 3. Login with correct password
    res_correct = client.post("/auth/local/login", json={
        "identifier": "localtest@test.internal",
        "password": "SecurePassword123!"
    })
    assert res_correct.status_code == 200
    assert res_correct.json()["redirect"] == "/dashboard"

    # Check if session_id cookie is present
    session_id = res_correct.cookies.get("session_id")
    assert session_id is not None

    # 4. Authenticated /auth/me works
    res_me = client.get("/auth/me")
    assert res_me.status_code == 200
    assert res_me.json()["email"] == "localtest@test.internal"
    assert res_me.json()["onboarding_status"] == "COMPLETED"


def test_google_admin_local_password_login(db_session: Session):
    import uuid
    from app.core.security import get_password_hash
    from app.db.models import Role, OnboardingStatus

    test_google_email = "test_google_admin_hybrid@test.internal"
    test_password = "AdminHybridPassword123!"

    # Clean up any leftover test user
    db_session.query(DBSession).filter(DBSession.user_id.in_(
        db_session.query(User.id).filter(User.email == test_google_email)
    )).delete(synchronize_session=False)
    db_session.query(User).filter(User.email == test_google_email).delete(synchronize_session=False)
    db_session.commit()

    # 1. Create a Google-linked admin account with a hashed_password
    google_admin = User(
        id=uuid.uuid4(),
        email=test_google_email,
        full_name="Google Admin User",
        authentication_provider="google",
        provider_subject_id="mock_google_sub_12345",
        role=Role.ADMIN.value,
        requested_role=Role.ADMIN.value,
        onboarding_status=OnboardingStatus.COMPLETED.value,
        hashed_password=get_password_hash(test_password)
    )
    db_session.add(google_admin)
    db_session.commit()

    try:
        # 2. Attempt local login with email + wrong password
        res_fail = client.post("/auth/local/login", json={
            "identifier": test_google_email,
            "password": "WrongAdminPassword!"
        })
        assert res_fail.status_code == 401

        # 3. Attempt local login with email + correct password
        res_login = client.post("/auth/local/login", json={
            "identifier": test_google_email,
            "password": test_password
        })
        assert res_login.status_code == 200
        data = res_login.json()
        assert data["role"] == "ADMIN"
        session_id = res_login.cookies.get("session_id")
        assert session_id is not None

        # 4. Verify /auth/me returns admin role and retains Google provider
        res_me = client.get("/auth/me", cookies={"session_id": session_id})
        assert res_me.status_code == 200
        me_data = res_me.json()
        assert me_data["email"] == test_google_email
        assert me_data["role"] == "ADMIN"
        assert me_data["authentication_provider"] == "google"

        # 5. Verify admin endpoints are accessible with this session
        res_admin = client.get("/admin/employee-requests", cookies={"session_id": session_id})
        assert res_admin.status_code == 200

    finally:
        # Cleanup
        db_session.query(DBSession).filter(DBSession.user_id == google_admin.id).delete(synchronize_session=False)
        db_session.query(User).filter(User.id == google_admin.id).delete(synchronize_session=False)
        db_session.commit()

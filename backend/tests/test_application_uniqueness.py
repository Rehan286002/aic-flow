import sys
import uuid
from pathlib import Path

# Ensure backend root is in sys.path
BACKEND_DIR = str(Path(__file__).resolve().parents[1])
if BACKEND_DIR not in sys.path:
    sys.path.insert(0, BACKEND_DIR)

import pytest
from fastapi import HTTPException
from fastapi.testclient import TestClient
from sqlalchemy import text
from sqlalchemy.exc import IntegrityError

from app.core.config import settings
from app.core.security import create_access_token
from app.db.session import SessionLocal
from app.main import app
from app.models.application import Application
from app.models.enums import ApplicationFamily, ApplicationStatus
from app.models.institution import Institution
from app.models.user import User
from app.schemas.application import ApplicationCreateRequest
from app.services.application_service import create_application_draft


@pytest.fixture
def client() -> TestClient:
    return TestClient(app)


@pytest.fixture
def db_session():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.rollback()
        db.close()


@pytest.fixture
def auth_headers(db_session):
    inst = (
        db_session.query(Institution)
        .filter_by(aicte_permanent_institution_id="SYNTH-AICTE-0001")
        .first()
    )
    assert inst is not None
    user = (
        db_session.query(User)
        .filter_by(email="institution@aic-verify.internal")
        .first()
    )
    assert user is not None

    token = create_access_token(user.user_id)
    csrf_token = "test-csrf-token-uniqueness"

    cookies = {
        settings.access_cookie_name: token,
        settings.csrf_cookie_name: csrf_token,
    }
    headers = {
        "X-CSRF-Token": csrf_token,
    }
    return {
        "institution_id": inst.institution_id,
        "user_id": user.user_id,
        "cookies": cookies,
        "headers": headers,
    }


def test_database_uniqueness_constraint_exists(db_session):
    """Verify that uq_applications_institution_ay_family exists in PostgreSQL pg_constraint."""
    stmt = text("""
        SELECT conname, contype, pg_get_constraintdef(c.oid)
        FROM pg_constraint c
        JOIN pg_class t ON c.conrelid = t.oid
        WHERE t.relname = 'applications'
          AND c.conname = 'uq_applications_institution_ay_family';
    """)
    result = db_session.execute(stmt).fetchone()
    assert result is not None, (
        "Constraint uq_applications_institution_ay_family not found in PostgreSQL"
    )
    assert result[1] == "u", "Constraint is not a UNIQUE constraint"
    assert "UNIQUE (institution_id, academic_year, application_family)" in result[2]


def test_sequential_duplicate_creation_returns_409(client, auth_headers):
    """Verify that standard sequential duplicate creation is rejected with HTTP 409."""
    inst_id = auth_headers["institution_id"]
    payload = {
        "academic_year": "2026-27",
        "application_family": "EXISTING_INSTITUTION",
        "completion_certificate_issue_date": "2008-07-12",
        "payment_applicable": True,
    }
    resp = client.post(
        f"/api/v1/institutions/{inst_id}/applications",
        json=payload,
        cookies=auth_headers["cookies"],
        headers=auth_headers["headers"],
    )
    assert resp.status_code == 409
    assert "already exists" in resp.json()["detail"].lower()


def test_database_rejects_duplicate_when_precheck_bypassed(db_session, auth_headers):
    """Verify database raises IntegrityError when pre-check is bypassed."""
    inst_id = auth_headers["institution_id"]
    user_id = auth_headers["user_id"]

    # Attempt to insert a duplicate application directly via SQLAlchemy bypassing service pre-check
    dup_app = Application(
        application_number=f"APP-TEST-DUP-{uuid.uuid4().hex[:6]}",
        institution_id=inst_id,
        application_family=ApplicationFamily.EXISTING_INSTITUTION,
        academic_year="2026-27",
        status=ApplicationStatus.DRAFT,
        created_by=user_id,
    )
    db_session.add(dup_app)
    with pytest.raises(IntegrityError) as exc_info:
        db_session.flush()

    assert "uq_applications_institution_ay_family" in str(exc_info.value).lower()
    db_session.rollback()


def test_concurrent_uniqueness_violation_mapped_to_409(
    db_session, auth_headers, monkeypatch
):
    """Verify that if two concurrent requests bypass pre-check, DB constraint violation maps to HTTP 409."""
    inst_id = auth_headers["institution_id"]
    user_id = auth_headers["user_id"]

    # Monkeypatch the service pre-check scalar query to return None (simulating simultaneous check)
    original_scalar = db_session.scalar

    def mock_scalar(statement, *args, **kwargs):
        # If querying Application in step 1, return None to simulate race condition
        stmt_str = str(statement)
        if "FROM applications" in stmt_str and "applications.academic_year" in stmt_str:
            return None
        return original_scalar(statement, *args, **kwargs)

    monkeypatch.setattr(db_session, "scalar", mock_scalar)

    payload = ApplicationCreateRequest(
        academic_year="2026-27",
        application_family=ApplicationFamily.EXISTING_INSTITUTION,
        completion_certificate_issue_date=None,
        payment_applicable=None,
        application_remarks="Simulated concurrent race request",
    )

    with pytest.raises(HTTPException) as exc_info:
        create_application_draft(db_session, inst_id, user_id, payload)

    assert exc_info.value.status_code == 409
    assert "already exists" in exc_info.value.detail.lower()


def test_unrelated_integrity_errors_not_misclassified(
    db_session, auth_headers, monkeypatch
):
    """Verify that unrelated IntegrityErrors (e.g. foreign key or check) are not misclassified as 409."""
    inst_id = auth_headers["institution_id"]

    # Bypass pre-check so we reach insertion
    original_scalar = db_session.scalar

    def mock_scalar(statement, *args, **kwargs):
        stmt_str = str(statement)
        if "FROM applications" in stmt_str and "applications.academic_year" in stmt_str:
            return None
        return original_scalar(statement, *args, **kwargs)

    monkeypatch.setattr(db_session, "scalar", mock_scalar)

    # Use a non-existent fake user_id for current_user_id to trigger a FOREIGN KEY violation
    fake_user_id = uuid.uuid4()

    payload = ApplicationCreateRequest(
        academic_year="2099-00",  # Different AY so unique constraint won't fire
        application_family=ApplicationFamily.EXISTING_INSTITUTION,
    )

    # Must raise IntegrityError from DB, NOT HTTPException(409)
    with pytest.raises(IntegrityError) as exc_info:
        create_application_draft(db_session, inst_id, fake_user_id, payload)

    assert "applications_created_by_fkey" in str(exc_info.value).lower()
    db_session.rollback()


def test_existing_application_records_remain_unchanged(db_session):
    """Verify existing applications (e.g. APP-2026-EOA-0006) remain completely intact."""
    app_record = (
        db_session.query(Application)
        .filter_by(application_number="APP-2026-EOA-0006")
        .first()
    )
    if app_record:
        assert app_record.academic_year == "2026-27"
        assert app_record.application_family == ApplicationFamily.EXISTING_INSTITUTION
        assert app_record.status == ApplicationStatus.DRAFT
        assert app_record.current_revision_id is not None

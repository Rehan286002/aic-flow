import sys
import uuid
from datetime import date
from pathlib import Path

# Ensure backend root is in sys.path
BACKEND_DIR = str(Path(__file__).resolve().parents[1])
if BACKEND_DIR not in sys.path:
    sys.path.insert(0, BACKEND_DIR)

import pytest
from fastapi.testclient import TestClient

from app.core.config import settings
from app.core.security import create_access_token
from app.db.session import SessionLocal
from app.main import app
from app.models.application import Application
from app.models.application_document_link import ApplicationDocumentLink
from app.models.application_field_value import ApplicationFieldValue
from app.models.application_requirements import ApplicationRequirement
from app.models.application_revision import ApplicationRevision
from app.models.application_status_history import ApplicationStatusHistory
from app.models.checklist_item import ChecklistItem
from app.models.institution import Institution
from app.models.user import User
from app.services.checklist_service import (
    evaluate_item_applicability,
    seed_standard_references,
)


@pytest.fixture
def client() -> TestClient:
    return TestClient(app)


@pytest.fixture
def seeded_db():
    db = SessionLocal()
    seed_standard_references(db)
    try:
        yield db
    finally:
        db.close()


@pytest.fixture
def auth_headers_institution(seeded_db):
    """Auth cookies and CSRF headers for institution user."""
    # Find existing synthetic institution user or Apex Institute
    inst = (
        seeded_db.query(Institution)
        .filter_by(aicte_permanent_institution_id="SYNTH-AICTE-0001")
        .first()
    )
    assert inst is not None

    user = (
        seeded_db.query(User).filter_by(email="institution@aic-verify.internal").first()
    )
    assert user is not None

    token = create_access_token(user.user_id)
    csrf_token = "test-csrf-token-12345"

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


def test_checklist_seed_definitions_and_order(seeded_db):
    """Verify all 7 checklist items exist with exact regulatory codes, titles, and display orders."""
    items = (
        seeded_db.query(ChecklistItem).order_by(ChecklistItem.display_order.asc()).all()
    )
    assert len(items) == 7

    codes = [i.item_code for i in items]
    assert codes == [
        "EOA-SD-01",
        "EOA-SD-02",
        "EOA-SD-03",
        "EOA-SD-04",
        "EOA-SD-05",
        "EOA-SD-06",
        "EOA-SD-07",
    ]

    # EOA-SD-06 document type check
    item_06 = next(i for i in items if i.item_code == "EOA-SD-06")
    assert item_06.expected_document_type_code == "SATELLITE_MAP"
    assert "geographical location" in item_06.description

    # EOA-SD-04 validity check
    item_04 = next(i for i in items if i.item_code == "EOA-SD-04")
    assert item_04.validation_config.get("validity_years") == 5
    assert "more than 30 years" in item_04.description


def test_structural_stability_applicability_boundary(seeded_db):
    """Verify exact 30-year boundary calculation for structural stability certificate."""
    item_04 = seeded_db.query(ChecklistItem).filter_by(item_code="EOA-SD-04").first()
    assessment_date = date(2026, 7, 1)

    # 1. Exactly 30 years (1996-07-01 to 2026-07-01) -> NOT_APPLICABLE (threshold is MORE THAN 30 years)
    app_status, reason = evaluate_item_applicability(
        item_04,
        {"completion_certificate_issue_date": date(1996, 7, 1)},
        assessment_date=assessment_date,
    )
    assert app_status == "NOT_APPLICABLE"
    assert "within the 30-year statutory threshold" in reason

    # 2. More than 30 years by 1 day (1996-06-30) -> APPLICABLE
    app_status, reason = evaluate_item_applicability(
        item_04,
        {"completion_certificate_issue_date": date(1996, 6, 30)},
        assessment_date=assessment_date,
    )
    assert app_status == "APPLICABLE"
    assert "exceeding the 30-year statutory threshold" in reason

    # 3. Apex Institute campus built in 2008 (18 years) -> NOT_APPLICABLE
    app_status, reason = evaluate_item_applicability(
        item_04,
        {"completion_certificate_issue_date": date(2008, 7, 12)},
        assessment_date=assessment_date,
    )
    assert app_status == "NOT_APPLICABLE"

    # 4. Missing/unknown date -> PENDING_DETERMINATION
    app_status, reason = evaluate_item_applicability(
        item_04,
        {},
        assessment_date=assessment_date,
    )
    assert app_status == "PENDING_DETERMINATION"


def test_payment_receipt_applicability_conditions(seeded_db):
    """Verify payment receipt evaluates to APPLICABLE, NOT_APPLICABLE or PENDING_DETERMINATION."""
    item_02 = seeded_db.query(ChecklistItem).filter_by(item_code="EOA-SD-02").first()

    # Declared applicable
    app_status, _ = evaluate_item_applicability(item_02, {"payment_applicable": True})
    assert app_status == "APPLICABLE"

    # Declared exempt / not applicable
    app_status, _ = evaluate_item_applicability(item_02, {"payment_applicable": False})
    assert app_status == "NOT_APPLICABLE"

    # Missing declaration
    app_status, _ = evaluate_item_applicability(item_02, {})
    assert app_status == "PENDING_DETERMINATION"


def test_create_application_draft_and_lifecycle(
    client, auth_headers_institution, seeded_db
):
    """Verify complete application creation, revision 1, status history, requirements and declarations."""
    inst_id = auth_headers_institution["institution_id"]
    cookies = auth_headers_institution["cookies"]
    headers = auth_headers_institution["headers"]

    # Clean any pre-existing application for this test academic year to ensure test isolation
    existing = (
        seeded_db.query(Application)
        .filter_by(institution_id=inst_id, academic_year="2028-29")
        .first()
    )
    if existing:
        # Clean requirements and values
        rev_ids = [
            r.application_revision_id
            for r in seeded_db.query(ApplicationRevision)
            .filter_by(application_id=existing.application_id)
            .all()
        ]
        seeded_db.query(ApplicationDocumentLink).filter(
            ApplicationDocumentLink.application_revision_id.in_(rev_ids)
        ).delete(synchronize_session=False)
        seeded_db.query(ApplicationRequirement).filter(
            ApplicationRequirement.application_revision_id.in_(rev_ids)
        ).delete(synchronize_session=False)
        seeded_db.query(ApplicationFieldValue).filter(
            ApplicationFieldValue.application_revision_id.in_(rev_ids)
        ).delete(synchronize_session=False)
        seeded_db.query(ApplicationStatusHistory).filter_by(
            application_id=existing.application_id
        ).delete(synchronize_session=False)
        existing.current_revision_id = None
        seeded_db.flush()
        seeded_db.query(ApplicationRevision).filter_by(
            application_id=existing.application_id
        ).delete(synchronize_session=False)
        seeded_db.delete(existing)
        seeded_db.commit()

    payload = {
        "academic_year": "2028-29",
        "application_family": "EXISTING_INSTITUTION",
        "completion_certificate_issue_date": "2008-07-12",
        "payment_applicable": True,
        "application_remarks": "Extension of Approval submission for Apex Institute of Technology AY 2028-29",
    }

    resp = client.post(
        f"/api/v1/institutions/{inst_id}/applications",
        json=payload,
        cookies=cookies,
        headers=headers,
    )
    assert resp.status_code == 201, resp.text
    data = resp.json()

    assert data["institution_id"] == str(inst_id)
    assert data["academic_year"] == "2028-29"
    assert data["status"] == "DRAFT"
    assert data["application_number"].startswith("APP-2028-EOA-")
    assert data["current_revision"]["revision_number"] == 1
    assert data["current_revision"]["status"] == "DRAFT"
    assert (
        data["current_revision"]["declarations"]["completion_certificate_issue_date"]
        == "2008-07-12"
    )
    assert data["current_revision"]["declarations"]["payment_applicable"] is True

    # Check status history
    assert len(data["status_history"]) == 1
    assert data["status_history"][0]["to_status"] == "DRAFT"
    assert "Initial Extension of Approval" in data["status_history"][0]["change_reason"]

    # Check all 7 requirements
    assert len(data["requirements"]) == 7
    req_map = {r["item_code"]: r for r in data["requirements"]}

    # EOA-SD-04 (campus built in 2008 -> 18 years <= 30) -> NOT_APPLICABLE
    assert req_map["EOA-SD-04"]["applicability_status"] == "NOT_APPLICABLE"
    assert req_map["EOA-SD-04"]["status"] == "NOT_APPLICABLE"

    # EOA-SD-02 (payment declared True) -> APPLICABLE
    assert req_map["EOA-SD-02"]["applicability_status"] == "APPLICABLE"

    # EOA-SD-01, 03, 05, 06, 07 -> APPLICABLE, PENDING
    assert req_map["EOA-SD-01"]["applicability_status"] == "APPLICABLE"
    assert req_map["EOA-SD-06"]["expected_document_type_code"] == "SATELLITE_MAP"

    app_id = data["application_id"]

    # Duplicate creation attempt must fail with 409 Conflict
    dup_resp = client.post(
        f"/api/v1/institutions/{inst_id}/applications",
        json=payload,
        cookies=cookies,
        headers=headers,
    )
    assert dup_resp.status_code == 409

    # List applications endpoint
    list_resp = client.get(
        f"/api/v1/institutions/{inst_id}/applications",
        cookies=cookies,
    )
    assert list_resp.status_code == 200
    list_data = list_resp.json()
    assert len(list_data) >= 1
    assert any(a["application_id"] == app_id for a in list_data)

    # Get application details endpoint
    detail_resp = client.get(
        f"/api/v1/institutions/{inst_id}/applications/{app_id}",
        cookies=cookies,
    )
    assert detail_resp.status_code == 200
    assert detail_resp.json()["application_id"] == app_id

    # Update draft declarations: change completion certificate to 1990 (36 years ago -> APPLICABLE)
    patch_payload = {
        "completion_certificate_issue_date": "1990-05-15",
        "payment_applicable": False,
        "application_remarks": "Updated: older annex block built in 1990.",
    }
    patch_resp = client.patch(
        f"/api/v1/institutions/{inst_id}/applications/{app_id}",
        json=patch_payload,
        cookies=cookies,
        headers=headers,
    )
    assert patch_resp.status_code == 200
    patch_data = patch_resp.json()
    updated_req_map = {r["item_code"]: r for r in patch_data["requirements"]}

    # EOA-SD-04 must now be dynamically recalculated to APPLICABLE
    assert updated_req_map["EOA-SD-04"]["applicability_status"] == "APPLICABLE"
    assert (
        "exceeding the 30-year statutory threshold"
        in updated_req_map["EOA-SD-04"]["determination_reason"]
    )

    # EOA-SD-02 must now be recalculated to NOT_APPLICABLE
    assert updated_req_map["EOA-SD-02"]["applicability_status"] == "NOT_APPLICABLE"


def test_authorization_and_isolation(client, auth_headers_institution, seeded_db):
    """Verify strict RBAC: cross-institution denial, admin denial, auditor denial, missing CSRF."""
    inst_id = auth_headers_institution["institution_id"]
    cookies = auth_headers_institution["cookies"]

    # 1. Cross-institution access: institution user accessing another institution's path
    fake_inst_id = uuid.uuid4()
    resp_cross = client.get(
        f"/api/v1/institutions/{fake_inst_id}/applications",
        cookies=cookies,
    )
    assert resp_cross.status_code == 403

    # 2. Admin access denial (Admin does not have institution scope)
    admin_user = (
        seeded_db.query(User).filter_by(email="admin@aic-verify.internal").first()
    )
    assert admin_user is not None
    admin_token = create_access_token(admin_user.user_id)
    resp_admin = client.get(
        f"/api/v1/institutions/{inst_id}/applications",
        cookies={settings.access_cookie_name: admin_token},
    )
    assert resp_admin.status_code == 403

    # 3. Auditor access denial (Auditor does not have institution scope)
    auditor_user = (
        seeded_db.query(User).filter_by(email="auditor@aic-verify.internal").first()
    )
    assert auditor_user is not None
    auditor_token = create_access_token(auditor_user.user_id)
    resp_auditor = client.get(
        f"/api/v1/institutions/{inst_id}/applications",
        cookies={settings.access_cookie_name: auditor_token},
    )
    assert resp_auditor.status_code == 403

    # 4. Unauthenticated request
    resp_unauth = client.get(f"/api/v1/institutions/{inst_id}/applications")
    assert resp_unauth.status_code == 401

    # 5. Missing CSRF token on POST
    resp_no_csrf = client.post(
        f"/api/v1/institutions/{inst_id}/applications",
        json={"academic_year": "2026-27"},
        cookies=cookies,
        # Omit X-CSRF-Token header
    )
    assert resp_no_csrf.status_code == 403

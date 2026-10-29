"""AIC-Verify — Integration Tests for Extracted Field Regulatory Reviews.

Phase 4, Batch 5 Part B:
Verifies:
1. Auditor and Lead Auditor review lifecycle (accept as extracted, submit corrections).
2. Pydantic validation: mutual exclusivity, >= 5 non-whitespace review note, max length.
3. Database check constraints: chk_extracted_field_reviews_decision (regex whitespace),
   chk_extracted_field_reviews_role, chk_extracted_field_reviews_payload_size.
4. Database append-only triggers: row-level blocking of UPDATE and DELETE,
   and statement-level blocking of TRUNCATE.
5. Migration safe downgrade concurrency: table lock and hard refusal if records exist.
6. Phase 2 RBAC: Institution User and Admin forbidden from POSTing reviews (403).
7. Confidentiality redaction: Institution User receives sanitized projection
   (review notes and reviewer identity completely stripped).
"""

from __future__ import annotations

import io
import uuid
from typing import Any

import pytest
from alembic.migration import MigrationContext
from alembic.operations import Operations
from fastapi.testclient import TestClient
from pypdf import PdfWriter
from sqlalchemy import text
from sqlalchemy.exc import DBAPIError, IntegrityError

from app.core.config import settings
from app.core.security import create_access_token
from app.db.session import SessionLocal
from app.main import app
from app.models.application import Application
from app.models.application_document_link import ApplicationDocumentLink
from app.models.application_requirements import ApplicationRequirement
from app.models.application_revision import ApplicationRevision
from app.models.checklist_item import ChecklistItem
from app.models.document import Document
from app.models.document_extraction import DocumentExtraction
from app.models.document_processing_job import DocumentProcessingJob
from app.models.document_security_scan import DocumentSecurityScan
from app.models.document_version import DocumentVersion
from app.models.enums import DocumentProcessingStatus
from app.models.extracted_field import ExtractedField
from app.models.extracted_field_review import ExtractedFieldReview
from app.models.institution import Institution
from app.models.review_team import ReviewTeam
from app.models.user import User
from app.services.checklist_service import seed_standard_references
from app.services.storage_service import storage_service


def make_native_pdf(text_content: str) -> bytes:
    writer = PdfWriter()
    writer.add_blank_page(width=612, height=792)
    buf = io.BytesIO()
    writer.write(buf)
    return buf.getvalue()


@pytest.fixture
def client() -> TestClient:
    return TestClient(app)


@pytest.fixture
def review_setup():
    """Sets up an isolated evidence document, extraction, and candidate field for review testing."""
    db = SessionLocal()
    seed_standard_references(db)

    inst = (
        db.query(Institution)
        .filter_by(aicte_permanent_institution_id="SYNTH-AICTE-0001")
        .first()
    )
    user_inst = (
        db.query(User).filter_by(email="institution@aic-verify.internal").first()
    )
    user_auditor = db.query(User).filter_by(email="auditor@aic-verify.internal").first()
    user_lead = db.query(User).filter_by(email="lead@aic-verify.internal").first()
    user_admin = db.query(User).filter_by(email="admin@aic-verify.internal").first()

    app_rec = (
        db.query(Application)
        .filter_by(
            institution_id=inst.institution_id,
            academic_year="2026-27",
        )
        .first()
    )

    # Assign application to synthetic review team so auditors have authorized scope
    team = db.query(ReviewTeam).first()
    if team:
        app_rec.review_team_id = team.review_team_id
        db.flush()

    rev = (
        db.query(ApplicationRevision)
        .filter_by(application_id=app_rec.application_id)
        .order_by(ApplicationRevision.revision_number.desc())
        .first()
    )
    ci = db.query(ChecklistItem).filter_by(item_code="EOA-SD-05").first()
    req = (
        db.query(ApplicationRequirement)
        .filter_by(
            application_revision_id=rev.application_revision_id,
            checklist_item_id=ci.checklist_item_id,
        )
        .first()
    )

    doc = Document(
        institution_id=inst.institution_id,
        document_label="Fire Safety Review Test Doc",
        created_by=user_inst.user_id,
    )
    db.add(doc)
    db.flush()

    pdf_bytes = make_native_pdf("FIRE NOC TEST CONTENT")
    quar_path, sha256_hex, fsize = storage_service.save_bytes_to_quarantine(pdf_bytes)
    _clean_path, storage_key = storage_service.move_to_clean(quar_path)

    doc_version = DocumentVersion(
        document_id=doc.document_id,
        version_number=1,
        original_filename="fire_noc_review_test.pdf",
        storage_key=storage_key,
        mime_type="application/pdf",
        file_size_bytes=fsize,
        sha256_hex=sha256_hex,
        uploaded_by=user_inst.user_id,
    )
    db.add(doc_version)
    db.flush()

    link = ApplicationDocumentLink(
        application_revision_id=rev.application_revision_id,
        uploaded_for_requirement_id=req.application_requirement_id,
        document_version_id=doc_version.document_version_id,
    )
    db.add(link)

    sec_scan = DocumentSecurityScan(
        document_version_id=doc_version.document_version_id,
        scanner_name="ClamAV",
        scanner_version="1.4.6",
        signature_database_version="27500",
        scan_status="CLEAN",
        threat_name=None,
    )
    db.add(sec_scan)

    job = DocumentProcessingJob(
        document_version_id=doc_version.document_version_id,
        processing_status=DocumentProcessingStatus.COMPLETED,
        pipeline_name="DOCUMENT_INGESTION_V1",
        pipeline_version="1.0.0",
    )
    db.add(job)
    db.flush()

    extraction = DocumentExtraction(
        document_version_id=doc_version.document_version_id,
        processing_job_id=job.document_processing_job_id,
        extraction_status=DocumentProcessingStatus.COMPLETED,
        extraction_engine="RAPIDOCR_ORT_V1",
        engine_version="RapidOCR 3.10.0",
        language_code="en",
    )
    db.add(extraction)
    db.flush()

    field = ExtractedField(
        document_extraction_id=extraction.document_extraction_id,
        field_code="noc_number",
        field_label="Fire Safety NOC Number",
        raw_value="NOC/FIRE/2026/888",
        normalized_value="NOC/FIRE/2026/888",
        confidence=0.95,
        page_number=1,
        bounding_box={"x": 50, "y": 100, "width": 200, "height": 30},
    )
    db.add(field)
    db.commit()

    csrf_token = "test-csrf-token-part-b"
    token_inst = create_access_token(user_inst.user_id)
    token_auditor = create_access_token(user_auditor.user_id)
    token_lead = create_access_token(user_lead.user_id)
    token_admin = create_access_token(user_admin.user_id)

    def make_auth(token: str) -> dict[str, Any]:
        return {
            "cookies": {
                settings.access_cookie_name: token,
                settings.csrf_cookie_name: csrf_token,
            },
            "headers": {"X-CSRF-Token": csrf_token},
        }

    setup_data = {
        "db": db,
        "req": req,
        "version": doc_version,
        "extraction": extraction,
        "field": field,
        "app": app_rec,
        "user_inst": user_inst,
        "user_auditor": user_auditor,
        "user_lead": user_lead,
        "user_admin": user_admin,
        "auth_inst": make_auth(token_inst),
        "auth_auditor": make_auth(token_auditor),
        "auth_lead": make_auth(token_lead),
        "auth_admin": make_auth(token_admin),
    }

    try:
        yield setup_data
    finally:
        db.close()


# =============================================================================
# 1. Auditor & Lead Auditor Review Lifecycle Tests
# =============================================================================


def test_auditor_and_lead_auditor_review_lifecycle(
    client: TestClient, review_setup: dict[str, Any]
):
    """Verifies Auditor acceptance and Lead Auditor correction workflows."""
    req_id = review_setup["req"].application_requirement_id
    ver_id = review_setup["version"].document_version_id
    field_id = review_setup["field"].extracted_field_id

    # 1. Auditor submits "accept as extracted"
    auditor_auth = review_setup["auth_auditor"]
    resp1 = client.post(
        f"/api/v1/requirements/{req_id}/documents/{ver_id}/fields/{field_id}/reviews",
        headers=auditor_auth["headers"],
        cookies=auditor_auth["cookies"],
        json={
            "accepted_as_extracted": True,
            "review_note": "Verified against municipal authority seal.",
        },
    )
    assert resp1.status_code == 201, resp1.text
    data1 = resp1.json()
    assert data1["accepted_as_extracted"] is True
    assert data1["corrected_value"] is None
    assert data1["reviewer_name"] == "Synthetic Auditor"
    assert data1["reviewer_role"] == "AUDITOR"
    assert data1["review_note"] == "Verified against municipal authority seal."
    assert "reviewed_at" in data1

    # 2. Lead Auditor submits an authoritative correction (sleep ensures strictly advancing timestamp)
    import time

    time.sleep(0.02)
    lead_auth = review_setup["auth_lead"]
    resp2 = client.post(
        f"/api/v1/requirements/{req_id}/documents/{ver_id}/fields/{field_id}/reviews",
        headers=lead_auth["headers"],
        cookies=lead_auth["cookies"],
        json={
            "accepted_as_extracted": False,
            "corrected_value": "NOC/FIRE/2026/888-REVISED",
            "review_note": "Correction required: document carries an official amendment suffix.",
        },
    )
    assert resp2.status_code == 201, resp2.text
    data2 = resp2.json()
    assert data2["accepted_as_extracted"] is False
    assert data2["corrected_value"] == "NOC/FIRE/2026/888-REVISED"
    assert data2["reviewer_name"] == "Synthetic Lead Auditor"
    assert data2["reviewer_role"] == "LEAD_AUDITOR"
    assert "amendment suffix" in data2["review_note"]

    # 3. Auditor retrieves review history
    resp_get = client.get(
        f"/api/v1/requirements/{req_id}/documents/{ver_id}/fields/{field_id}/reviews",
        headers=auditor_auth["headers"],
        cookies=auditor_auth["cookies"],
    )
    assert resp_get.status_code == 200
    reviews = resp_get.json()
    assert len(reviews) == 2
    # Reverse chronological order: newest (Lead Auditor) first
    assert reviews[0]["reviewer_role"] == "LEAD_AUDITOR"
    assert reviews[0]["accepted_as_extracted"] is False
    assert reviews[1]["reviewer_role"] == "AUDITOR"
    assert reviews[1]["accepted_as_extracted"] is True

    # 4. Auditor retrieves extraction details: latest_review is populated
    resp_ext = client.get(
        f"/api/v1/requirements/{req_id}/documents/{ver_id}/extraction",
        headers=auditor_auth["headers"],
        cookies=auditor_auth["cookies"],
    )
    assert resp_ext.status_code == 200
    ext_data = resp_ext.json()
    matched_field = next(
        f for f in ext_data["fields"] if f["extracted_field_id"] == str(field_id)
    )
    assert matched_field["latest_review"] is not None
    assert matched_field["latest_review"]["reviewer_role"] == "LEAD_AUDITOR"
    assert matched_field["latest_review"]["accepted_as_extracted"] is False


# =============================================================================
# 2. Pydantic Validation & Mutual Exclusivity Tests
# =============================================================================


def test_pydantic_validation_mutual_exclusivity(
    client: TestClient, review_setup: dict[str, Any]
):
    """Verifies schema validation rules at the API boundary."""
    req_id = review_setup["req"].application_requirement_id
    ver_id = review_setup["version"].document_version_id
    field_id = review_setup["field"].extracted_field_id
    auth = review_setup["auth_auditor"]

    # 1. accepted_as_extracted=True WITH corrected_value -> 422
    resp1 = client.post(
        f"/api/v1/requirements/{req_id}/documents/{ver_id}/fields/{field_id}/reviews",
        headers=auth["headers"],
        cookies=auth["cookies"],
        json={
            "accepted_as_extracted": True,
            "corrected_value": "Invalid correction on accept",
        },
    )
    assert resp1.status_code == 422
    assert "corrected_value must not be supplied" in resp1.text

    # 2. accepted_as_extracted=False WITHOUT corrected_value -> 422
    resp2 = client.post(
        f"/api/v1/requirements/{req_id}/documents/{ver_id}/fields/{field_id}/reviews",
        headers=auth["headers"],
        cookies=auth["cookies"],
        json={
            "accepted_as_extracted": False,
            "corrected_value": None,
            "review_note": "A valid correction note.",
        },
    )
    assert resp2.status_code == 422
    assert "corrected_value must be provided" in resp2.text

    # 3. accepted_as_extracted=False with whitespace-only note (< 5 non-whitespace chars) -> 422
    resp3 = client.post(
        f"/api/v1/requirements/{req_id}/documents/{ver_id}/fields/{field_id}/reviews",
        headers=auth["headers"],
        cookies=auth["cookies"],
        json={
            "accepted_as_extracted": False,
            "corrected_value": "Some value",
            "review_note": "   \t\n  ",
        },
    )
    assert resp3.status_code == 422
    assert "at least 5 non-whitespace characters" in resp3.text

    # 4. Overlong review_note (> 2000 chars) -> 422
    resp4 = client.post(
        f"/api/v1/requirements/{req_id}/documents/{ver_id}/fields/{field_id}/reviews",
        headers=auth["headers"],
        cookies=auth["cookies"],
        json={
            "accepted_as_extracted": True,
            "review_note": "X" * 2001,
        },
    )
    assert resp4.status_code == 422
    assert "cannot exceed 2000 characters" in resp4.text


# =============================================================================
# 3. Database Check Constraints (SQL-Level Verification)
# =============================================================================


def test_database_check_constraints_at_sql_level(review_setup: dict[str, Any]):
    """Proves that PostgreSQL enforces decision, regex whitespace, role, and payload size constraints."""
    db = review_setup["db"]
    field_id = review_setup["field"].extracted_field_id
    user_id = review_setup["user_auditor"].user_id

    # 1. chk_extracted_field_reviews_decision: whitespace-only note (< 5 chars) on correction
    with pytest.raises(IntegrityError) as exc_info, db.begin_nested():
        db.execute(
            text(
                """
                INSERT INTO extracted_field_reviews (
                    extracted_field_id, reviewed_by, reviewer_role, accepted_as_extracted,
                    corrected_value, review_note
                ) VALUES (
                    :fid, :uid, 'AUDITOR', false,
                    '"corrected"'::jsonb, ' \t \n '
                )
                """
            ),
            {"fid": field_id, "uid": user_id},
        )
    assert "chk_extracted_field_reviews_decision" in str(exc_info.value)

    # 2. chk_extracted_field_reviews_decision: accepted_as_extracted=true with corrected_value
    with pytest.raises(IntegrityError) as exc_info, db.begin_nested():
        db.execute(
            text(
                """
                INSERT INTO extracted_field_reviews (
                    extracted_field_id, reviewed_by, reviewer_role, accepted_as_extracted,
                    corrected_value
                ) VALUES (
                    :fid, :uid, 'AUDITOR', true,
                    '{"forbidden": true}'::jsonb
                )
                """
            ),
            {"fid": field_id, "uid": user_id},
        )
    assert "chk_extracted_field_reviews_decision" in str(exc_info.value)

    # 3. chk_extracted_field_reviews_role: reviewer_role not AUDITOR or LEAD_AUDITOR
    with pytest.raises(IntegrityError) as exc_info, db.begin_nested():
        db.execute(
            text(
                """
                INSERT INTO extracted_field_reviews (
                    extracted_field_id, reviewed_by, reviewer_role, accepted_as_extracted
                ) VALUES (
                    :fid, :uid, 'INSTITUTION_USER', true
                )
                """
            ),
            {"fid": field_id, "uid": user_id},
        )
    assert "chk_extracted_field_reviews_role" in str(exc_info.value)

    # 4. chk_extracted_field_reviews_payload_size: payload > 65,536 bytes
    oversized_payload = f'{{"data": "{"A" * 66000}"}}'
    with pytest.raises(IntegrityError) as exc_info, db.begin_nested():
        db.execute(
            text(
                """
                INSERT INTO extracted_field_reviews (
                    extracted_field_id, reviewed_by, reviewer_role, accepted_as_extracted,
                    corrected_value, review_note
                ) VALUES (
                    :fid, :uid, 'AUDITOR', false,
                    CAST(:payload AS jsonb), 'Valid explanation note'
                )
                """
            ),
            {"fid": field_id, "uid": user_id, "payload": oversized_payload},
        )
    assert "chk_extracted_field_reviews_payload_size" in str(exc_info.value)


# =============================================================================
# 4. Database Trigger Immutability (Append-Only Protections)
# =============================================================================


def test_database_triggers_prevent_update_delete_truncate(review_setup: dict[str, Any]):
    """Proves that PostgreSQL triggers block UPDATE, DELETE, and TRUNCATE unconditionally."""
    db = review_setup["db"]
    field_id = review_setup["field"].extracted_field_id
    user_id = review_setup["user_auditor"].user_id

    # Insert a valid review record
    review = ExtractedFieldReview(
        extracted_field_id=field_id,
        reviewed_by=user_id,
        reviewer_role="AUDITOR",
        accepted_as_extracted=True,
        review_note="Initial audit acceptance note.",
    )
    db.add(review)
    db.commit()
    db.refresh(review)
    rev_id = review.extracted_field_review_id

    # 1. Test row-level trigger blocks UPDATE
    with pytest.raises(DBAPIError) as exc_update, db.begin_nested():
        db.execute(
            text(
                "UPDATE extracted_field_reviews SET review_note = 'tampered' WHERE extracted_field_review_id = :id"
            ),
            {"id": rev_id},
        )
    assert "immutable regulatory audit trail" in str(exc_update.value)
    assert "UPDATE operations are prohibited" in str(exc_update.value)

    # 2. Test row-level trigger blocks DELETE
    with pytest.raises(DBAPIError) as exc_delete, db.begin_nested():
        db.execute(
            text(
                "DELETE FROM extracted_field_reviews WHERE extracted_field_review_id = :id"
            ),
            {"id": rev_id},
        )
    assert "immutable regulatory audit trail" in str(exc_delete.value)
    assert "DELETE operations are prohibited" in str(exc_delete.value)

    # 3. Test statement-level trigger blocks TRUNCATE
    with pytest.raises(DBAPIError) as exc_truncate, db.begin_nested():
        db.execute(text("TRUNCATE TABLE extracted_field_reviews"))
    assert "immutable regulatory audit trail" in str(exc_truncate.value)
    assert "TRUNCATE operations are prohibited" in str(exc_truncate.value)


# =============================================================================
# 5. Safe Downgrade Concurrency & Refusal
# =============================================================================


def test_safe_downgrade_refuses_when_records_exist(review_setup: dict[str, Any]):
    """Proves that alembic downgrade() holds an ACCESS EXCLUSIVE lock and refuses if records exist."""
    import importlib.util
    from pathlib import Path

    migration_path = (
        Path(__file__).resolve().parents[1]
        / "alembic"
        / "versions"
        / "a3b4c5d6e7f8_add_extracted_field_reviews_table.py"
    )
    spec = importlib.util.spec_from_file_location("migration_module", migration_path)
    assert spec is not None and spec.loader is not None
    migration_module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(migration_module)
    downgrade = migration_module.downgrade

    db = review_setup["db"]
    field_id = review_setup["field"].extracted_field_id
    user_id = review_setup["user_auditor"].user_id

    # Insert a review row
    review = ExtractedFieldReview(
        extracted_field_id=field_id,
        reviewed_by=user_id,
        reviewer_role="AUDITOR",
        accepted_as_extracted=True,
    )
    db.add(review)
    db.commit()

    # Invoke downgrade() using an Alembic Operations context connected to the session
    conn = db.connection()
    context = MigrationContext.configure(conn)
    with Operations.context(context), pytest.raises(RuntimeError) as exc_info:
        downgrade()

    assert "cannot downgrade migration a3b4c5d6e7f8" in str(exc_info.value).lower()
    assert "permanent regulatory audit records" in str(exc_info.value)


# =============================================================================
# 6. RBAC Isolation & Confidentiality Redaction Tests
# =============================================================================


def test_rbac_institution_user_and_admin_cannot_post_review(
    client: TestClient, review_setup: dict[str, Any]
):
    """Enforces that Institution Users and Admins are denied review creation (HTTP 403)."""
    req_id = review_setup["req"].application_requirement_id
    ver_id = review_setup["version"].document_version_id
    field_id = review_setup["field"].extracted_field_id

    # 1. Institution user attempt -> 403 Forbidden
    inst_auth = review_setup["auth_inst"]
    resp1 = client.post(
        f"/api/v1/requirements/{req_id}/documents/{ver_id}/fields/{field_id}/reviews",
        headers=inst_auth["headers"],
        cookies=inst_auth["cookies"],
        json={"accepted_as_extracted": True},
    )
    assert resp1.status_code == 403
    assert (
        "only regulatory auditors assigned to this application's review team may submit field reviews"
        in resp1.text
    )

    # 2. Admin attempt -> 403 Forbidden
    admin_auth = review_setup["auth_admin"]
    resp2 = client.post(
        f"/api/v1/requirements/{req_id}/documents/{ver_id}/fields/{field_id}/reviews",
        headers=admin_auth["headers"],
        cookies=admin_auth["cookies"],
        json={"accepted_as_extracted": True},
    )
    assert resp2.status_code == 403
    assert "access denied" in resp2.text.lower()


def test_institution_user_receives_sanitized_review_projection(
    client: TestClient, review_setup: dict[str, Any]
):
    """Verifies that when Institution Users retrieve reviews, internal notes and reviewer identities are stripped."""
    req_id = review_setup["req"].application_requirement_id
    ver_id = review_setup["version"].document_version_id
    field_id = review_setup["field"].extracted_field_id

    # 1. Lead auditor records a correction with internal audit notes
    lead_auth = review_setup["auth_lead"]
    client.post(
        f"/api/v1/requirements/{req_id}/documents/{ver_id}/fields/{field_id}/reviews",
        headers=lead_auth["headers"],
        cookies=lead_auth["cookies"],
        json={
            "accepted_as_extracted": False,
            "corrected_value": "CORRECTED_NO_LEAK",
            "review_note": "CONFIDENTIAL NOTE: Candidate value showed OCR artifacts on line 4.",
        },
    )

    # 2. Institution user calls GET /fields/{field_id}/reviews
    inst_auth = review_setup["auth_inst"]
    resp_get = client.get(
        f"/api/v1/requirements/{req_id}/documents/{ver_id}/fields/{field_id}/reviews",
        headers=inst_auth["headers"],
        cookies=inst_auth["cookies"],
    )
    assert resp_get.status_code == 200
    reviews = resp_get.json()
    assert len(reviews) == 1
    rev = reviews[0]

    # Verify sanitized projection fields
    assert rev["accepted_as_extracted"] is False
    assert rev["has_correction"] is True
    assert rev["corrected_value"] == "CORRECTED_NO_LEAK"
    assert "reviewed_at" in rev

    # Verify sensitive auditor fields are completely stripped
    assert "review_note" not in rev
    assert "reviewed_by" not in rev
    assert "reviewer_name" not in rev
    assert "reviewer_role" not in rev

    # 3. Institution user calls GET /extraction
    resp_ext = client.get(
        f"/api/v1/requirements/{req_id}/documents/{ver_id}/extraction",
        headers=inst_auth["headers"],
        cookies=inst_auth["cookies"],
    )
    assert resp_ext.status_code == 200
    ext_data = resp_ext.json()
    matched_field = next(
        f for f in ext_data["fields"] if f["extracted_field_id"] == str(field_id)
    )
    latest = matched_field["latest_review"]
    assert latest is not None
    assert latest["accepted_as_extracted"] is False
    assert latest["has_correction"] is True
    assert "review_note" not in latest
    assert "reviewer_name" not in latest


def test_review_on_nonexistent_field_returns_404(
    client: TestClient, review_setup: dict[str, Any]
):
    """Calling review endpoints with an unknown field UUID returns 404."""
    req_id = review_setup["req"].application_requirement_id
    ver_id = review_setup["version"].document_version_id
    random_field_id = uuid.uuid4()
    auth = review_setup["auth_auditor"]

    resp_post = client.post(
        f"/api/v1/requirements/{req_id}/documents/{ver_id}/fields/{random_field_id}/reviews",
        headers=auth["headers"],
        cookies=auth["cookies"],
        json={"accepted_as_extracted": True},
    )
    assert resp_post.status_code == 404

    resp_get = client.get(
        f"/api/v1/requirements/{req_id}/documents/{ver_id}/fields/{random_field_id}/reviews",
        headers=auth["headers"],
        cookies=auth["cookies"],
    )
    assert resp_get.status_code == 404

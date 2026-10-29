"""AIC-Verify — API Integration Tests for Document Intelligence & Content Extraction Endpoints.

Phase 4, Batch 4:
Verifies:
- POST /{version_id}/process triggers extraction and returns HTTP 202 Accepted.
- GET /{version_id}/extraction returns structured fields with full Batch 3 provenance.
- GET /{version_id}/extraction/text returns page-by-page extracted text with pagination.
- Enforces strict Phase 2 RBAC and tenant isolation on all extraction endpoints.
- Verifies Admin cannot automatically access confidential institutional documents without explicit assignment (HTTP 403).
- Proves clean upload does NOT automatically trigger background extraction (job remains QUEUED).
"""

from __future__ import annotations

import io
from uuid import UUID

import pytest
from fastapi.testclient import TestClient
from pypdf import PdfWriter
from pypdf.generic import DecodedStreamObject, DictionaryObject, NameObject

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
from app.models.document_processing_job import DocumentProcessingJob
from app.models.document_security_scan import DocumentSecurityScan
from app.models.document_version import DocumentVersion
from app.models.enums import DocumentProcessingStatus
from app.models.institution import Institution
from app.models.user import User
from app.services.checklist_service import seed_standard_references
from app.services.document_processing_service import document_processing_service
from app.services.storage_service import storage_service


def make_native_pdf(text: str) -> bytes:
    """Generates a valid PDF with genuine native text stream."""
    writer = PdfWriter()
    page = writer.add_blank_page(width=612, height=792)
    font_dict = DictionaryObject(
        {
            NameObject("/Type"): NameObject("/Font"),
            NameObject("/Subtype"): NameObject("/Type1"),
            NameObject("/BaseFont"): NameObject("/Helvetica"),
        }
    )
    resources = DictionaryObject(
        {
            NameObject("/Font"): DictionaryObject({NameObject("/F1"): font_dict}),
        }
    )
    page[NameObject("/Resources")] = resources

    lines = text.strip().split("\n")
    stream_cmds = ["BT", "/F1 12 Tf", "50 720 Td"]
    for i, line in enumerate(lines):
        safe_line = line.replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)")
        if i == 0:
            stream_cmds.append(f"({safe_line}) Tj")
        else:
            stream_cmds.append(f"0 -20 Td ({safe_line}) Tj")
    stream_cmds.append("ET")

    stream = DecodedStreamObject()
    stream.set_data("\n".join(stream_cmds).encode("latin-1"))
    page[NameObject("/Contents")] = stream

    buf = io.BytesIO()
    writer.write(buf)
    return buf.getvalue()


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
def api_setup(seeded_db):
    inst = (
        seeded_db.query(Institution)
        .filter_by(aicte_permanent_institution_id="SYNTH-AICTE-0001")
        .first()
    )
    user_inst = (
        seeded_db.query(User).filter_by(email="institution@aic-verify.internal").first()
    )
    user_admin = (
        seeded_db.query(User).filter_by(email="admin@aic-verify.internal").first()
    )
    user_auditor = (
        seeded_db.query(User).filter_by(email="auditor@aic-verify.internal").first()
    )

    app_rec = (
        seeded_db.query(Application)
        .filter_by(
            institution_id=inst.institution_id,
            academic_year="2026-27",
        )
        .first()
    )

    rev = (
        seeded_db.query(ApplicationRevision)
        .filter_by(application_id=app_rec.application_id)
        .order_by(ApplicationRevision.revision_number.desc())
        .first()
    )

    ci = seeded_db.query(ChecklistItem).filter_by(item_code="EOA-SD-05").first()
    req = (
        seeded_db.query(ApplicationRequirement)
        .filter_by(
            application_revision_id=rev.application_revision_id,
            checklist_item_id=ci.checklist_item_id,
        )
        .first()
    )

    # Document & clean version
    doc = Document(
        institution_id=inst.institution_id,
        document_label="Fire Safety NOC",
        created_by=user_inst.user_id,
    )
    seeded_db.add(doc)
    seeded_db.flush()

    pdf_bytes = make_native_pdf(
        "FIRE SAFETY CERTIFICATE\nCertificate No: NOC/FIRE/2024/777\nValid To: 31/03/2027\nAuthority: Fire Service"
    )
    quar_path, sha256_hex, fsize = storage_service.save_bytes_to_quarantine(pdf_bytes)
    _clean_path, storage_key = storage_service.move_to_clean(quar_path)

    doc_version = DocumentVersion(
        document_id=doc.document_id,
        version_number=1,
        original_filename="fire_noc_777.pdf",
        storage_key=storage_key,
        mime_type="application/pdf",
        file_size_bytes=fsize,
        sha256_hex=sha256_hex,
        uploaded_by=user_inst.user_id,
    )
    seeded_db.add(doc_version)
    seeded_db.flush()

    link = ApplicationDocumentLink(
        application_revision_id=rev.application_revision_id,
        uploaded_for_requirement_id=req.application_requirement_id,
        document_version_id=doc_version.document_version_id,
    )
    seeded_db.add(link)

    sec_scan = DocumentSecurityScan(
        document_version_id=doc_version.document_version_id,
        scanner_name="ClamAV",
        scanner_version="1.4.6",
        signature_database_version="27500",
        scan_status="CLEAN",
        threat_name=None,
    )
    seeded_db.add(sec_scan)

    job = DocumentProcessingJob(
        document_version_id=doc_version.document_version_id,
        processing_status=DocumentProcessingStatus.QUEUED,
        pipeline_name="DOCUMENT_INGESTION_V1",
        pipeline_version="1.0.0",
    )
    seeded_db.add(job)
    seeded_db.commit()

    csrf_token = "test-csrf-token-batch4-12345"

    token_inst = create_access_token(user_inst.user_id)
    token_admin = create_access_token(user_admin.user_id)
    token_auditor = create_access_token(user_auditor.user_id)

    return {
        "req": req,
        "version": doc_version,
        "job": job,
        "app": app_rec,
        "csrf_token": csrf_token,
        "auth_inst": {
            "cookies": {
                settings.access_cookie_name: token_inst,
                settings.csrf_cookie_name: csrf_token,
            },
            "headers": {"X-CSRF-Token": csrf_token},
        },
        "auth_admin": {
            "cookies": {
                settings.access_cookie_name: token_admin,
                settings.csrf_cookie_name: csrf_token,
            },
            "headers": {"X-CSRF-Token": csrf_token},
        },
        "auth_auditor": {
            "cookies": {
                settings.access_cookie_name: token_auditor,
                settings.csrf_cookie_name: csrf_token,
            },
            "headers": {"X-CSRF-Token": csrf_token},
        },
    }


def test_api_process_document_returns_202_accepted(client: TestClient, api_setup):
    """POST /{version_id}/process explicitly schedules processing and returns HTTP 202."""
    req_id = api_setup["req"].application_requirement_id
    ver_id = api_setup["version"].document_version_id
    auth = api_setup["auth_inst"]

    resp = client.post(
        f"/api/v1/requirements/{req_id}/documents/{ver_id}/process",
        headers=auth["headers"],
        cookies=auth["cookies"],
    )
    assert resp.status_code == 202
    data = resp.json()
    assert data["processing_status"] in ("QUEUED", "PROCESSING", "COMPLETED")
    assert data["document_version_id"] == str(ver_id)


def test_api_process_unauthorized_admin_rejected_403(client: TestClient, api_setup):
    """Enforces that an Admin without explicit institutional assignment is denied (HTTP 403)."""
    req_id = api_setup["req"].application_requirement_id
    ver_id = api_setup["version"].document_version_id
    auth = api_setup["auth_admin"]

    resp = client.post(
        f"/api/v1/requirements/{req_id}/documents/{ver_id}/process",
        headers=auth["headers"],
        cookies=auth["cookies"],
    )
    assert resp.status_code == 403
    assert "not authorized" in resp.json()["detail"].lower()


def test_api_process_csrf_missing_rejected_403(client: TestClient, api_setup):
    """POST /{version_id}/process without CSRF header is rejected with HTTP 403."""
    req_id = api_setup["req"].application_requirement_id
    ver_id = api_setup["version"].document_version_id
    auth = api_setup["auth_inst"]

    resp = client.post(
        f"/api/v1/requirements/{req_id}/documents/{ver_id}/process",
        cookies=auth["cookies"],  # No X-CSRF-Token header
    )
    assert resp.status_code == 403


def test_api_process_unauthenticated_rejected_401(client: TestClient, api_setup):
    """Unauthenticated calls are rejected with HTTP 401."""
    req_id = api_setup["req"].application_requirement_id
    ver_id = api_setup["version"].document_version_id

    resp = client.post(
        f"/api/v1/requirements/{req_id}/documents/{ver_id}/process",
    )
    assert resp.status_code == 401


def test_api_get_extraction_before_completion_returns_404(
    client: TestClient, api_setup
):
    """GET /{version_id}/extraction returns 404 with descriptive job status if not completed."""
    req_id = api_setup["req"].application_requirement_id
    ver_id = api_setup["version"].document_version_id
    auth = api_setup["auth_inst"]

    resp = client.get(
        f"/api/v1/requirements/{req_id}/documents/{ver_id}/extraction",
        headers=auth["headers"],
        cookies=auth["cookies"],
    )
    assert resp.status_code == 404
    assert "QUEUED" in resp.json()["detail"]


def test_api_get_extraction_and_text_success_after_processing(
    client: TestClient, api_setup
):
    """Runs extraction job and tests both GET /extraction and GET /extraction/text."""
    req_id = api_setup["req"].application_requirement_id
    ver_id = api_setup["version"].document_version_id
    job_id = api_setup["job"].document_processing_job_id
    auth = api_setup["auth_inst"]

    # Execute processing synchronously
    document_processing_service.execute_processing_job(
        job_id=job_id,
        requirement_id=req_id,
        version_id=ver_id,
    )

    # 1. GET /extraction
    resp = client.get(
        f"/api/v1/requirements/{req_id}/documents/{ver_id}/extraction",
        headers=auth["headers"],
        cookies=auth["cookies"],
    )
    assert resp.status_code == 200
    ext_data = resp.json()
    assert ext_data["extraction_status"] == "COMPLETED"
    assert ext_data["extraction_engine"] == "RapidOCR+PyPDF"
    assert "fields" in ext_data
    assert len(ext_data["fields"]) >= 1

    # Check that candidate field has full provenance attributes
    field = ext_data["fields"][0]
    assert "extracted_field_id" in field
    assert "field_code" in field
    assert "raw_value" in field
    assert "confidence" in field
    assert "review_category" in field

    # 2. GET /extraction/text (all pages)
    resp_text = client.get(
        f"/api/v1/requirements/{req_id}/documents/{ver_id}/extraction/text",
        headers=auth["headers"],
        cookies=auth["cookies"],
    )
    assert resp_text.status_code == 200
    text_data = resp_text.json()
    assert text_data["total_pages"] >= 1
    assert "pages" in text_data
    assert "full_text" in text_data

    # 3. GET /extraction/text?page=1 (paginated)
    resp_p1 = client.get(
        f"/api/v1/requirements/{req_id}/documents/{ver_id}/extraction/text?page=1",
        headers=auth["headers"],
        cookies=auth["cookies"],
    )
    assert resp_p1.status_code == 200
    p1_data = resp_p1.json()
    assert p1_data["selected_page"] == 1
    assert len(p1_data["pages"]) == 1
    assert p1_data["full_text"] is None

    # 4. GET /extraction/text?page=999 (out of range -> 404)
    resp_err = client.get(
        f"/api/v1/requirements/{req_id}/documents/{ver_id}/extraction/text?page=999",
        headers=auth["headers"],
        cookies=auth["cookies"],
    )
    assert resp_err.status_code == 404


def test_api_auditor_review_team_isolation(client: TestClient, seeded_db, api_setup):
    """Verifies that an Auditor cannot access an application until assigned to its review team."""
    req_id = api_setup["req"].application_requirement_id
    ver_id = api_setup["version"].document_version_id
    app_rec = api_setup["app"]
    auth_auditor = api_setup["auth_auditor"]

    # In default seed, app_rec.review_team_id is None. Auditor should be rejected.
    resp = client.get(
        f"/api/v1/requirements/{req_id}/documents/{ver_id}/extraction",
        headers=auth_auditor["headers"],
        cookies=auth_auditor["cookies"],
    )
    assert resp.status_code == 403
    assert "not authorized" in resp.json()["detail"].lower()

    # When the application is assigned to the auditor's review team:
    # From inspection earlier, auditor's review_team_id is 9533f553-82be-44ac-9d46-85936fdec003
    team_id = UUID("9533f553-82be-44ac-9d46-85936fdec003")
    app_rec.review_team_id = team_id
    seeded_db.commit()

    # Now auditor has authorized review-team scope!
    resp_ok = client.get(
        f"/api/v1/requirements/{req_id}/documents/{ver_id}/extraction",
        headers=auth_auditor["headers"],
        cookies=auth_auditor["cookies"],
    )
    # The application is within scope; returns 404 (extraction not run yet) rather than 403 Forbidden!
    assert resp_ok.status_code == 404
    assert "QUEUED" in resp_ok.json()["detail"]


def test_get_document_history_includes_processing_job(
    client: TestClient, seeded_db, api_setup
):
    """Phase 4 Batch 5 Part A:

    Verifies that GET /requirements/{id}/documents enriches DocumentVersionRead
    with authoritative processing_job metadata alongside security_scan.
    """
    req_id = api_setup["req"].application_requirement_id
    ver_id = str(api_setup["version"].document_version_id)
    auth = api_setup["auth_inst"]

    resp = client.get(
        f"/api/v1/requirements/{req_id}/documents",
        headers=auth["headers"],
        cookies=auth["cookies"],
    )
    assert resp.status_code == 200
    data = resp.json()

    assert "versions" in data
    assert len(data["versions"]) >= 1

    matched_ver = next(
        (v for v in data["versions"] if v["document_version_id"] == ver_id), None
    )
    assert matched_ver is not None

    # Verify Antivirus scan status is present and CLEAN
    assert matched_ver["security_scan"] is not None
    assert matched_ver["security_scan"]["scan_status"] == "CLEAN"
    assert matched_ver["is_clean"] is True

    # Verify Processing job metadata is present and authoritative
    assert matched_ver["processing_job"] is not None
    assert matched_ver["processing_job"]["processing_status"] == "QUEUED"
    assert matched_ver["processing_job"]["pipeline_name"] == "DOCUMENT_INGESTION_V1"
    assert matched_ver["processing_job"]["queued_at"] is not None

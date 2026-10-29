import io
import sys
from pathlib import Path

# Ensure backend root is in sys.path
BACKEND_DIR = str(Path(__file__).resolve().parents[1])
if BACKEND_DIR not in sys.path:
    sys.path.insert(0, BACKEND_DIR)

import pytest
from fastapi.testclient import TestClient
from PIL import Image
from pypdf import PdfWriter
from pypdf.generic import DecodedStreamObject, NameObject
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.security import create_access_token
from app.db.session import SessionLocal
from app.main import app
from app.models.application import Application
from app.models.application_requirements import ApplicationRequirement
from app.models.application_revision import ApplicationRevision
from app.models.checklist_item import ChecklistItem
from app.models.document_version import DocumentVersion
from app.models.institution import Institution
from app.models.user import User
from app.services.checklist_service import seed_standard_references
from app.services.document_upload_service import document_upload_service
from app.services.malware_scanner import (
    EICAR_BYTE_SIGNATURE,
    BaseMalwareScanner,
    ClamAVScanner,
    ScanResult,
)
from app.services.storage_service import storage_service


def make_valid_pdf(title: str = "Synthetic Document", pages: int = 1) -> bytes:
    writer = PdfWriter()
    for _ in range(pages):
        writer.add_blank_page(width=100, height=100)
    writer.add_metadata({"/Title": title})
    buf = io.BytesIO()
    writer.write(buf)
    return buf.getvalue()


def make_eicar_pdf() -> bytes:
    writer = PdfWriter()
    page = writer.add_blank_page(width=100, height=100)
    stream = DecodedStreamObject()
    stream.set_data(EICAR_BYTE_SIGNATURE)
    page[NameObject("/Contents")] = stream
    buf = io.BytesIO()
    writer.write(buf)
    return buf.getvalue()


def make_valid_png(width: int = 10, height: int = 10, color: str = "blue") -> bytes:
    buf = io.BytesIO()
    Image.new("RGB", (width, height), color=color).save(buf, format="PNG")
    return buf.getvalue()


def make_valid_jpeg(width: int = 10, height: int = 10, color: str = "green") -> bytes:
    buf = io.BytesIO()
    Image.new("RGB", (width, height), color=color).save(buf, format="JPEG")
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
def auth_headers_institution(seeded_db):
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
    csrf_token = "test-csrf-token-docs-12345"

    return {
        "institution_id": inst.institution_id,
        "user_id": user.user_id,
        "cookies": {
            settings.access_cookie_name: token,
            settings.csrf_cookie_name: csrf_token,
        },
        "headers": {
            "X-CSRF-Token": csrf_token,
        },
    }


@pytest.fixture
def test_requirement(seeded_db, auth_headers_institution):
    """Finds active EOA-SD-01 requirement for the synthetic institution."""
    app_record = (
        seeded_db.query(Application)
        .filter_by(
            institution_id=auth_headers_institution["institution_id"],
            academic_year="2026-27",
        )
        .first()
    )
    assert app_record is not None, "Active test application must exist"

    rev = (
        seeded_db.query(ApplicationRevision)
        .filter_by(application_id=app_record.application_id)
        .order_by(ApplicationRevision.revision_number.desc())
        .first()
    )
    assert rev is not None

    item = seeded_db.query(ChecklistItem).filter_by(item_code="EOA-SD-01").first()
    assert item is not None

    req = (
        seeded_db.query(ApplicationRequirement)
        .filter_by(
            application_revision_id=rev.application_revision_id,
            checklist_item_id=item.checklist_item_id,
        )
        .first()
    )
    assert req is not None
    return req


# ==============================================================================
# Base Format & Anti-malware Tests
# ==============================================================================


def test_file_validation_rejections(client, auth_headers_institution, test_requirement):
    req_id = test_requirement.application_requirement_id

    # 1. Reject invalid extension (.exe)
    resp = client.post(
        f"/api/v1/requirements/{req_id}/documents",
        files={
            "file": (
                "malicious.exe",
                b"MZ\x90\x00executable content",
                "application/octet-stream",
            )
        },
        cookies=auth_headers_institution["cookies"],
        headers=auth_headers_institution["headers"],
    )
    assert resp.status_code == 400
    assert "Unsupported file format" in resp.json()["detail"]

    # 2. Reject empty file (0 bytes)
    resp = client.post(
        f"/api/v1/requirements/{req_id}/documents",
        files={"file": ("empty.pdf", b"", "application/pdf")},
        cookies=auth_headers_institution["cookies"],
        headers=auth_headers_institution["headers"],
    )
    assert resp.status_code == 400
    assert "empty" in resp.json()["detail"].lower()

    # 3. Reject spoofed PDF (starts with non-PDF bytes)
    resp = client.post(
        f"/api/v1/requirements/{req_id}/documents",
        files={"file": ("spoofed.pdf", b"NOT_A_PDF_CONTENT %%EOF", "application/pdf")},
        cookies=auth_headers_institution["cookies"],
        headers=auth_headers_institution["headers"],
    )
    assert resp.status_code == 400
    assert "%PDF-" in resp.json()["detail"]


def test_clean_document_upload_and_download(
    client, auth_headers_institution, test_requirement, seeded_db
):
    req_id = test_requirement.application_requirement_id

    # Build valid synthetic PDF
    pdf_content = make_valid_pdf(title="Synthetic Affidavit 2")

    resp = client.post(
        f"/api/v1/requirements/{req_id}/documents",
        files={"file": ("affidavit_v1.pdf", pdf_content, "application/pdf")},
        cookies=auth_headers_institution["cookies"],
        headers=auth_headers_institution["headers"],
    )
    assert resp.status_code == 201, resp.text
    data = resp.json()

    assert data["requirement_status"] == "UPLOADED"
    doc_ver = data["document_version"]
    assert doc_ver["version_number"] >= 1
    assert doc_ver["original_filename"] == "affidavit_v1.pdf"
    assert doc_ver["mime_type"] == "application/pdf"
    assert doc_ver["is_clean"] is True
    assert doc_ver["is_downloadable"] is True
    assert doc_ver["security_scan"]["scan_status"] == "CLEAN"
    assert doc_ver["security_scan"]["threat_name"] is None

    version_id = doc_ver["document_version_id"]

    # Test Download
    dl_resp = client.get(
        f"/api/v1/requirements/{req_id}/documents/{version_id}/download",
        cookies=auth_headers_institution["cookies"],
    )
    assert dl_resp.status_code == 200
    assert dl_resp.content == pdf_content
    assert "attachment" in dl_resp.headers["content-disposition"]
    assert dl_resp.headers["x-content-type-options"] == "nosniff"


def test_eicar_replacement_rejection_and_version_preservation(
    client, auth_headers_institution, test_requirement
):
    """Demonstrates:

    1. Clean version 1 already uploaded.
    2. Upload infected replacement containing EICAR -> DETECTED, Version rejected.
    3. Download of infected version is blocked (403 Forbidden).
    4. Active clean version is preserved.
    """
    req_id = test_requirement.application_requirement_id

    # 1. Establish clean baseline version 1
    clean_pdf = make_valid_pdf(title="Affidavit Baseline")
    v1_resp = client.post(
        f"/api/v1/requirements/{req_id}/documents",
        files={"file": ("affidavit_v1.pdf", clean_pdf, "application/pdf")},
        cookies=auth_headers_institution["cookies"],
        headers=auth_headers_institution["headers"],
    )
    assert v1_resp.status_code == 201

    # 2. Create infected PDF with embedded EICAR stream
    infected_pdf = make_eicar_pdf()

    resp = client.post(
        f"/api/v1/requirements/{req_id}/documents",
        files={
            "file": (
                "affidavit_revised_eicar.pdf",
                infected_pdf,
                "application/pdf",
            )
        },
        cookies=auth_headers_institution["cookies"],
        headers=auth_headers_institution["headers"],
    )
    assert resp.status_code == 201, resp.text
    data = resp.json()

    doc_ver = data["document_version"]
    assert doc_ver["original_filename"] == "affidavit_revised_eicar.pdf"
    assert doc_ver["security_scan"]["scan_status"] == "DETECTED"
    assert "Eicar" in doc_ver["security_scan"]["threat_name"]
    assert doc_ver["is_clean"] is False
    assert doc_ver["is_downloadable"] is False

    # Requirement status MUST remain UPLOADED because previous version was clean!
    assert data["requirement_status"] == "UPLOADED"

    infected_version_id = doc_ver["document_version_id"]

    # Verify download of infected version is blocked
    dl_resp = client.get(
        f"/api/v1/requirements/{req_id}/documents/{infected_version_id}/download",
        cookies=auth_headers_institution["cookies"],
    )
    assert dl_resp.status_code == 403
    assert "malware" in dl_resp.json()["detail"].lower()

    # Query document history
    hist_resp = client.get(
        f"/api/v1/requirements/{req_id}/documents",
        cookies=auth_headers_institution["cookies"],
    )
    assert hist_resp.status_code == 200
    hist = hist_resp.json()
    assert hist["requirement_status"] == "UPLOADED"
    assert hist["active_version_id"] is not None
    assert hist["active_version_id"] != infected_version_id

    versions = hist["versions"]
    assert len(versions) >= 2
    assert versions[0]["document_version_id"] == infected_version_id
    assert versions[0]["is_clean"] is False

    clean_v = next(v for v in versions if v["is_clean"])
    assert clean_v["document_version_id"] == hist["active_version_id"]
    assert clean_v["is_downloadable"] is True


def test_csrf_and_unauthorized_upload(
    client, auth_headers_institution, test_requirement
):
    req_id = test_requirement.application_requirement_id
    pdf_content = make_valid_pdf()

    # 1. Missing authentication
    resp = client.post(
        f"/api/v1/requirements/{req_id}/documents",
        files={"file": ("doc.pdf", pdf_content, "application/pdf")},
    )
    assert resp.status_code == 401

    # 2. Missing CSRF header
    resp = client.post(
        f"/api/v1/requirements/{req_id}/documents",
        files={"file": ("doc.pdf", pdf_content, "application/pdf")},
        cookies=auth_headers_institution["cookies"],
    )
    assert resp.status_code == 403
    assert "CSRF" in resp.json()["detail"]


def test_valid_image_uploads(client, auth_headers_institution, seeded_db):
    """Verifies image evidence uploads specifically for EOA-SD-06 (Satellite map / site plan)."""
    app_record = (
        seeded_db.query(Application)
        .filter_by(
            institution_id=auth_headers_institution["institution_id"],
            academic_year="2026-27",
        )
        .first()
    )
    rev = (
        seeded_db.query(ApplicationRevision)
        .filter_by(application_id=app_record.application_id)
        .order_by(ApplicationRevision.revision_number.desc())
        .first()
    )
    item = seeded_db.query(ChecklistItem).filter_by(item_code="EOA-SD-06").first()
    req = (
        seeded_db.query(ApplicationRequirement)
        .filter_by(
            application_revision_id=rev.application_revision_id,
            checklist_item_id=item.checklist_item_id,
        )
        .first()
    )
    req_id = req.application_requirement_id

    # PNG test
    png_content = make_valid_png(width=50, height=50)
    resp = client.post(
        f"/api/v1/requirements/{req_id}/documents",
        files={"file": ("satellite_map.png", png_content, "image/png")},
        cookies=auth_headers_institution["cookies"],
        headers=auth_headers_institution["headers"],
    )
    assert resp.status_code == 201
    assert resp.json()["document_version"]["mime_type"] == "image/png"

    # JPEG test
    jpeg_content = make_valid_jpeg(width=50, height=50)
    resp = client.post(
        f"/api/v1/requirements/{req_id}/documents",
        files={"file": ("site_photo.jpg", jpeg_content, "image/jpeg")},
        cookies=auth_headers_institution["cookies"],
        headers=auth_headers_institution["headers"],
    )
    assert resp.status_code == 201
    assert resp.json()["document_version"]["mime_type"] == "image/jpeg"


def test_corrupt_pdf_trailer_rejected(
    client, auth_headers_institution, test_requirement
):
    req_id = test_requirement.application_requirement_id
    corrupt_pdf = b"%PDF-1.4\n1 0 obj<< /Title (Incomplete) >>endobj\n"
    resp = client.post(
        f"/api/v1/requirements/{req_id}/documents",
        files={"file": ("incomplete.pdf", corrupt_pdf, "application/pdf")},
        cookies=auth_headers_institution["cookies"],
        headers=auth_headers_institution["headers"],
    )
    assert resp.status_code == 400
    assert "eof" in resp.json()["detail"].lower()


# ==============================================================================
# PDF & Image Structural Validation Tests
# ==============================================================================


def test_encrypted_pdf_rejected(client, auth_headers_institution, test_requirement):
    req_id = test_requirement.application_requirement_id
    writer = PdfWriter()
    writer.add_blank_page(width=100, height=100)
    writer.encrypt("secret_password")
    buf = io.BytesIO()
    writer.write(buf)

    resp = client.post(
        f"/api/v1/requirements/{req_id}/documents",
        files={"file": ("encrypted.pdf", buf.getvalue(), "application/pdf")},
        cookies=auth_headers_institution["cookies"],
        headers=auth_headers_institution["headers"],
    )
    assert resp.status_code == 400
    assert "encrypted" in resp.json()["detail"].lower()


def test_zero_page_pdf_rejected(client, auth_headers_institution, test_requirement):
    req_id = test_requirement.application_requirement_id
    writer = PdfWriter()
    buf = io.BytesIO()
    writer.write(buf)

    resp = client.post(
        f"/api/v1/requirements/{req_id}/documents",
        files={"file": ("zero_page.pdf", buf.getvalue(), "application/pdf")},
        cookies=auth_headers_institution["cookies"],
        headers=auth_headers_institution["headers"],
    )
    assert resp.status_code == 400
    assert "zero pages" in resp.json()["detail"].lower()


def test_excessive_page_count_pdf_rejected(
    client, auth_headers_institution, test_requirement, monkeypatch
):
    req_id = test_requirement.application_requirement_id
    from app.services.document_validation_service import (
        document_validation_service,
    )

    monkeypatch.setattr(document_validation_service, "max_pdf_pages", 5)
    pdf_6_pages = make_valid_pdf(pages=6)

    resp = client.post(
        f"/api/v1/requirements/{req_id}/documents",
        files={"file": ("too_many_pages.pdf", pdf_6_pages, "application/pdf")},
        cookies=auth_headers_institution["cookies"],
        headers=auth_headers_institution["headers"],
    )
    assert resp.status_code == 400
    assert "page count" in resp.json()["detail"].lower()
    assert "limit" in resp.json()["detail"].lower()


def test_png_trailing_payload_rejected(
    client, auth_headers_institution, test_requirement
):
    req_id = test_requirement.application_requirement_id
    valid_png = make_valid_png()
    malicious_png = valid_png + b"TRAILING_MALICIOUS_PAYLOAD_BYTES"

    resp = client.post(
        f"/api/v1/requirements/{req_id}/documents",
        files={"file": ("trailing.png", malicious_png, "image/png")},
        cookies=auth_headers_institution["cookies"],
        headers=auth_headers_institution["headers"],
    )
    assert resp.status_code == 400
    assert "trailing data" in resp.json()["detail"].lower()


def test_jpeg_trailing_payload_rejected(
    client, auth_headers_institution, test_requirement
):
    req_id = test_requirement.application_requirement_id
    valid_jpeg = make_valid_jpeg()
    malicious_jpeg = valid_jpeg + b"EXTRA_TRAILING_PAYLOAD"

    resp = client.post(
        f"/api/v1/requirements/{req_id}/documents",
        files={"file": ("trailing.jpg", malicious_jpeg, "image/jpeg")},
        cookies=auth_headers_institution["cookies"],
        headers=auth_headers_institution["headers"],
    )
    assert resp.status_code == 400
    assert "trailing data" in resp.json()["detail"].lower()


# ==============================================================================
# 12 Missing Focused Security Tests
# ==============================================================================


def test_upload_exceeds_max_size_rejected_413(
    client, auth_headers_institution, test_requirement, monkeypatch
):
    """Test 1: Upload exceeding maximum allowed size is rejected with HTTP 413."""
    req_id = test_requirement.application_requirement_id
    # Temporarily set max_upload_size_bytes to 500 bytes for fast deterministic testing
    monkeypatch.setattr(settings, "max_upload_size_bytes", 500)
    oversized = make_valid_pdf(pages=5)  # ~1.2 KB

    resp = client.post(
        f"/api/v1/requirements/{req_id}/documents",
        files={"file": ("oversized.pdf", oversized, "application/pdf")},
        cookies=auth_headers_institution["cookies"],
        headers=auth_headers_institution["headers"],
    )
    assert resp.status_code == 413
    assert "exceeds maximum allowed size" in resp.json()["detail"]


def test_posix_path_traversal_filename_sanitized(
    client, auth_headers_institution, test_requirement
):
    """Test 2: POSIX path traversal in filename is sanitized."""
    req_id = test_requirement.application_requirement_id
    pdf_content = make_valid_pdf(title="POSIX Traversal Test")

    resp = client.post(
        f"/api/v1/requirements/{req_id}/documents",
        files={"file": ("../../../../etc/passwd.pdf", pdf_content, "application/pdf")},
        cookies=auth_headers_institution["cookies"],
        headers=auth_headers_institution["headers"],
    )
    assert resp.status_code == 201
    assert resp.json()["document_version"]["original_filename"] == "passwd.pdf"


def test_windows_path_traversal_filename_sanitized(
    client, auth_headers_institution, test_requirement
):
    """Test 3: Windows backslash path traversal in filename is sanitized."""
    req_id = test_requirement.application_requirement_id
    pdf_content = make_valid_pdf(title="Win Traversal Test")

    resp = client.post(
        f"/api/v1/requirements/{req_id}/documents",
        files={
            "file": (
                "..\\..\\..\\windows\\win.ini.pdf",
                pdf_content,
                "application/pdf",
            )
        },
        cookies=auth_headers_institution["cookies"],
        headers=auth_headers_institution["headers"],
    )
    assert resp.status_code == 201
    assert resp.json()["document_version"]["original_filename"] == "win.ini.pdf"


def test_null_byte_and_overlong_filename_rejected_400(
    client, auth_headers_institution, test_requirement
):
    """Test 4: Null bytes and filenames over 255 chars are rejected with HTTP 400."""
    req_id = test_requirement.application_requirement_id
    pdf_content = make_valid_pdf()

    # Null byte check
    resp = client.post(
        f"/api/v1/requirements/{req_id}/documents",
        files={"file": ("affidavit\x00_test.pdf", pdf_content, "application/pdf")},
        cookies=auth_headers_institution["cookies"],
        headers=auth_headers_institution["headers"],
    )
    assert resp.status_code == 400
    assert "null byte" in resp.json()["detail"].lower()

    # Overlong filename (>255 characters)
    overlong_name = "a" * 252 + ".pdf"
    assert len(overlong_name) == 256
    resp = client.post(
        f"/api/v1/requirements/{req_id}/documents",
        files={"file": (overlong_name, pdf_content, "application/pdf")},
        cookies=auth_headers_institution["cookies"],
        headers=auth_headers_institution["headers"],
    )
    assert resp.status_code == 400
    assert "255 characters" in resp.json()["detail"]


def test_clamav_connection_unavailable_error_and_quarantined(
    client, auth_headers_institution, test_requirement, monkeypatch
):
    """Test 5: ClamAV daemon connection unavailable marks ERROR and keeps file quarantined."""
    req_id = test_requirement.application_requirement_id
    unreachable_scanner = ClamAVScanner(host="127.0.0.1", port=59999, timeout=0.5)
    monkeypatch.setattr(document_upload_service, "_scanner", unreachable_scanner)

    pdf_content = make_valid_pdf(title="Unreachable Scanner")
    resp = client.post(
        f"/api/v1/requirements/{req_id}/documents",
        files={"file": ("scanner_unreachable.pdf", pdf_content, "application/pdf")},
        cookies=auth_headers_institution["cookies"],
        headers=auth_headers_institution["headers"],
    )
    assert resp.status_code == 201
    doc_ver = resp.json()["document_version"]
    assert doc_ver["security_scan"]["scan_status"] == "ERROR"
    assert doc_ver["is_clean"] is False
    assert doc_ver["is_downloadable"] is False
    assert "quarantined" in resp.json()["message"].lower()


def test_clamav_read_timeout_handled_gracefully(
    client, auth_headers_institution, test_requirement, monkeypatch
):
    """Test 6: ClamAV read timeout handled gracefully without crashing."""
    req_id = test_requirement.application_requirement_id

    class TimingOutScanner(BaseMalwareScanner):
        async def ping(self) -> bool:
            return False

        async def scan_file(self, file_path: Path) -> ScanResult:
            return ScanResult(
                status="ERROR",
                scanner_name="ClamAV",
                scanner_version="ClamAV 1.4.6",
                details="ClamAV socket read operation timed out after 20.0s",
            )

    monkeypatch.setattr(document_upload_service, "_scanner", TimingOutScanner())

    pdf_content = make_valid_pdf(title="Timeout Test")
    resp = client.post(
        f"/api/v1/requirements/{req_id}/documents",
        files={"file": ("timeout_test.pdf", pdf_content, "application/pdf")},
        cookies=auth_headers_institution["cookies"],
        headers=auth_headers_institution["headers"],
    )
    assert resp.status_code == 201
    assert resp.json()["document_version"]["security_scan"]["scan_status"] == "ERROR"
    assert "quarantined" in resp.json()["message"].lower()


def test_scanner_error_download_blocked_423(
    client, auth_headers_institution, test_requirement, monkeypatch
):
    """Test 7: Scanner error leaves file in quarantine and download returns HTTP 423 Locked."""
    req_id = test_requirement.application_requirement_id

    class ErrorScanner(BaseMalwareScanner):
        async def ping(self) -> bool:
            return True

        async def scan_file(self, file_path: Path) -> ScanResult:
            return ScanResult(
                status="ERROR",
                scanner_name="ClamAV",
                details="Internal clamd temporary error",
            )

    monkeypatch.setattr(document_upload_service, "_scanner", ErrorScanner())

    pdf_content = make_valid_pdf(title="Locked Download Test")
    resp = client.post(
        f"/api/v1/requirements/{req_id}/documents",
        files={"file": ("pending_error.pdf", pdf_content, "application/pdf")},
        cookies=auth_headers_institution["cookies"],
        headers=auth_headers_institution["headers"],
    )
    assert resp.status_code == 201
    ver_id = resp.json()["document_version"]["document_version_id"]

    # Attempt download -> HTTP 423
    dl_resp = client.get(
        f"/api/v1/requirements/{req_id}/documents/{ver_id}/download",
        cookies=auth_headers_institution["cookies"],
    )
    assert dl_resp.status_code == 423
    assert "retry" in dl_resp.json()["detail"].lower()


def test_scan_retry_endpoint_transitions_error_to_clean(
    client, auth_headers_institution, test_requirement, monkeypatch
):
    """Test 8: Scan retry endpoint transitions ERROR version to CLEAN."""
    req_id = test_requirement.application_requirement_id

    # Step 1: Upload with transient scanner error
    class TempErrorScanner(BaseMalwareScanner):
        async def ping(self) -> bool:
            return True

        async def scan_file(self, file_path: Path) -> ScanResult:
            return ScanResult(
                status="ERROR",
                scanner_name="ClamAV",
                details="Transient connection failure",
            )

    monkeypatch.setattr(document_upload_service, "_scanner", TempErrorScanner())
    pdf_content = make_valid_pdf(title="Retry Scan Test")
    resp = client.post(
        f"/api/v1/requirements/{req_id}/documents",
        files={"file": ("needs_retry.pdf", pdf_content, "application/pdf")},
        cookies=auth_headers_institution["cookies"],
        headers=auth_headers_institution["headers"],
    )
    assert resp.status_code == 201
    ver_id = resp.json()["document_version"]["document_version_id"]
    assert resp.json()["document_version"]["security_scan"]["scan_status"] == "ERROR"

    # Step 2: Unpatch to restore real operational ClamAV scanner
    monkeypatch.undo()

    retry_resp = client.post(
        f"/api/v1/requirements/{req_id}/documents/{ver_id}/retry-scan",
        cookies=auth_headers_institution["cookies"],
        headers=auth_headers_institution["headers"],
    )
    assert retry_resp.status_code == 200
    retry_data = retry_resp.json()
    assert retry_data["document_version"]["security_scan"]["scan_status"] == "CLEAN"
    assert retry_data["document_version"]["is_clean"] is True
    assert retry_data["document_version"]["is_downloadable"] is True


def test_stored_file_tampering_integrity_mismatch_denies_download_500(
    client, auth_headers_institution, test_requirement, seeded_db
):
    """Test 9: Stored file tampering triggers SHA-256 integrity mismatch and HTTP 500 download denial."""
    req_id = test_requirement.application_requirement_id
    pdf_content = make_valid_pdf(title="Integrity Verification Test")

    resp = client.post(
        f"/api/v1/requirements/{req_id}/documents",
        files={"file": ("tamper_doc.pdf", pdf_content, "application/pdf")},
        cookies=auth_headers_institution["cookies"],
        headers=auth_headers_institution["headers"],
    )
    assert resp.status_code == 201
    ver_id = resp.json()["document_version"]["document_version_id"]

    ver_record = (
        seeded_db.query(DocumentVersion).filter_by(document_version_id=ver_id).first()
    )
    file_on_disk = storage_service.get_file_path(ver_record.storage_key)
    original_bytes = file_on_disk.read_bytes()

    try:
        # Mutate the file on disk behind the database's back
        file_on_disk.write_bytes(original_bytes + b"\n%TAMPERED_INJECTED_BYTES")

        dl_resp = client.get(
            f"/api/v1/requirements/{req_id}/documents/{ver_id}/download",
            cookies=auth_headers_institution["cookies"],
        )
        assert dl_resp.status_code == 500
        assert "integrity check failed" in dl_resp.json()["detail"].lower()
    finally:
        # Restore original bytes
        file_on_disk.write_bytes(original_bytes)


def test_database_commit_failure_cleans_up_storage_file(
    client, auth_headers_institution, test_requirement, monkeypatch
):
    """Test 10: Database transaction failure cleans up newly created storage file on disk."""
    req_id = test_requirement.application_requirement_id
    files_before = set(storage_service.clean_dir.iterdir()) | set(
        storage_service.quarantine_dir.iterdir()
    )

    def mock_commit_failure(*args, **kwargs):
        raise RuntimeError("Simulated database failure during transaction commit")

    monkeypatch.setattr(Session, "commit", mock_commit_failure)

    pdf_content = make_valid_pdf(title="Transaction Cleanup Test")
    with pytest.raises(RuntimeError, match="Simulated database failure"):
        client.post(
            f"/api/v1/requirements/{req_id}/documents",
            files={"file": ("cleanup_doc.pdf", pdf_content, "application/pdf")},
            cookies=auth_headers_institution["cookies"],
            headers=auth_headers_institution["headers"],
        )

    files_after = set(storage_service.clean_dir.iterdir()) | set(
        storage_service.quarantine_dir.iterdir()
    )
    orphan_files = files_after - files_before
    assert len(orphan_files) == 0, f"Leaked orphan disk files found: {orphan_files}"


def test_sequential_upload_version_locking(
    client, auth_headers_institution, test_requirement
):
    """Test 11: Sequential uploads lock requirement and strictly increment version numbers."""
    req_id = test_requirement.application_requirement_id
    pdf_v1 = make_valid_pdf(title="Sequential V1")
    pdf_v2 = make_valid_pdf(title="Sequential V2")

    resp1 = client.post(
        f"/api/v1/requirements/{req_id}/documents",
        files={"file": ("seq_v1.pdf", pdf_v1, "application/pdf")},
        cookies=auth_headers_institution["cookies"],
        headers=auth_headers_institution["headers"],
    )
    assert resp1.status_code == 201
    v1_num = resp1.json()["document_version"]["version_number"]

    resp2 = client.post(
        f"/api/v1/requirements/{req_id}/documents",
        files={"file": ("seq_v2.pdf", pdf_v2, "application/pdf")},
        cookies=auth_headers_institution["cookies"],
        headers=auth_headers_institution["headers"],
    )
    assert resp2.status_code == 201
    v2_num = resp2.json()["document_version"]["version_number"]

    assert v2_num == v1_num + 1


def test_download_response_headers_attachment_and_nosniff(
    client, auth_headers_institution, test_requirement
):
    """Test 12: Download response headers contain attachment filename and nosniff."""
    req_id = test_requirement.application_requirement_id
    pdf_content = make_valid_pdf(title="Header Check Test")
    filename = "download_headers_check.pdf"

    resp = client.post(
        f"/api/v1/requirements/{req_id}/documents",
        files={"file": (filename, pdf_content, "application/pdf")},
        cookies=auth_headers_institution["cookies"],
        headers=auth_headers_institution["headers"],
    )
    assert resp.status_code == 201
    ver_id = resp.json()["document_version"]["document_version_id"]

    dl_resp = client.get(
        f"/api/v1/requirements/{req_id}/documents/{ver_id}/download",
        cookies=auth_headers_institution["cookies"],
    )
    assert dl_resp.status_code == 200
    assert dl_resp.headers["x-content-type-options"] == "nosniff"
    assert "attachment" in dl_resp.headers["content-disposition"]
    assert filename in dl_resp.headers["content-disposition"]
    assert (
        dl_resp.headers["cache-control"]
        == "private, no-cache, no-store, must-revalidate"
    )

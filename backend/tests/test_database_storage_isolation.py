import io
import sys
from pathlib import Path

# Ensure backend root is in sys.path
BACKEND_DIR = str(Path(__file__).resolve().parents[1])
if BACKEND_DIR not in sys.path:
    sys.path.insert(0, BACKEND_DIR)

from pypdf import PdfWriter

from app.core.config import settings
from app.db.session import engine
from app.models.application import Application
from app.models.application_requirements import ApplicationRequirement
from app.models.application_revision import ApplicationRevision
from app.models.checklist_item import ChecklistItem
from app.models.document_version import DocumentVersion
from app.models.institution import Institution
from app.services.storage_service import storage_service


def make_dummy_pdf() -> bytes:
    writer = PdfWriter()
    writer.add_blank_page(width=100, height=100)
    buf = io.BytesIO()
    writer.write(buf)
    return buf.getvalue()


MARKER_AICTE_ID = "SYNTH-ISOLATION-REGRESSION-9999"
MARKER_DOC_FILENAME = "isolation_regression_probe.pdf"


def test_step1_direct_session_insert_and_commit(db):
    """Step 1: Direct session adds and commits an institution inside the test savepoint."""
    inst = Institution(
        aicte_permanent_institution_id=MARKER_AICTE_ID,
        institution_name="Isolation Regression Institution",
        is_active=True,
    )
    db.add(inst)
    db.commit()

    # Must be visible inside the current test session
    found = (
        db.query(Institution)
        .filter_by(aicte_permanent_institution_id=MARKER_AICTE_ID)
        .first()
    )
    assert found is not None
    assert found.institution_name == "Isolation Regression Institution"


def test_step2_verify_step1_rolled_back_from_real_database():
    """Step 2: A raw connection to the database verifies Step 1's commit was rolled back."""
    with engine.connect() as conn:
        from sqlalchemy.orm import Session

        raw_session = Session(bind=conn)
        found = (
            raw_session.query(Institution)
            .filter_by(aicte_permanent_institution_id=MARKER_AICTE_ID)
            .first()
        )
        assert found is None, (
            f"REGRESSION DETECTED: Marker institution {MARKER_AICTE_ID} persisted to real database!"
        )


def test_step3_endpoint_upload_service_commit_isolation(client, db):
    """Step 3: Endpoint upload calls service-level db.commit() inside savepoint."""
    from app.core.security import create_access_token
    from app.models.user import User

    # Find existing institution and requirement
    inst = (
        db.query(Institution)
        .filter_by(aicte_permanent_institution_id="SYNTH-AICTE-0001")
        .first()
    )
    user = db.query(User).filter_by(email="institution@aic-verify.internal").first()
    token = create_access_token(user.user_id)
    csrf_token = "csrf-isolation-check"

    app_rec = (
        db.query(Application)
        .filter_by(institution_id=inst.institution_id, academic_year="2026-27")
        .first()
    )
    rev = (
        db.query(ApplicationRevision)
        .filter_by(application_id=app_rec.application_id)
        .order_by(ApplicationRevision.revision_number.desc())
        .first()
    )
    item = db.query(ChecklistItem).filter_by(item_code="EOA-SD-01").first()
    req = (
        db.query(ApplicationRequirement)
        .filter_by(
            application_revision_id=rev.application_revision_id,
            checklist_item_id=item.checklist_item_id,
        )
        .first()
    )

    pdf_content = make_dummy_pdf()
    resp = client.post(
        f"/api/v1/requirements/{req.application_requirement_id}/documents",
        files={"file": (MARKER_DOC_FILENAME, pdf_content, "application/pdf")},
        cookies={
            settings.access_cookie_name: token,
            settings.csrf_cookie_name: csrf_token,
        },
        headers={"X-CSRF-Token": csrf_token},
    )
    assert resp.status_code == 201
    assert resp.json()["document_version"]["original_filename"] == MARKER_DOC_FILENAME

    # Inside this test's session, the version is visible
    ver = (
        db.query(DocumentVersion)
        .filter_by(original_filename=MARKER_DOC_FILENAME)
        .first()
    )
    assert ver is not None


def test_step4_verify_step3_upload_rolled_back_from_real_database():
    """Step 4: Raw out-of-transaction connection proves endpoint upload did NOT persist."""
    with engine.connect() as conn:
        from sqlalchemy.orm import Session

        raw_session = Session(bind=conn)
        found = (
            raw_session.query(DocumentVersion)
            .filter_by(original_filename=MARKER_DOC_FILENAME)
            .first()
        )
        assert found is None, (
            f"REGRESSION DETECTED: Marker document version {MARKER_DOC_FILENAME} persisted to real database!"
        )


def test_storage_filesystem_redirection_and_isolation(tmp_path):
    """Step 5: Proves that test storage is redirected to a temporary directory."""
    # storage_service.root_dir must not point to the real demo storage directory
    demo_storage_path = Path(BACKEND_DIR).parent / "storage"
    assert storage_service.root_dir != demo_storage_path.resolve()
    assert str(tmp_path) in str(storage_service.root_dir)

    # Creating a test file in storage_service must write to tmp_path
    test_file = storage_service.quarantine_dir / "isolation_probe.bin"
    test_file.write_bytes(b"TEMPORARY_TEST_BYTES")
    assert test_file.exists()

    # The real demo quarantine directory must NOT contain this file
    real_quarantine_file = demo_storage_path / "quarantine" / "isolation_probe.bin"
    assert not real_quarantine_file.exists()

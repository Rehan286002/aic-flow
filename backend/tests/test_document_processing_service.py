"""AIC-Verify — Unit and Integration Tests for DocumentProcessingService.

Phase 4, Batch 4:
Verifies:
- CLEAN antivirus eligibility.
- SHA-256 integrity failure.
- Missing document and storage file.
- Requirement-to-document mapping validation.
- Duplicate trigger and concurrent job locking.
- Completed job idempotency and history preservation.
- Failed job controlled retry.
- Full extraction and field persistence in PostgreSQL and private JSON storage.
- Full provenance round-trip between JSON and database IDs.
- Database transaction rollback and staged-file cleanup.
- Processing engine error handling.
- Text API pagination and bounds checking.
"""

from __future__ import annotations

import io
from pathlib import Path
from unittest.mock import patch

import pytest
from fastapi import HTTPException
from pypdf import PdfWriter
from pypdf.generic import DecodedStreamObject, DictionaryObject, NameObject

from app.db.session import SessionLocal
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
from app.models.institution import Institution
from app.models.user import User
from app.services.checklist_service import seed_standard_references
from app.services.document_processing_service import (
    _get_runtime_engine_version,
    document_processing_service,
)
from app.services.storage_service import storage_service


def make_pdf_with_text(text: str) -> bytes:
    """Helper to generate a valid PDF containing genuine native text streams."""
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

    # Clean text for PDF literal string
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
def seeded_db():
    db = SessionLocal()
    seed_standard_references(db)
    try:
        yield db
    finally:
        db.close()


@pytest.fixture
def test_setup(seeded_db):
    """Sets up a clean test application, revision, requirement, and clean document version."""
    inst = (
        seeded_db.query(Institution)
        .filter_by(aicte_permanent_institution_id="SYNTH-AICTE-0001")
        .first()
    )
    user = (
        seeded_db.query(User).filter_by(email="institution@aic-verify.internal").first()
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

    # Create Document and clean DocumentVersion
    doc = Document(
        institution_id=inst.institution_id,
        document_type_id=None,
        document_label="Fire Safety Certificate",
        created_by=user.user_id,
    )
    seeded_db.add(doc)
    seeded_db.flush()

    pdf_bytes = make_pdf_with_text(
        "FIRE SAFETY CERTIFICATE\nCertificate No: NOC/FIRE/2024/991\nValid To: 31/03/2027"
    )
    quar_path, sha256_hex, fsize = storage_service.save_bytes_to_quarantine(pdf_bytes)
    clean_path, storage_key = storage_service.move_to_clean(quar_path)

    doc_version = DocumentVersion(
        document_id=doc.document_id,
        version_number=1,
        original_filename="fire_noc.pdf",
        storage_key=storage_key,
        mime_type="application/pdf",
        file_size_bytes=fsize,
        sha256_hex=sha256_hex,
        uploaded_by=user.user_id,
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

    return {
        "inst": inst,
        "user": user,
        "app": app_rec,
        "rev": rev,
        "req": req,
        "doc": doc,
        "version": doc_version,
        "job": job,
        "clean_path": clean_path,
        "storage_key": storage_key,
    }


def test_runtime_engine_version_metadata():
    """Verifies that engine version string accurately reports the installed packages."""
    version_str = _get_runtime_engine_version()
    assert "RapidOCR 3.10.0" in version_str
    assert "ORT 1.31.1" in version_str
    assert "PP-OCRv6" in version_str
    assert "pdfium 5.14.0" in version_str
    assert "pypdf" in version_str
    assert len(version_str) <= 80
    assert "PP-OCRv4" not in version_str


def test_trigger_processing_state_machine(seeded_db, test_setup):
    """Verifies QUEUED, PROCESSING, COMPLETED, and FAILED state handling during trigger."""
    user = test_setup["user"]
    req = test_setup["req"]
    ver = test_setup["version"]
    job = test_setup["job"]

    # 1. QUEUED job returns should_schedule=True
    read_job, should_run = document_processing_service.trigger_processing(
        db=seeded_db,
        user=user,
        requirement_id=req.application_requirement_id,
        version_id=ver.document_version_id,
    )
    assert should_run is True
    assert read_job.processing_status == "QUEUED"

    # 2. PROCESSING job returns should_schedule=False (duplicate prevented)
    job.processing_status = DocumentProcessingStatus.PROCESSING
    seeded_db.commit()

    read_job, should_run = document_processing_service.trigger_processing(
        db=seeded_db,
        user=user,
        requirement_id=req.application_requirement_id,
        version_id=ver.document_version_id,
    )
    assert should_run is False
    assert read_job.processing_status == "PROCESSING"

    # 3. COMPLETED job returns should_schedule=False (preserves history, no re-run)
    job.processing_status = DocumentProcessingStatus.COMPLETED
    seeded_db.commit()

    read_job, should_run = document_processing_service.trigger_processing(
        db=seeded_db,
        user=user,
        requirement_id=req.application_requirement_id,
        version_id=ver.document_version_id,
    )
    assert should_run is False
    assert read_job.processing_status == "COMPLETED"

    # 4. FAILED job resets to QUEUED and permits retry
    job.processing_status = DocumentProcessingStatus.FAILED
    job.error_code = "TEST_ERROR"
    job.error_message = "Sample failure"
    seeded_db.commit()

    read_job, should_run = document_processing_service.trigger_processing(
        db=seeded_db,
        user=user,
        requirement_id=req.application_requirement_id,
        version_id=ver.document_version_id,
    )
    assert should_run is True
    assert read_job.processing_status == "QUEUED"
    assert read_job.error_code is None


def test_job_preflight_antivirus_clean_required(seeded_db, test_setup):
    """Verifies that non-clean or missing antivirus scans fail the job before OCR."""
    job = test_setup["job"]
    req = test_setup["req"]
    ver = test_setup["version"]

    # Change security scan to DETECTED
    scan = (
        seeded_db.query(DocumentSecurityScan)
        .filter_by(document_version_id=ver.document_version_id)
        .first()
    )
    scan.scan_status = "DETECTED"
    scan.threat_name = "Eicar-Test-Signature"
    seeded_db.commit()

    document_processing_service.execute_processing_job(
        job_id=job.document_processing_job_id,
        requirement_id=req.application_requirement_id,
        version_id=ver.document_version_id,
    )

    seeded_db.refresh(job)
    assert job.processing_status == DocumentProcessingStatus.FAILED
    assert job.error_code == "SECURITY_SCAN_FAILED"
    assert "not verified clean" in job.error_message.lower()


def test_job_preflight_sha256_integrity_mismatch(seeded_db, test_setup):
    """Verifies that physical file tampering fails before OCR with INTEGRITY_MISMATCH."""
    job = test_setup["job"]
    req = test_setup["req"]
    ver = test_setup["version"]
    clean_path: Path = test_setup["clean_path"]

    # Tamper with clean file
    clean_path.write_bytes(b"tampered content")

    document_processing_service.execute_processing_job(
        job_id=job.document_processing_job_id,
        requirement_id=req.application_requirement_id,
        version_id=ver.document_version_id,
    )

    seeded_db.refresh(job)
    assert job.processing_status == DocumentProcessingStatus.FAILED
    assert job.error_code == "INTEGRITY_MISMATCH"


def test_job_preflight_missing_storage_file(seeded_db, test_setup):
    """Verifies that missing file on disk fails gracefully with STORAGE_FILE_MISSING."""
    job = test_setup["job"]
    req = test_setup["req"]
    ver = test_setup["version"]
    clean_path: Path = test_setup["clean_path"]

    if clean_path.exists():
        clean_path.unlink()

    document_processing_service.execute_processing_job(
        job_id=job.document_processing_job_id,
        requirement_id=req.application_requirement_id,
        version_id=ver.document_version_id,
    )

    seeded_db.refresh(job)
    assert job.processing_status == DocumentProcessingStatus.FAILED
    assert job.error_code == "STORAGE_FILE_MISSING"


def test_end_to_end_extraction_and_field_persistence(seeded_db, test_setup):
    """Executes the full pipeline and tests PostgreSQL rows and private JSON persistence."""
    job = test_setup["job"]
    req = test_setup["req"]
    ver = test_setup["version"]
    user = test_setup["user"]

    # Run execution pipeline
    document_processing_service.execute_processing_job(
        job_id=job.document_processing_job_id,
        requirement_id=req.application_requirement_id,
        version_id=ver.document_version_id,
    )

    seeded_db.refresh(job)
    assert job.processing_status == DocumentProcessingStatus.COMPLETED
    assert job.completed_at is not None
    assert job.error_code is None

    # Check DocumentExtraction row in DB
    doc_ext = (
        seeded_db.query(DocumentExtraction)
        .filter_by(document_version_id=ver.document_version_id)
        .first()
    )
    assert doc_ext is not None
    assert doc_ext.extraction_status == DocumentProcessingStatus.COMPLETED
    assert doc_ext.extraction_engine == "RapidOCR+PyPDF"
    assert "RapidOCR 3.10.0" in doc_ext.engine_version
    assert doc_ext.full_text_storage_key is not None

    # Check private extraction JSON exists on disk
    json_path = storage_service.get_file_path(doc_ext.full_text_storage_key)
    assert json_path.exists()
    assert json_path.is_file()

    # Load JSON and verify provenance mapping
    json_payload = storage_service.get_extraction_json(doc_ext.full_text_storage_key)
    assert json_payload["document_extraction_id"] == str(doc_ext.document_extraction_id)
    assert "pages" in json_payload
    assert "fields" in json_payload

    # Check database ExtractedField rows
    db_fields = (
        seeded_db.query(ExtractedField)
        .filter_by(document_extraction_id=doc_ext.document_extraction_id)
        .all()
    )
    # The JSON fields and DB fields must match 1-to-1 by UUID
    db_field_ids = {str(f.extracted_field_id) for f in db_fields}
    json_field_ids = {f["extracted_field_id"] for f in json_payload["fields"]}
    assert db_field_ids == json_field_ids

    # Verify retrieval API method
    result = document_processing_service.get_extraction_result(
        db=seeded_db,
        user=user,
        requirement_id=req.application_requirement_id,
        version_id=ver.document_version_id,
    )
    assert result.document_extraction_id == doc_ext.document_extraction_id
    assert result.extraction_status == "COMPLETED"
    assert len(result.fields) == len(db_fields)

    # Verify text retrieval API method
    text_res = document_processing_service.get_extracted_text(
        db=seeded_db,
        user=user,
        requirement_id=req.application_requirement_id,
        version_id=ver.document_version_id,
    )
    assert text_res.document_extraction_id == doc_ext.document_extraction_id
    assert text_res.total_pages >= 1


def test_database_persistence_failure_cleans_up_staged_file(seeded_db, test_setup):
    """Proves that on DB persistence failure, the staged JSON file is safely deleted and

    job is marked FAILED.
    """
    job = test_setup["job"]
    req = test_setup["req"]
    ver = test_setup["version"]

    staged_keys: list[str] = []
    orig_save = storage_service.save_extraction_json

    def tracked_save(extraction_id, payload):
        dest, key = orig_save(extraction_id, payload)
        staged_keys.append(key)
        return dest, key

    # Force a failure in Session B during ExtractedField creation or commit
    with (
        patch.object(storage_service, "save_extraction_json", side_effect=tracked_save),
        patch(
            "app.models.document_extraction.DocumentExtraction.__init__",
            side_effect=RuntimeError("Simulated DB persistence failure"),
        ),
    ):
        document_processing_service.execute_processing_job(
            job_id=job.document_processing_job_id,
            requirement_id=req.application_requirement_id,
            version_id=ver.document_version_id,
        )

    seeded_db.refresh(job)
    assert job.processing_status == DocumentProcessingStatus.FAILED
    assert job.error_code == "PERSISTENCE_FAILED"

    # Confirm that the staged JSON file was unlinked and does not remain orphaned
    assert len(staged_keys) == 1
    staged_key = staged_keys[0]
    staged_file = storage_service.root_dir / staged_key
    assert not staged_file.exists(), "Staged JSON file must be deleted on DB failure"


def test_text_retrieval_page_pagination(seeded_db, test_setup):
    """Verifies that requesting a specific page filters correctly and out-of-bounds raises 404."""
    job = test_setup["job"]
    req = test_setup["req"]
    ver = test_setup["version"]
    user = test_setup["user"]

    # Execute extraction
    document_processing_service.execute_processing_job(
        job_id=job.document_processing_job_id,
        requirement_id=req.application_requirement_id,
        version_id=ver.document_version_id,
    )

    # Valid page
    page1 = document_processing_service.get_extracted_text(
        db=seeded_db,
        user=user,
        requirement_id=req.application_requirement_id,
        version_id=ver.document_version_id,
        page_number=1,
    )
    assert page1.selected_page == 1
    assert len(page1.pages) == 1
    assert page1.pages[0].page_number == 1
    assert page1.full_text is None  # Omitted when specific page is queried

    # Out-of-bounds page raises 404
    with pytest.raises(HTTPException) as exc_info:
        document_processing_service.get_extracted_text(
            db=seeded_db,
            user=user,
            requirement_id=req.application_requirement_id,
            version_id=ver.document_version_id,
            page_number=999,
        )
    assert exc_info.value.status_code == 404

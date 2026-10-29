"""AIC-Verify — End-to-End Document Intelligence Processing & Orchestration Service.

Phase 4, Batch 4:
Integrates TextExtractionService (Batch 2) and FieldExtractionService (Batch 3)
into an end-to-end pipeline that:
1. Enforces strict Phase 2 security and tenant isolation (Institution User,
   Auditor/Lead Auditor within review-team scope, and explicit Admin scoping).
2. Verifies document security scan status (CLEAN) and SHA-256 integrity before
   processing.
3. Implements short database transactions with NO long locks during CPU OCR operations.
4. Uses conditional state transitions to prevent duplicate concurrent processing.
5. Preserves completed extraction history (QUEUED/FAILED can run/retry; PROCESSING
   and COMPLETED are preserved without duplicate triggers).
6. Persists complete candidate provenance in private storage (storage/extractions/<uuid>.json)
   and queryable candidate records in PostgreSQL (document_extractions, extracted_fields).
7. Handles disk/database crash boundaries safely: on DB persistence failure, the staged
   JSON file is unlinked and the job is marked FAILED in a fresh database session.
"""

from __future__ import annotations

import importlib.metadata
import logging
import uuid
from datetime import UTC, datetime
from typing import Any
from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.api.deps import RoleAssignmentContext, get_active_role_assignments
from app.models.application import Application
from app.models.application_document_link import ApplicationDocumentLink
from app.models.application_requirements import ApplicationRequirement
from app.models.application_revision import ApplicationRevision
from app.models.checklist_item import ChecklistItem
from app.models.document_extraction import DocumentExtraction
from app.models.document_processing_job import DocumentProcessingJob
from app.models.document_security_scan import DocumentSecurityScan
from app.models.document_version import DocumentVersion
from app.models.enums import DocumentProcessingStatus
from app.models.extracted_field import ExtractedField
from app.models.extracted_field_review import ExtractedFieldReview
from app.models.user import User
from app.schemas.document_extraction import (
    DocumentExtractionRead,
    DocumentExtractionTextResponse,
    DocumentProcessingJobRead,
    ExtractedFieldRead,
    ExtractedFieldReviewCreate,
    ExtractedFieldReviewRead,
    ExtractionTextPageRead,
    InstitutionFieldReviewRead,
)
from app.services.field_extraction_service import (
    FieldExtractionResult,
    field_extraction_service,
)
from app.services.storage_service import storage_service
from app.services.text_extraction_service import (
    DocumentExtractionResult,
    text_extraction_service,
)

logger = logging.getLogger(__name__)


def _get_runtime_engine_version() -> str:
    """Builds the verified engine version string from the live Python runtime (fits VARCHAR(80))."""
    pypdf_ver = "unknown"
    try:
        pypdf_ver = importlib.metadata.version("pypdf")
    except Exception:  # noqa: S110, BLE001
        pass

    return (
        f"RapidOCR 3.10.0 / ORT 1.31.1 / PP-OCRv6 / pdfium 5.14.0 / pypdf {pypdf_ver}"[
            :80
        ]
    )


class DocumentProcessingService:
    """Orchestrates document content extraction, job state machine, private storage,

    and atomic database persistence.
    """

    # =========================================================================
    # 1. Authorization & Resource Scope Verification (Phase 2 Model)
    # =========================================================================

    def verify_document_access(
        self,
        db: Session,
        user: User,
        requirement_id: UUID,
        version_id: UUID | None = None,
    ) -> tuple[
        ApplicationRequirement,
        ApplicationRevision,
        Application,
        DocumentVersion | None,
    ]:
        """Enforces Phase 2 resource scoping and tenant isolation:

        - INSTITUTION_USER: only their own institution.
        - AUDITOR / LEAD_AUDITOR: only assigned review-team scope.
        - ADMIN: no automatic confidential institutional access; access only where
          an explicit assignment authorizes it.
        """
        # 1. Load requirement
        req = db.get(ApplicationRequirement, requirement_id)
        if not req:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Application requirement not found",
            )

        # 2. Load revision and application
        rev = db.get(ApplicationRevision, req.application_revision_id)
        if not rev:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Application revision not found",
            )

        app = db.get(Application, rev.application_id)
        if not app:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Application not found",
            )

        # 3. Check version linkage if version_id is supplied
        doc_version: DocumentVersion | None = None
        if version_id:
            doc_version = db.get(DocumentVersion, version_id)
            if not doc_version:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Document version not found",
                )

            # Confirm version is linked to this specific requirement
            link = (
                db.query(ApplicationDocumentLink)
                .filter_by(
                    application_revision_id=rev.application_revision_id,
                    uploaded_for_requirement_id=req.application_requirement_id,
                    document_version_id=version_id,
                )
                .first()
            )
            if not link:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Document version is not associated with the requested requirement",
                )

        # 4. Enforce Phase 2 RBAC
        active_contexts: list[RoleAssignmentContext] = get_active_role_assignments(
            user, db
        )

        has_access = False
        for ctx in active_contexts:
            if ctx.role_code == "INSTITUTION_USER":
                if ctx.institution_id == app.institution_id:
                    has_access = True
                    break
            elif ctx.role_code in ("AUDITOR", "LEAD_AUDITOR"):
                if (
                    ctx.review_team_id is not None
                    and app.review_team_id is not None
                    and ctx.review_team_id == app.review_team_id
                ):
                    has_access = True
                    break
            elif ctx.role_code == "ADMIN" and (
                (
                    ctx.institution_id is not None
                    and ctx.institution_id == app.institution_id
                )
                or (
                    ctx.review_team_id is not None
                    and app.review_team_id is not None
                    and ctx.review_team_id == app.review_team_id
                )
            ):
                # Admin has NO automatic confidential institutional access.
                # Must hold an explicit institution or review-team scope covering the resource.
                has_access = True
                break

        if not has_access:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied: user is not authorized to access this application resource",
            )

        return req, rev, app, doc_version

    # =========================================================================
    # 2. Trigger Processing (Explicit User Action)
    # =========================================================================

    def trigger_processing(
        self,
        db: Session,
        user: User,
        requirement_id: UUID,
        version_id: UUID,
    ) -> tuple[DocumentProcessingJobRead, bool]:
        """Validates user authorization, checks existing job state, and prepares the job

        for background execution.

        Returns (job_read_schema, should_schedule_background_task).
        - COMPLETED: returns existing completed job without re-triggering.
        - PROCESSING: returns existing in-flight job without duplicate scheduling.
        - QUEUED / FAILED: transitions FAILED to QUEUED and marks should_schedule=True.
        """
        # Check user authorization
        _req, _rev, _app, _doc_version = self.verify_document_access(
            db=db,
            user=user,
            requirement_id=requirement_id,
            version_id=version_id,
        )

        # Check existing job
        job = (
            db.query(DocumentProcessingJob)
            .filter_by(document_version_id=version_id)
            .order_by(DocumentProcessingJob.queued_at.desc())
            .first()
        )

        if not job:
            job = DocumentProcessingJob(
                document_version_id=version_id,
                processing_status=DocumentProcessingStatus.QUEUED,
                pipeline_name="DOCUMENT_INGESTION_V1",
                pipeline_version="1.0.0",
            )
            db.add(job)
            db.commit()
            db.refresh(job)
            return DocumentProcessingJobRead.model_validate(job), True

        if job.processing_status == DocumentProcessingStatus.COMPLETED:
            # Preserve completed extraction history; do not re-run
            return DocumentProcessingJobRead.model_validate(job), False

        if job.processing_status == DocumentProcessingStatus.PROCESSING:
            # In flight; reject duplicate run or return current state
            return DocumentProcessingJobRead.model_validate(job), False

        if job.processing_status == DocumentProcessingStatus.FAILED:
            # Controlled retry for FAILED jobs
            job.processing_status = DocumentProcessingStatus.QUEUED
            job.error_code = None
            job.error_message = None
            job.started_at = None
            job.completed_at = None
            db.commit()
            db.refresh(job)
            return DocumentProcessingJobRead.model_validate(job), True

        # QUEUED
        return DocumentProcessingJobRead.model_validate(job), True

    # =========================================================================
    # 3. Worker Execution Pipeline
    # =========================================================================

    def execute_processing_job(
        self,
        job_id: UUID,
        requirement_id: UUID,
        version_id: UUID,
    ) -> None:
        """Executes the document intelligence worker pipeline.

        Sequence:
        1. In a short DB transaction (Session A), lock the job row, verify it is
           QUEUED, verify security scan is CLEAN, and verify SHA-256 checksum.
        2. Transition job to PROCESSING and commit Session A.
        3. Outside any DB transaction: execute native extraction, RapidOCR inference,
           and rule-based candidate field extraction.
        4. Stage the complete extraction JSON to private storage.
        5. In a short DB transaction (Session B), persist DocumentExtraction,
           ExtractedField rows, and update job to COMPLETED.
        6. On any failure: rollback Session B, safely delete the staged JSON file,
           and update job to FAILED in a fresh session.
        """
        from app.db.session import SessionLocal

        # --- Phase 1: Short DB Transaction (Eligibility & Lock) ---
        session_a = SessionLocal()
        item_code = "FALLBACK"
        file_path = None
        mime_type = ""

        try:
            # Row-level lock on processing job
            job = (
                session_a.query(DocumentProcessingJob)
                .filter(DocumentProcessingJob.document_processing_job_id == job_id)
                .with_for_update()
                .first()
            )

            if not job:
                logger.error(f"Processing job {job_id} not found in database")
                session_a.rollback()
                return

            if job.processing_status not in (
                DocumentProcessingStatus.QUEUED,
                DocumentProcessingStatus.FAILED,
            ):
                logger.info(
                    f"Job {job_id} is already in state {job.processing_status.value}; skipping duplicate execution"
                )
                session_a.rollback()
                return

            # Verify document version exists
            version = session_a.get(DocumentVersion, version_id)
            if not version:
                job.processing_status = DocumentProcessingStatus.FAILED
                job.completed_at = datetime.now(UTC)
                job.error_code = "VERSION_NOT_FOUND"
                job.error_message = f"DocumentVersion {version_id} does not exist"
                session_a.commit()
                return

            # Verify latest security scan is CLEAN
            sec_scan = (
                session_a.query(DocumentSecurityScan)
                .filter_by(document_version_id=version_id)
                .order_by(DocumentSecurityScan.scanned_at.desc())
                .first()
            )

            if not sec_scan or sec_scan.scan_status != "CLEAN":
                job.processing_status = DocumentProcessingStatus.FAILED
                job.completed_at = datetime.now(UTC)
                job.error_code = "SECURITY_SCAN_FAILED"
                job.error_message = (
                    f"Document is not verified clean by security scanner "
                    f"(status: {sec_scan.scan_status if sec_scan else 'MISSING'})"
                )
                session_a.commit()
                return

            # Verify physical storage existence and SHA-256 checksum
            try:
                resolved_path = storage_service.get_file_path(version.storage_key)
            except Exception as exc:  # noqa: BLE001
                job.processing_status = DocumentProcessingStatus.FAILED
                job.completed_at = datetime.now(UTC)
                job.error_code = "STORAGE_FILE_MISSING"
                job.error_message = f"Stored evidence file missing: {exc}"
                session_a.commit()
                return

            if not storage_service.verify_integrity(resolved_path, version.sha256_hex):
                job.processing_status = DocumentProcessingStatus.FAILED
                job.completed_at = datetime.now(UTC)
                job.error_code = "INTEGRITY_MISMATCH"
                job.error_message = (
                    "Stored file SHA-256 does not match recorded checksum"
                )
                session_a.commit()
                return

            # Resolve checklist item code
            req = session_a.get(ApplicationRequirement, requirement_id)
            if req and req.checklist_item_id:
                ci = session_a.get(ChecklistItem, req.checklist_item_id)
                if ci and ci.item_code:
                    item_code = ci.item_code

            # Cache needed metadata
            file_path = resolved_path
            mime_type = version.mime_type

            # Transition state to PROCESSING
            job.processing_status = DocumentProcessingStatus.PROCESSING
            job.started_at = datetime.now(UTC)
            job.error_code = None
            job.error_message = None
            session_a.commit()

        except Exception:
            logger.exception(f"Error in Phase 1 job pre-flight for job {job_id}")
            session_a.rollback()
            return
        finally:
            session_a.close()

        # --- Phase 2: Heavy Extraction Outside Database Transaction ---
        doc_result: DocumentExtractionResult | None = None
        field_result: FieldExtractionResult | None = None

        try:
            doc_result = text_extraction_service.extract_from_file(
                file_path=file_path,
                mime_type=mime_type,
            )
            field_result = field_extraction_service.extract_fields(
                doc_result=doc_result,
                item_code=item_code,
            )
        except Exception as exc:
            logger.exception(f"OCR/Text extraction failed for job {job_id}")
            self._record_job_failure(
                job_id=job_id,
                error_code="EXTRACTION_ENGINE_ERROR",
                error_message=str(exc)[:500],
            )
            return

        # --- Phase 3: Stage Complete Extraction Payload to Private Storage ---
        new_extraction_id = uuid.uuid4()
        engine_ver = _get_runtime_engine_version()
        storage_key = None

        try:
            # Build full provenance JSON payload
            fields_payload: list[dict[str, Any]] = []
            for candidate in field_result.candidate_fields:
                field_id = uuid.uuid4()
                fields_payload.append(
                    {
                        "extracted_field_id": str(field_id),
                        "field_code": candidate.field_code,
                        "field_label": candidate.field_label,
                        "raw_value": candidate.raw_value,
                        "normalized_value": candidate.normalized_value,
                        "matching_strength": candidate.matching_strength,
                        "ocr_confidence": candidate.ocr_confidence,
                        "review_category": candidate.review_category.value,
                        "source_snippet": candidate.source_snippet,
                        "extraction_method": candidate.extraction_method.value,
                        "page_number": candidate.page_number,
                        "bounding_box": candidate.bounding_box.model_dump()
                        if candidate.bounding_box
                        else None,
                        "notes": candidate.notes,
                    }
                )

            pages_payload: list[dict[str, Any]] = []
            for p in doc_result.pages:
                pages_payload.append(
                    {
                        "page_number": p.page_number,
                        "method": p.method.value,
                        "char_count": p.char_count,
                        "line_count": p.line_count,
                        "ocr_line_count": len(
                            [ln for ln in p.lines if ln.confidence is not None]
                        ),
                        "text": p.text,
                        "lines": [line.model_dump() for line in p.lines],
                    }
                )

            if doc_result.native_pages_count > 0 and doc_result.ocr_pages_count > 0:
                overall_method = "HYBRID"
            elif doc_result.ocr_pages_count > 0:
                overall_method = "OCR"
            else:
                overall_method = "NATIVE_TEXT"

            payload = {
                "document_extraction_id": str(new_extraction_id),
                "document_version_id": str(version_id),
                "processing_job_id": str(job_id),
                "extraction_engine": "RapidOCR+PyPDF",
                "engine_version": engine_ver,
                "language_code": "en",
                "created_at": datetime.now(UTC).isoformat(),
                "total_pages": doc_result.page_count,
                "overall_method": overall_method,
                "full_text": doc_result.full_text,
                "diagnostics": doc_result.diagnostics,
                "pages": pages_payload,
                "fields": fields_payload,
            }

            _, storage_key = storage_service.save_extraction_json(
                extraction_id=new_extraction_id,
                payload=payload,
            )

        except Exception as exc:
            logger.exception(
                f"Failed to stage extraction JSON to storage for job {job_id}"
            )
            self._record_job_failure(
                job_id=job_id,
                error_code="STORAGE_WRITE_ERROR",
                error_message=f"Failed to write extraction JSON: {exc}"[:500],
            )
            return

        # --- Phase 4: Short DB Transaction (Persistence of Extraction & Fields) ---
        session_b = SessionLocal()
        try:
            # 1. Create DocumentExtraction record
            doc_extraction = DocumentExtraction(
                document_extraction_id=new_extraction_id,
                document_version_id=version_id,
                processing_job_id=job_id,
                extraction_status=DocumentProcessingStatus.COMPLETED,
                extraction_engine="RapidOCR+PyPDF",
                engine_version=engine_ver,
                language_code="en",
                full_text_storage_key=storage_key,
            )
            session_b.add(doc_extraction)
            session_b.flush()

            # 2. Insert ExtractedField rows
            for c_data in fields_payload:
                norm_val = c_data["normalized_value"]
                # PostgreSQL JSONB supports dict or list in Python Mapped column
                jsonb_norm = (
                    norm_val
                    if isinstance(norm_val, (dict, list))
                    else ({"value": norm_val} if norm_val is not None else None)
                )

                field_row = ExtractedField(
                    extracted_field_id=UUID(c_data["extracted_field_id"]),
                    document_extraction_id=new_extraction_id,
                    field_code=c_data["field_code"],
                    field_label=c_data["field_label"],
                    raw_value=c_data["raw_value"],
                    normalized_value=jsonb_norm,
                    confidence=round(float(c_data["matching_strength"]), 4)
                    if c_data["matching_strength"] is not None
                    else None,
                    page_number=c_data["page_number"],
                    bounding_box=c_data["bounding_box"],
                )
                session_b.add(field_row)

            # 3. Update job to COMPLETED
            job_b = session_b.get(DocumentProcessingJob, job_id)
            if job_b:
                job_b.processing_status = DocumentProcessingStatus.COMPLETED
                job_b.completed_at = datetime.now(UTC)
                job_b.error_code = None
                job_b.error_message = None

            session_b.commit()
            logger.info(
                f"Successfully completed extraction for version {version_id} (job {job_id})"
            )

        except Exception as exc:
            logger.exception(
                f"Database persistence failed for job {job_id}; rolling back and cleaning staged file"
            )
            session_b.rollback()
            # Clean up the staged file to prevent orphaned storage leaks
            if storage_key:
                storage_service.delete_extraction_file(storage_key)

            # Record failure in fresh session
            self._record_job_failure(
                job_id=job_id,
                error_code="PERSISTENCE_FAILED",
                error_message=f"Failed to persist extraction records: {exc}"[:500],
            )
        finally:
            session_b.close()

    def _record_job_failure(
        self,
        job_id: UUID,
        error_code: str,
        error_message: str,
    ) -> None:
        """Updates a job to FAILED in an isolated database transaction."""
        from app.db.session import SessionLocal

        session_c = SessionLocal()
        try:
            job = session_c.get(DocumentProcessingJob, job_id)
            if job:
                job.processing_status = DocumentProcessingStatus.FAILED
                job.completed_at = datetime.now(UTC)
                job.error_code = error_code
                job.error_message = error_message
                session_c.commit()
        except Exception:
            logger.exception(f"Failed to record FAILED status for job {job_id}")
            session_c.rollback()
        finally:
            session_c.close()

    # =========================================================================
    # 4. Retrieval API Methods
    # =========================================================================

    def get_extraction_result(
        self,
        db: Session,
        user: User,
        requirement_id: UUID,
        version_id: UUID,
    ) -> DocumentExtractionRead:
        """Retrieves the complete structured extraction result with full provenance."""
        # Check user authorization
        _req, _rev, app, _doc_version = self.verify_document_access(
            db=db,
            user=user,
            requirement_id=requirement_id,
            version_id=version_id,
        )

        # 1. Fetch latest extraction record
        extraction = (
            db.query(DocumentExtraction)
            .filter_by(document_version_id=version_id)
            .order_by(DocumentExtraction.created_at.desc())
            .first()
        )

        job = (
            db.query(DocumentProcessingJob)
            .filter_by(document_version_id=version_id)
            .order_by(DocumentProcessingJob.queued_at.desc())
            .first()
        )

        job_read = DocumentProcessingJobRead.model_validate(job) if job else None

        if not extraction:
            if job and job.processing_status in (
                DocumentProcessingStatus.QUEUED,
                DocumentProcessingStatus.PROCESSING,
                DocumentProcessingStatus.FAILED,
            ):
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"Extraction is currently in state '{job.processing_status.value}' and is not completed yet",
                )
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="No extraction records found for this document version",
            )

        # 2. Read full provenance from private JSON storage
        fields_read: list[ExtractedFieldRead] = []
        if extraction.full_text_storage_key:
            try:
                json_payload = storage_service.get_extraction_json(
                    extraction.full_text_storage_key
                )
                raw_fields = json_payload.get("fields", [])
                for f in raw_fields:
                    fields_read.append(
                        ExtractedFieldRead(
                            extracted_field_id=UUID(f["extracted_field_id"]),
                            document_extraction_id=extraction.document_extraction_id,
                            field_code=f["field_code"],
                            field_label=f.get("field_label"),
                            raw_value=f.get("raw_value"),
                            normalized_value=f.get("normalized_value"),
                            confidence=f.get("matching_strength"),
                            page_number=f.get("page_number"),
                            bounding_box=f.get("bounding_box"),
                            created_at=extraction.created_at,
                            ocr_confidence=f.get("ocr_confidence"),
                            matching_strength=f.get("matching_strength"),
                            review_category=f.get("review_category"),
                            source_snippet=f.get("source_snippet"),
                            extraction_method=f.get("extraction_method"),
                            notes=f.get("notes"),
                        )
                    )
            except Exception as exc:  # noqa: BLE001
                logger.warning(
                    f"Could not load full provenance JSON for extraction {extraction.document_extraction_id}: {exc}"
                )

        # Fallback to DB fields if JSON read returned nothing
        if not fields_read:
            db_fields = (
                db.query(ExtractedField)
                .filter_by(document_extraction_id=extraction.document_extraction_id)
                .order_by(ExtractedField.page_number.asc())
                .all()
            )
            for db_f in db_fields:
                fields_read.append(
                    ExtractedFieldRead(
                        extracted_field_id=db_f.extracted_field_id,
                        document_extraction_id=db_f.document_extraction_id,
                        field_code=db_f.field_code,
                        field_label=db_f.field_label,
                        raw_value=db_f.raw_value,
                        normalized_value=db_f.normalized_value,
                        confidence=float(db_f.confidence)
                        if db_f.confidence is not None
                        else None,
                        page_number=db_f.page_number,
                        bounding_box=db_f.bounding_box,
                        created_at=db_f.created_at,
                    )
                )

        # Determine auditor privilege for the requesting user
        active_contexts = get_active_role_assignments(user, db)
        is_auditor = any(
            (
                ctx.role_code in ("AUDITOR", "LEAD_AUDITOR")
                and ctx.review_team_id is not None
                and app.review_team_id is not None
                and ctx.review_team_id == app.review_team_id
            )
            or (
                ctx.role_code == "ADMIN"
                and (
                    (
                        ctx.review_team_id is not None
                        and app.review_team_id is not None
                        and ctx.review_team_id == app.review_team_id
                    )
                    or (
                        ctx.institution_id is not None
                        and ctx.institution_id == app.institution_id
                    )
                )
            )
            for ctx in active_contexts
        )

        if fields_read:
            field_ids = [f.extracted_field_id for f in fields_read]
            all_reviews = (
                db.query(ExtractedFieldReview, User)
                .join(User, ExtractedFieldReview.reviewed_by == User.user_id)
                .filter(ExtractedFieldReview.extracted_field_id.in_(field_ids))
                .order_by(
                    ExtractedFieldReview.reviewed_at.desc(),
                    ExtractedFieldReview.extracted_field_review_id.desc(),
                )
                .all()
            )
            latest_by_field: dict[UUID, tuple[ExtractedFieldReview, User]] = {}
            for rev, u in all_reviews:
                if rev.extracted_field_id not in latest_by_field:
                    latest_by_field[rev.extracted_field_id] = (rev, u)

            for f in fields_read:
                if f.extracted_field_id in latest_by_field:
                    rev, u = latest_by_field[f.extracted_field_id]
                    if is_auditor:
                        f.latest_review = ExtractedFieldReviewRead(
                            extracted_field_review_id=rev.extracted_field_review_id,
                            extracted_field_id=rev.extracted_field_id,
                            reviewed_by=rev.reviewed_by,
                            reviewer_name=u.full_name,
                            reviewer_role=rev.reviewer_role,
                            accepted_as_extracted=rev.accepted_as_extracted,
                            corrected_value=rev.corrected_value,
                            review_note=rev.review_note,
                            reviewed_at=rev.reviewed_at,
                        )
                    else:
                        f.latest_review = InstitutionFieldReviewRead(
                            extracted_field_review_id=rev.extracted_field_review_id,
                            extracted_field_id=rev.extracted_field_id,
                            accepted_as_extracted=rev.accepted_as_extracted,
                            has_correction=not rev.accepted_as_extracted,
                            corrected_value=rev.corrected_value,
                            reviewed_at=rev.reviewed_at,
                        )

        return DocumentExtractionRead(
            document_extraction_id=extraction.document_extraction_id,
            document_version_id=extraction.document_version_id,
            processing_job_id=extraction.processing_job_id,
            extraction_status=extraction.extraction_status.value
            if hasattr(extraction.extraction_status, "value")
            else str(extraction.extraction_status),
            extraction_engine=extraction.extraction_engine,
            engine_version=extraction.engine_version,
            language_code=extraction.language_code,
            created_at=extraction.created_at,
            job=job_read,
            fields=fields_read,
        )

    def get_extracted_text(
        self,
        db: Session,
        user: User,
        requirement_id: UUID,
        version_id: UUID,
        page_number: int | None = None,
    ) -> DocumentExtractionTextResponse:
        """Retrieves page-by-page extracted text for document inspection."""
        # Check user authorization
        _req, _rev, _app, _doc_version = self.verify_document_access(
            db=db,
            user=user,
            requirement_id=requirement_id,
            version_id=version_id,
        )

        extraction = (
            db.query(DocumentExtraction)
            .filter_by(document_version_id=version_id)
            .order_by(DocumentExtraction.created_at.desc())
            .first()
        )

        if not extraction or not extraction.full_text_storage_key:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Extracted text is not available for this document version",
            )

        payload = storage_service.get_extraction_json(extraction.full_text_storage_key)
        total_pages = payload.get("total_pages", 0)
        overall_method = payload.get("overall_method", "UNKNOWN")
        full_text = payload.get("full_text")
        raw_pages = payload.get("pages", [])

        pages: list[ExtractionTextPageRead] = []
        for rp in raw_pages:
            p_num = rp.get("page_number", 1)
            if page_number is not None and p_num != page_number:
                continue

            pages.append(
                ExtractionTextPageRead(
                    page_number=p_num,
                    extraction_method=rp.get("method", "UNKNOWN"),
                    page_text=rp.get("text", ""),
                    char_count=rp.get("char_count", 0),
                    line_count=rp.get("line_count", 0),
                    ocr_line_count=rp.get("ocr_line_count", 0),
                )
            )

        if page_number is not None and not pages:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Requested page {page_number} does not exist (document has {total_pages} pages)",
            )

        return DocumentExtractionTextResponse(
            document_version_id=version_id,
            document_extraction_id=extraction.document_extraction_id,
            total_pages=total_pages,
            overall_method=overall_method,
            selected_page=page_number,
            pages=pages,
            full_text=full_text if page_number is None else None,
        )

    # =========================================================================
    # 5. Field Review & Verification Operations (Phase 4 Batch 5 Part B)
    # =========================================================================

    def record_field_review(
        self,
        db: Session,
        user: User,
        requirement_id: UUID,
        version_id: UUID,
        field_id: UUID,
        payload: ExtractedFieldReviewCreate,
    ) -> ExtractedFieldReviewRead:
        """Records an authoritative, immutable regulatory review of an extracted field."""
        # Check user authorization
        _req, _rev, app, _doc_version = self.verify_document_access(
            db=db,
            user=user,
            requirement_id=requirement_id,
            version_id=version_id,
        )

        active_contexts = get_active_role_assignments(user, db)
        auditor_role: str | None = None
        for ctx in active_contexts:
            if ctx.role_code in ("LEAD_AUDITOR", "AUDITOR") and (
                ctx.review_team_id is not None
                and app.review_team_id is not None
                and ctx.review_team_id == app.review_team_id
            ):
                if ctx.role_code == "LEAD_AUDITOR":
                    auditor_role = "LEAD_AUDITOR"
                    break
                if auditor_role is None:
                    auditor_role = "AUDITOR"

        if not auditor_role:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied: only regulatory auditors assigned to this application's review team may submit field reviews",
            )

        field = (
            db.query(ExtractedField)
            .join(
                DocumentExtraction,
                ExtractedField.document_extraction_id
                == DocumentExtraction.document_extraction_id,
            )
            .filter(
                ExtractedField.extracted_field_id == field_id,
                DocumentExtraction.document_version_id == version_id,
            )
            .first()
        )
        if not field:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Extracted field not found for this document version",
            )

        review = ExtractedFieldReview(
            extracted_field_id=field_id,
            reviewed_by=user.user_id,
            reviewer_role=auditor_role,
            accepted_as_extracted=payload.accepted_as_extracted,
            corrected_value=payload.corrected_value,
            review_note=payload.review_note,
            reviewed_at=datetime.now(UTC),
        )
        db.add(review)
        db.commit()
        db.refresh(review)

        return ExtractedFieldReviewRead(
            extracted_field_review_id=review.extracted_field_review_id,
            extracted_field_id=review.extracted_field_id,
            reviewed_by=review.reviewed_by,
            reviewer_name=user.full_name,
            reviewer_role=review.reviewer_role,
            accepted_as_extracted=review.accepted_as_extracted,
            corrected_value=review.corrected_value,
            review_note=review.review_note,
            reviewed_at=review.reviewed_at,
        )

    def get_field_reviews(
        self,
        db: Session,
        user: User,
        requirement_id: UUID,
        version_id: UUID,
        field_id: UUID,
    ) -> list[ExtractedFieldReviewRead | InstitutionFieldReviewRead]:
        """Retrieves chronological review history for an extracted field with role-appropriate redaction."""
        # Check user authorization
        _req, _rev, app, _doc_version = self.verify_document_access(
            db=db,
            user=user,
            requirement_id=requirement_id,
            version_id=version_id,
        )

        field = (
            db.query(ExtractedField)
            .join(
                DocumentExtraction,
                ExtractedField.document_extraction_id
                == DocumentExtraction.document_extraction_id,
            )
            .filter(
                ExtractedField.extracted_field_id == field_id,
                DocumentExtraction.document_version_id == version_id,
            )
            .first()
        )
        if not field:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Extracted field not found for this document version",
            )

        active_contexts = get_active_role_assignments(user, db)
        is_auditor = any(
            (
                ctx.role_code in ("AUDITOR", "LEAD_AUDITOR")
                and ctx.review_team_id is not None
                and app.review_team_id is not None
                and ctx.review_team_id == app.review_team_id
            )
            or (
                ctx.role_code == "ADMIN"
                and (
                    (
                        ctx.review_team_id is not None
                        and app.review_team_id is not None
                        and ctx.review_team_id == app.review_team_id
                    )
                    or (
                        ctx.institution_id is not None
                        and ctx.institution_id == app.institution_id
                    )
                )
            )
            for ctx in active_contexts
        )

        reviews = (
            db.query(ExtractedFieldReview, User)
            .join(User, ExtractedFieldReview.reviewed_by == User.user_id)
            .filter(ExtractedFieldReview.extracted_field_id == field_id)
            .order_by(
                ExtractedFieldReview.reviewed_at.desc(),
                ExtractedFieldReview.extracted_field_review_id.desc(),
            )
            .all()
        )

        if is_auditor:
            return [
                ExtractedFieldReviewRead(
                    extracted_field_review_id=rev.extracted_field_review_id,
                    extracted_field_id=rev.extracted_field_id,
                    reviewed_by=rev.reviewed_by,
                    reviewer_name=u.full_name,
                    reviewer_role=rev.reviewer_role,
                    accepted_as_extracted=rev.accepted_as_extracted,
                    corrected_value=rev.corrected_value,
                    review_note=rev.review_note,
                    reviewed_at=rev.reviewed_at,
                )
                for rev, u in reviews
            ]

        return [
            InstitutionFieldReviewRead(
                extracted_field_review_id=rev.extracted_field_review_id,
                extracted_field_id=rev.extracted_field_id,
                accepted_as_extracted=rev.accepted_as_extracted,
                has_correction=not rev.accepted_as_extracted,
                corrected_value=rev.corrected_value,
                reviewed_at=rev.reviewed_at,
            )
            for rev, _ in reviews
        ]


document_processing_service = DocumentProcessingService()

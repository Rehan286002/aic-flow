import logging
from pathlib import Path
from uuid import UUID

from fastapi import HTTPException, UploadFile, status
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.api.deps import get_active_role_assignments
from app.models.application import Application
from app.models.application_document_link import ApplicationDocumentLink
from app.models.application_requirements import ApplicationRequirement
from app.models.application_revision import ApplicationRevision
from app.models.checklist_item import ChecklistItem
from app.models.document import Document
from app.models.document_metadata_observation import DocumentMetadataObservation
from app.models.document_processing_job import DocumentProcessingJob
from app.models.document_security_scan import DocumentSecurityScan
from app.models.document_type import DocumentType
from app.models.document_version import DocumentVersion
from app.models.enums import DocumentProcessingStatus, RequirementStatus
from app.models.user import User
from app.schemas.document import (
    DocumentHistoryResponse,
    DocumentSecurityScanRead,
    DocumentUploadResponse,
    DocumentVersionRead,
)
from app.schemas.document_extraction import DocumentProcessingJobRead
from app.services.document_validation_service import (
    document_validation_service,
)
from app.services.malware_scanner import (
    BaseMalwareScanner,
    ScanResult,
    get_malware_scanner,
)
from app.services.storage_service import storage_service

logger = logging.getLogger(__name__)


DOCUMENT_TEAM_ROLES = {
    "AUDITOR",
    "LEAD_AUDITOR",
    "INTAKE_OFFICER",
    "SCRUTINY_OFFICER",
    "REGIONAL_OFFICER",
    "EVC_COORDINATOR",
    "EVC_MEMBER",
    "COMMITTEE_SECRETARIAT",
    "SAC_SECRETARIAT",
    "COUNCIL_SECRETARIAT",
    "BUREAU_SUPERVISOR",
    "COMPETENT_AUTHORITY",
}


def has_document_scope_access(
    institution_id: UUID,
    review_team_id: UUID | None,
    role_contexts: list[object],
) -> bool:
    """Check document access against the institution or the application's active review team."""
    for context in role_contexts:
        role_code = getattr(context, "role_code", None)
        context_institution_id = getattr(context, "institution_id", None)
        context_review_team_id = getattr(context, "review_team_id", None)
        if role_code == "ADMIN":
            return True
        if role_code == "INSTITUTION_USER" and context_institution_id == institution_id:
            return True
        if role_code == "INTAKE_OFFICER" and review_team_id is None:
            return True
        if (
            role_code in DOCUMENT_TEAM_ROLES
            and review_team_id is not None
            and context_review_team_id == review_team_id
        ):
            return True
    return False


class DocumentUploadService:
    def __init__(self, scanner: BaseMalwareScanner | None = None):
        self._scanner = scanner

    @property
    def scanner(self) -> BaseMalwareScanner:
        if self._scanner is None:
            return get_malware_scanner()
        return self._scanner

    def _get_requirement_with_lock(
        self,
        db: Session,
        application_requirement_id: UUID,
    ) -> ApplicationRequirement:
        req = (
            db.query(ApplicationRequirement)
            .filter_by(application_requirement_id=application_requirement_id)
            .with_for_update()
            .first()
        )
        if not req:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Application requirement not found",
            )
        return req

    def _verify_institution_access(
        self,
        db: Session,
        requirement: ApplicationRequirement,
        user: User,
    ) -> tuple[ApplicationRevision, Application]:
        rev = (
            db.query(ApplicationRevision)
            .filter_by(application_revision_id=requirement.application_revision_id)
            .first()
        )
        if not rev:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Application revision not found",
            )

        app = db.query(Application).filter_by(application_id=rev.application_id).first()
        if not app:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Application not found",
            )

        # Check tenant and review-team isolation against validated active role contexts.
        active_contexts = get_active_role_assignments(user, db)
        if not has_document_scope_access(
            app.institution_id,
            app.review_team_id,
            active_contexts,
        ):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied: the application is outside your institution or review-team scope.",
            )

        return rev, app

    def _build_version_read(
        self,
        version: DocumentVersion,
        security_scan: DocumentSecurityScan | None = None,
        processing_job: DocumentProcessingJob | None = None,
    ) -> DocumentVersionRead:
        scan_read = None
        is_clean = False
        is_downloadable = False

        if security_scan:
            scan_read = DocumentSecurityScanRead(
                document_security_scan_id=security_scan.document_security_scan_id,
                scanner_name=security_scan.scanner_name,
                scanner_version=security_scan.scanner_version,
                signature_database_version=security_scan.signature_database_version,
                scan_status=security_scan.scan_status,
                threat_name=security_scan.threat_name,
                scanned_at=security_scan.scanned_at,
                scan_log_reference=security_scan.scan_log_reference,
            )
            is_clean = security_scan.scan_status == "CLEAN"
            is_downloadable = is_clean

        job_read = None
        if processing_job:
            job_read = DocumentProcessingJobRead(
                document_processing_job_id=processing_job.document_processing_job_id,
                document_version_id=processing_job.document_version_id,
                processing_status=processing_job.processing_status,
                pipeline_name=processing_job.pipeline_name,
                pipeline_version=processing_job.pipeline_version,
                queued_at=processing_job.queued_at,
                started_at=processing_job.started_at,
                completed_at=processing_job.completed_at,
                error_code=processing_job.error_code,
                error_message=processing_job.error_message,
            )

        return DocumentVersionRead(
            document_version_id=version.document_version_id,
            document_id=version.document_id,
            version_number=version.version_number,
            original_filename=version.original_filename,
            mime_type=version.mime_type,
            file_size_bytes=version.file_size_bytes,
            sha256_hex=version.sha256_hex,
            uploaded_at=version.uploaded_at,
            uploaded_by=version.uploaded_by,
            replaces_document_version_id=version.replaces_document_version_id,
            security_scan=scan_read,
            processing_job=job_read,
            is_clean=is_clean,
            is_downloadable=is_downloadable,
        )

    def get_active_clean_version(
        self,
        db: Session,
        application_requirement_id: UUID,
    ) -> tuple[DocumentVersion | None, DocumentSecurityScan | None]:
        """Returns the latest CLEAN DocumentVersion and its security scan for this requirement."""
        links = (
            db.query(ApplicationDocumentLink)
            .filter_by(uploaded_for_requirement_id=application_requirement_id)
            .all()
        )
        if not links:
            return None, None

        version_ids = [l.document_version_id for l in links]
        versions = (
            db.query(DocumentVersion)
            .filter(DocumentVersion.document_version_id.in_(version_ids))
            .order_by(DocumentVersion.version_number.desc())
            .all()
        )

        for v in versions:
            scan = (
                db.query(DocumentSecurityScan)
                .filter_by(document_version_id=v.document_version_id)
                .order_by(DocumentSecurityScan.scanned_at.desc())
                .first()
            )
            if scan and scan.scan_status == "CLEAN":
                return v, scan

        return None, None

    def get_requirement_history(
        self,
        db: Session,
        application_requirement_id: UUID,
        user: User,
    ) -> DocumentHistoryResponse:
        req = self._get_requirement_with_lock(db, application_requirement_id)
        self._verify_institution_access(db, req, user)

        checklist_item = (
            db.query(ChecklistItem)
            .filter_by(checklist_item_id=req.checklist_item_id)
            .first()
        )

        links = (
            db.query(ApplicationDocumentLink)
            .filter_by(uploaded_for_requirement_id=application_requirement_id)
            .all()
        )
        version_ids = [l.document_version_id for l in links]

        version_reads: list[DocumentVersionRead] = []
        active_version_id = None

        if version_ids:
            versions = (
                db.query(DocumentVersion)
                .filter(DocumentVersion.document_version_id.in_(version_ids))
                .order_by(DocumentVersion.version_number.desc())
                .all()
            )
            for v in versions:
                scan = (
                    db.query(DocumentSecurityScan)
                    .filter_by(document_version_id=v.document_version_id)
                    .order_by(DocumentSecurityScan.scanned_at.desc())
                    .first()
                )
                job = (
                    db.query(DocumentProcessingJob)
                    .filter_by(document_version_id=v.document_version_id)
                    .order_by(DocumentProcessingJob.queued_at.desc())
                    .first()
                )
                v_read = self._build_version_read(v, scan, job)
                version_reads.append(v_read)
                if active_version_id is None and v_read.is_clean:
                    active_version_id = v.document_version_id

        return DocumentHistoryResponse(
            application_requirement_id=req.application_requirement_id,
            checklist_item_code=checklist_item.item_code if checklist_item else "",
            checklist_item_title=checklist_item.title if checklist_item else "",
            requirement_status=req.status.value,
            active_version_id=active_version_id,
            versions=version_reads,
        )

    async def upload_document(
        self,
        db: Session,
        application_requirement_id: UUID,
        user: User,
        upload_file: UploadFile,
        *,
        update_requirement_status: bool = True,
    ) -> DocumentUploadResponse:
        # 1. Lock requirement row
        req = self._get_requirement_with_lock(db, application_requirement_id)
        rev, app = self._verify_institution_access(db, req, user)

        if req.applicability_status != "APPLICABLE":
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Cannot upload documents for requirement with status '{req.applicability_status}'",
            )

        checklist_item = (
            db.query(ChecklistItem)
            .filter_by(checklist_item_id=req.checklist_item_id)
            .first()
        )

        # 2. Stream to quarantine storage
        (
            quarantine_path,
            sha256_hex,
            file_size,
        ) = await storage_service.save_to_quarantine(upload_file)
        created_disk_path: Path = quarantine_path

        try:
            # 3. Format and magic byte validation
            raw_filename = upload_file.filename or "uploaded_document"
            val_result = document_validation_service.validate_file_format(
                filename=raw_filename,
                file_path=quarantine_path,
                declared_mime_type=upload_file.content_type,
            )

            # 4. Malware scan with ClamAV
            scan_result: ScanResult = await self.scanner.scan_file(quarantine_path)

            if scan_result.status == "CLEAN":
                dest_path, storage_key = storage_service.move_to_clean(quarantine_path)
                created_disk_path = dest_path
            elif scan_result.status == "DETECTED":
                dest_path, storage_key = storage_service.move_to_rejected(
                    quarantine_path
                )
                created_disk_path = dest_path
            else:  # ERROR
                storage_key = storage_service.get_relative_key_for_quarantine(
                    quarantine_path
                )
                created_disk_path = quarantine_path

            # 5. Determine Document and Version numbering
            existing_links = (
                db.query(ApplicationDocumentLink)
                .filter_by(uploaded_for_requirement_id=application_requirement_id)
                .all()
            )

            parent_document: Document | None = None
            new_version_num = 1
            replaces_version_id: UUID | None = None

            if existing_links:
                # Find document id from earliest link
                first_link = existing_links[0]
                prev_v = (
                    db.query(DocumentVersion)
                    .filter_by(document_version_id=first_link.document_version_id)
                    .first()
                )
                if prev_v:
                    parent_document = (
                        db.query(Document)
                        .filter_by(document_id=prev_v.document_id)
                        .first()
                    )
                    # Find highest existing version
                    max_ver = (
                        db.query(func.max(DocumentVersion.version_number))
                        .filter_by(document_id=prev_v.document_id)
                        .scalar()
                        or 0
                    )
                    new_version_num = max_ver + 1
                    # Most recent version is the one being replaced
                    latest_v = (
                        db.query(DocumentVersion)
                        .filter_by(
                            document_id=prev_v.document_id,
                            version_number=max_ver,
                        )
                        .first()
                    )
                    if latest_v:
                        replaces_version_id = latest_v.document_version_id

            if not parent_document:
                # Resolve document type if possible
                doc_type = None
                if checklist_item and checklist_item.expected_document_type_code:
                    doc_type = (
                        db.query(DocumentType)
                        .filter_by(type_code=checklist_item.expected_document_type_code)
                        .first()
                    )

                parent_document = Document(
                    institution_id=app.institution_id,
                    document_type_id=doc_type.document_type_id if doc_type else None,
                    document_label=checklist_item.title
                    if checklist_item
                    else val_result.original_filename,
                    created_by=user.user_id,
                )
                db.add(parent_document)
                db.flush()

            # 6. Create DocumentVersion record
            doc_version = DocumentVersion(
                document_id=parent_document.document_id,
                version_number=new_version_num,
                original_filename=val_result.original_filename,
                storage_key=storage_key,
                mime_type=val_result.mime_type,
                file_size_bytes=file_size,
                sha256_hex=sha256_hex,
                uploaded_by=user.user_id,
                replaces_document_version_id=replaces_version_id,
            )
            db.add(doc_version)
            db.flush()

            # 7. Create ApplicationDocumentLink
            doc_link = ApplicationDocumentLink(
                application_revision_id=rev.application_revision_id,
                uploaded_for_requirement_id=req.application_requirement_id,
                document_version_id=doc_version.document_version_id,
            )
            db.add(doc_link)

            # 8. Create DocumentSecurityScan record
            sec_scan = DocumentSecurityScan(
                document_version_id=doc_version.document_version_id,
                scanner_name=scan_result.scanner_name,
                scanner_version=scan_result.scanner_version,
                signature_database_version=scan_result.signature_version,
                scan_status=scan_result.status,
                threat_name=scan_result.threat_name,
                scan_log_reference=scan_result.details,
            )
            db.add(sec_scan)

            # 9. Create DocumentProcessingJob record
            proc_job = DocumentProcessingJob(
                document_version_id=doc_version.document_version_id,
                processing_status=(
                    DocumentProcessingStatus.QUEUED
                    if scan_result.status == "CLEAN"
                    else DocumentProcessingStatus.FAILED
                ),
                pipeline_name="DOCUMENT_INGESTION_V1",
                pipeline_version="1.0.0",
                error_message=(
                    scan_result.threat_name
                    if scan_result.status == "DETECTED"
                    else scan_result.details
                ),
            )
            db.add(proc_job)

            # 10. Record DocumentMetadataObservations
            observations = [
                DocumentMetadataObservation(
                    document_version_id=doc_version.document_version_id,
                    metadata_source="SERVER_INGEST",
                    metadata_key="original_filename",
                    metadata_value=val_result.original_filename,
                    trust_level="SERVER_OBSERVED",
                ),
                DocumentMetadataObservation(
                    document_version_id=doc_version.document_version_id,
                    metadata_source="SERVER_INGEST",
                    metadata_key="sha256_hex",
                    metadata_value=sha256_hex,
                    trust_level="SERVER_OBSERVED",
                ),
                DocumentMetadataObservation(
                    document_version_id=doc_version.document_version_id,
                    metadata_source="SERVER_INGEST",
                    metadata_key="file_size_bytes",
                    metadata_value=str(file_size),
                    trust_level="SERVER_OBSERVED",
                ),
                DocumentMetadataObservation(
                    document_version_id=doc_version.document_version_id,
                    metadata_source="SERVER_INGEST",
                    metadata_key="mime_type",
                    metadata_value=val_result.mime_type,
                    trust_level="SERVER_OBSERVED",
                ),
            ]
            db.add_all(observations)

            # 11. Update requirement status
            if scan_result.status == "CLEAN":
                if update_requirement_status:
                    req.status = RequirementStatus.UPLOADED
                message = f"Document '{val_result.original_filename}' uploaded and verified clean (v{new_version_num})."
            elif scan_result.status == "DETECTED":
                if update_requirement_status:
                    active_v, _ = self.get_active_clean_version(db, application_requirement_id)
                    if not active_v:
                        req.status = RequirementStatus.PENDING
                message = (
                    f"SECURITY ALERT: Malware detected ({scan_result.threat_name}) in "
                    f"'{val_result.original_filename}'. Version {new_version_num} rejected."
                )
            else:  # ERROR
                if update_requirement_status:
                    active_v, _ = self.get_active_clean_version(db, application_requirement_id)
                    if not active_v:
                        req.status = RequirementStatus.PENDING
                message = (
                    f"Antivirus scanning error occurred for '{val_result.original_filename}'. "
                    f"File quarantined; please retry scan."
                )

            if update_requirement_status:
                req.last_evaluated_at = func.now()
            db.commit()

            # Find active clean version ID after commit
            active_clean, _ = self.get_active_clean_version(
                db, application_requirement_id
            )
            active_id = active_clean.document_version_id if active_clean else None

            version_read = self._build_version_read(doc_version, sec_scan, proc_job)

            return DocumentUploadResponse(
                message=message,
                application_requirement_id=req.application_requirement_id,
                document_version=version_read,
                requirement_status=req.status.value,
                active_version_id=active_id,
            )

        except Exception:
            db.rollback()
            # Clean up disk file created during failed transaction
            if created_disk_path and created_disk_path.exists():
                try:
                    created_disk_path.unlink()
                except OSError:
                    pass
            raise

    async def retry_scan(
        self,
        db: Session,
        application_requirement_id: UUID,
        document_version_id: UUID,
        user: User,
    ) -> DocumentUploadResponse:
        req = self._get_requirement_with_lock(db, application_requirement_id)
        _rev, _app = self._verify_institution_access(db, req, user)

        version = (
            db.query(DocumentVersion)
            .filter_by(document_version_id=document_version_id)
            .first()
        )
        if not version:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Document version not found",
            )

        # Get latest security scan
        latest_scan = (
            db.query(DocumentSecurityScan)
            .filter_by(document_version_id=document_version_id)
            .order_by(DocumentSecurityScan.scanned_at.desc())
            .first()
        )

        if latest_scan and latest_scan.scan_status == "CLEAN":
            return DocumentUploadResponse(
                message="Document is already scanned and marked CLEAN.",
                application_requirement_id=req.application_requirement_id,
                document_version=self._build_version_read(version, latest_scan),
                requirement_status=req.status.value,
                active_version_id=version.document_version_id,
            )

        current_file_path = storage_service.get_file_path(version.storage_key)
        scan_result = await self.scanner.scan_file(current_file_path)

        if scan_result.status == "CLEAN":
            _dest_path, storage_key = storage_service.move_to_clean(current_file_path)
            version.storage_key = storage_key
            req.status = RequirementStatus.UPLOADED
            message = f"Retry scan successful: document marked CLEAN (v{version.version_number})."
        elif scan_result.status == "DETECTED":
            _dest_path, storage_key = storage_service.move_to_rejected(
                current_file_path
            )
            version.storage_key = storage_key
            active_v, _ = self.get_active_clean_version(db, application_requirement_id)
            if not active_v:
                req.status = RequirementStatus.PENDING
            message = f"Malware detected during retry scan ({scan_result.threat_name}). Version rejected."
        else:
            message = "Antivirus scanner returned ERROR again during retry."

        new_scan = DocumentSecurityScan(
            document_version_id=version.document_version_id,
            scanner_name=scan_result.scanner_name,
            scanner_version=scan_result.scanner_version,
            signature_database_version=scan_result.signature_version,
            scan_status=scan_result.status,
            threat_name=scan_result.threat_name,
            scan_log_reference=scan_result.details,
        )
        db.add(new_scan)
        db.commit()

        active_clean, _ = self.get_active_clean_version(db, application_requirement_id)
        active_id = active_clean.document_version_id if active_clean else None

        latest_job = (
            db.query(DocumentProcessingJob)
            .filter_by(document_version_id=version.document_version_id)
            .order_by(DocumentProcessingJob.queued_at.desc())
            .first()
        )

        return DocumentUploadResponse(
            message=message,
            application_requirement_id=req.application_requirement_id,
            document_version=self._build_version_read(version, new_scan, latest_job),
            requirement_status=req.status.value,
            active_version_id=active_id,
        )

    def get_document_for_download(
        self,
        db: Session,
        application_requirement_id: UUID,
        document_version_id: UUID,
        user: User,
    ) -> tuple[Path, str, str]:
        """Validates security scan status and cryptographic integrity before permitting download.

        Returns (file_path, original_filename, mime_type).
        """
        req = self._get_requirement_with_lock(db, application_requirement_id)
        self._verify_institution_access(db, req, user)

        version = (
            db.query(DocumentVersion)
            .filter_by(document_version_id=document_version_id)
            .first()
        )
        if not version:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Document version not found",
            )

        # Check security scan status
        latest_scan = (
            db.query(DocumentSecurityScan)
            .filter_by(document_version_id=document_version_id)
            .order_by(DocumentSecurityScan.scanned_at.desc())
            .first()
        )

        if not latest_scan or latest_scan.scan_status != "CLEAN":
            if latest_scan and latest_scan.scan_status == "DETECTED":
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail=(
                        f"Download prohibited: this document version was rejected due to malware detection "
                        f"({latest_scan.threat_name})."
                    ),
                )
            elif latest_scan and latest_scan.scan_status == "ERROR":
                raise HTTPException(
                    status_code=status.HTTP_423_LOCKED,
                    detail="Download unavailable: security scan resulted in error and is pending retry.",
                )
            else:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Download prohibited: document has not passed antivirus security verification.",
                )

        file_path = storage_service.get_file_path(version.storage_key)

        # Cryptographic integrity re-verification
        if not storage_service.verify_integrity(file_path, version.sha256_hex):
            logger.critical(
                "INTEGRITY VIOLATION: File %s does not match recorded SHA-256 %s",
                file_path,
                version.sha256_hex,
            )
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="File integrity check failed: stored content does not match cryptographic signature.",
            )

        return file_path, version.original_filename, version.mime_type


document_upload_service = DocumentUploadService()

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict

from app.schemas.document_extraction import DocumentProcessingJobRead


class DocumentSecurityScanRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    document_security_scan_id: UUID
    scanner_name: str
    scanner_version: str | None = None
    signature_database_version: str | None = None
    scan_status: str  # CLEAN, DETECTED, ERROR, NOT_SCANNED
    threat_name: str | None = None
    scanned_at: datetime
    scan_log_reference: str | None = None


class DocumentVersionRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    document_version_id: UUID
    document_id: UUID
    version_number: int
    original_filename: str
    mime_type: str
    file_size_bytes: int
    sha256_hex: str
    uploaded_at: datetime
    uploaded_by: UUID
    replaces_document_version_id: UUID | None = None
    security_scan: DocumentSecurityScanRead | None = None
    processing_job: DocumentProcessingJobRead | None = None
    is_clean: bool = False
    is_downloadable: bool = False


class DocumentRequirementStatusRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    application_requirement_id: UUID
    checklist_item_code: str
    checklist_item_title: str
    applicability_status: str
    requirement_status: str
    active_version: DocumentVersionRead | None = None
    total_versions: int = 0


class DocumentUploadResponse(BaseModel):
    message: str
    application_requirement_id: UUID
    document_version: DocumentVersionRead
    requirement_status: str
    active_version_id: UUID | None = None


class DocumentHistoryResponse(BaseModel):
    application_requirement_id: UUID
    checklist_item_code: str
    checklist_item_title: str
    requirement_status: str
    active_version_id: UUID | None = None
    versions: list[DocumentVersionRead]

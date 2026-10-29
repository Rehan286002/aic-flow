from typing import Annotated
from uuid import UUID

from fastapi import (
    APIRouter,
    BackgroundTasks,
    Depends,
    File,
    Query,
    UploadFile,
    status,
)
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, get_db, verify_csrf
from app.models.user import User
from app.schemas.document import (
    DocumentHistoryResponse,
    DocumentUploadResponse,
)
from app.schemas.document_extraction import (
    DocumentExtractionRead,
    DocumentExtractionTextResponse,
    DocumentProcessingJobRead,
    ExtractedFieldReviewCreate,
    ExtractedFieldReviewRead,
    InstitutionFieldReviewRead,
)
from app.services.document_processing_service import document_processing_service
from app.services.document_upload_service import document_upload_service

router = APIRouter(
    prefix="/requirements/{requirement_id}/documents",
    tags=["documents"],
)


@router.post(
    "",
    response_model=DocumentUploadResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Upload evidence document for a checklist requirement",
)
async def upload_document_endpoint(
    requirement_id: UUID,
    file: Annotated[UploadFile, File(...)],
    current_user: Annotated[User, Depends(get_current_user)],
    _csrf: Annotated[str, Depends(verify_csrf)],
    db: Annotated[Session, Depends(get_db)],
) -> DocumentUploadResponse:
    """Uploads, validates, quarantines, scans with ClamAV, and records a new version

    of evidence for the designated requirement.
    """
    return await document_upload_service.upload_document(
        db=db,
        application_requirement_id=requirement_id,
        user=current_user,
        upload_file=file,
    )


@router.get(
    "",
    response_model=DocumentHistoryResponse,
    summary="Retrieve document version history for a checklist requirement",
)
def get_document_history_endpoint(
    requirement_id: UUID,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
) -> DocumentHistoryResponse:
    """Returns the full version history, security scan records, and active version

    pointer for the requirement.
    """
    return document_upload_service.get_requirement_history(
        db=db,
        application_requirement_id=requirement_id,
        user=current_user,
    )


@router.post(
    "/{version_id}/retry-scan",
    response_model=DocumentUploadResponse,
    summary="Retry antivirus scan on a quarantined or failed document version",
)
async def retry_scan_endpoint(
    requirement_id: UUID,
    version_id: UUID,
    current_user: Annotated[User, Depends(get_current_user)],
    _csrf: Annotated[str, Depends(verify_csrf)],
    db: Annotated[Session, Depends(get_db)],
) -> DocumentUploadResponse:
    """Re-runs the malware scanner on an existing quarantined version that had a scan error."""
    return await document_upload_service.retry_scan(
        db=db,
        application_requirement_id=requirement_id,
        document_version_id=version_id,
        user=current_user,
    )


@router.get(
    "/{version_id}/download",
    summary="Securely download clean document evidence",
)
def download_document_endpoint(
    requirement_id: UUID,
    version_id: UUID,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
) -> FileResponse:
    """Streams the document file if and only if it has passed antivirus inspection

    (CLEAN) and verified against its recorded SHA-256 checksum.
    """
    file_path, filename, mime_type = document_upload_service.get_document_for_download(
        db=db,
        application_requirement_id=requirement_id,
        document_version_id=version_id,
        user=current_user,
    )

    return FileResponse(
        path=file_path,
        media_type=mime_type,
        filename=filename,
        content_disposition_type="attachment",
        headers={
            "X-Content-Type-Options": "nosniff",
            "Cache-Control": "private, no-cache, no-store, must-revalidate",
        },
    )


@router.post(
    "/{version_id}/process",
    response_model=DocumentProcessingJobRead,
    status_code=status.HTTP_202_ACCEPTED,
    summary="Explicitly trigger content extraction on a clean document version",
)
def process_document_endpoint(
    requirement_id: UUID,
    version_id: UUID,
    background_tasks: BackgroundTasks,
    current_user: Annotated[User, Depends(get_current_user)],
    _csrf: Annotated[str, Depends(verify_csrf)],
    db: Annotated[Session, Depends(get_db)],
) -> DocumentProcessingJobRead:
    """Explicitly triggers content extraction and structured field parsing for a clean

    evidence document. Returns HTTP 202 with job state.
    """
    job, should_schedule = document_processing_service.trigger_processing(
        db=db,
        user=current_user,
        requirement_id=requirement_id,
        version_id=version_id,
    )

    if should_schedule:
        background_tasks.add_task(
            document_processing_service.execute_processing_job,
            job_id=job.document_processing_job_id,
            requirement_id=requirement_id,
            version_id=version_id,
        )

    return job


@router.get(
    "/{version_id}/extraction",
    response_model=DocumentExtractionRead,
    summary="Retrieve structured candidate fields and extraction metadata",
)
def get_extraction_endpoint(
    requirement_id: UUID,
    version_id: UUID,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
) -> DocumentExtractionRead:
    """Returns candidate fields with full Batch 3 provenance, bounding boxes,

    heuristics matching strength, and raw OCR confidence.
    """
    return document_processing_service.get_extraction_result(
        db=db,
        user=current_user,
        requirement_id=requirement_id,
        version_id=version_id,
    )


@router.get(
    "/{version_id}/extraction/text",
    response_model=DocumentExtractionTextResponse,
    summary="Retrieve page-by-page extracted text for document inspection",
)
def get_extraction_text_endpoint(
    requirement_id: UUID,
    version_id: UUID,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
    page: Annotated[
        int | None,
        Query(
            ge=1,
            description="1-indexed page number for page-level retrieval",
        ),
    ] = None,
) -> DocumentExtractionTextResponse:
    """Returns page-by-page extracted text, extraction method, line counts, and

    optionally full concatenated document text. Supports pagination via the 'page' parameter.
    """
    return document_processing_service.get_extracted_text(
        db=db,
        user=current_user,
        requirement_id=requirement_id,
        version_id=version_id,
        page_number=page,
    )


@router.post(
    "/{version_id}/fields/{field_id}/reviews",
    response_model=ExtractedFieldReviewRead,
    status_code=status.HTTP_201_CREATED,
    summary="Record an immutable auditor review (accept or correct) for an extracted field",
)
def create_field_review_endpoint(
    requirement_id: UUID,
    version_id: UUID,
    field_id: UUID,
    payload: ExtractedFieldReviewCreate,
    current_user: Annotated[User, Depends(get_current_user)],
    _csrf: Annotated[str, Depends(verify_csrf)],
    db: Annotated[Session, Depends(get_db)],
) -> ExtractedFieldReviewRead:
    """Submits an authoritative regulatory review of an automated candidate field.
    Only authorized AUDITOR or LEAD_AUDITOR assigned to the application's review team may review.
    Enforces strict append-only immutability.
    """
    return document_processing_service.record_field_review(
        db=db,
        user=current_user,
        requirement_id=requirement_id,
        version_id=version_id,
        field_id=field_id,
        payload=payload,
    )


@router.get(
    "/{version_id}/fields/{field_id}/reviews",
    response_model=list[ExtractedFieldReviewRead | InstitutionFieldReviewRead],
    summary="Retrieve audit review history for an extracted field",
)
def get_field_reviews_endpoint(
    requirement_id: UUID,
    version_id: UUID,
    field_id: UUID,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
) -> list[ExtractedFieldReviewRead | InstitutionFieldReviewRead]:
    """Retrieves chronological review history for an extracted field.
    Auditors receive full provenance and review notes; Institution users receive a sanitized projection.
    """
    return document_processing_service.get_field_reviews(
        db=db,
        user=current_user,
        requirement_id=requirement_id,
        version_id=version_id,
        field_id=field_id,
    )

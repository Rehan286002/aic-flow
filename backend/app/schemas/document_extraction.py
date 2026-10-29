import re
from datetime import datetime
from typing import Any, Self
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, model_validator


class DocumentProcessingJobRead(BaseModel):
    """Schema for document processing job status and timing information."""

    model_config = ConfigDict(from_attributes=True)

    document_processing_job_id: UUID
    document_version_id: UUID
    processing_status: str
    pipeline_name: str
    pipeline_version: str | None = None
    queued_at: datetime
    started_at: datetime | None = None
    completed_at: datetime | None = None
    error_code: str | None = None
    error_message: str | None = None


class ExtractedFieldReviewCreate(BaseModel):
    """Payload submitted by Auditor or Lead Auditor to record field verification decision."""

    accepted_as_extracted: bool
    corrected_value: Any | None = None
    review_note: str | None = None

    @model_validator(mode="after")
    def validate_decision_exclusivity(self) -> Self:
        if self.accepted_as_extracted:
            if self.corrected_value is not None:
                raise ValueError(
                    "When accepted_as_extracted is true, corrected_value must not be supplied."
                )
            if self.review_note and len(self.review_note) > 2000:
                raise ValueError("Review note cannot exceed 2000 characters.")
        else:
            if self.corrected_value is None:
                raise ValueError(
                    "When accepted_as_extracted is false, a corrected_value must be provided."
                )
            if not self.review_note or len(re.sub(r"\s", "", self.review_note)) < 5:
                raise ValueError(
                    "When correcting an extracted value, a review_note containing at least 5 non-whitespace characters is required."
                )
            if len(self.review_note) > 2000:
                raise ValueError("Review note cannot exceed 2000 characters.")
        return self


class ExtractedFieldReviewRead(BaseModel):
    """Authoritative review record returned to authorized regulatory auditors."""

    model_config = ConfigDict(from_attributes=True)

    extracted_field_review_id: UUID
    extracted_field_id: UUID
    reviewed_by: UUID
    reviewer_name: str
    reviewer_role: str
    accepted_as_extracted: bool
    corrected_value: Any | None = None
    review_note: str | None = None
    reviewed_at: datetime


class InstitutionFieldReviewRead(BaseModel):
    """Sanitized review projection returned to Institution Users with internal notes and reviewer identities withheld."""

    model_config = ConfigDict(from_attributes=True)

    extracted_field_review_id: UUID
    extracted_field_id: UUID
    accepted_as_extracted: bool
    has_correction: bool
    corrected_value: Any | None = None
    reviewed_at: datetime


class ExtractedFieldRead(BaseModel):
    """Schema for candidate extracted field with complete Batch 3 provenance."""

    model_config = ConfigDict(from_attributes=True)

    extracted_field_id: UUID
    document_extraction_id: UUID
    field_code: str
    field_label: str | None = None
    raw_value: str | None = None
    normalized_value: Any | None = None
    confidence: float | None = Field(
        default=None,
        description="Rule-based heuristic matching strength (0.0 to 1.0)",
    )
    page_number: int | None = None
    bounding_box: dict[str, Any] | None = None
    created_at: datetime | None = None

    # Full provenance attributes from private JSON payload
    ocr_confidence: float | None = Field(
        default=None,
        description="Raw line recognition score from OCR engine (None for native text)",
    )
    matching_strength: float | None = Field(
        default=None,
        description="Explicit matching strength heuristic",
    )
    review_category: str | None = Field(
        default=None,
        description="Provisional review tier: HIGH, MEDIUM_REVIEW, or LOW_UNCERTAIN",
    )
    source_snippet: str | None = Field(
        default=None,
        description="Contextual source line or nearby text snippet",
    )
    extraction_method: str | None = Field(
        default=None,
        description="NATIVE_TEXT or OCR",
    )
    notes: str | None = Field(
        default=None,
        description="Extraction rationale, ambiguity, or jurisdiction notes",
    )

    # Optional latest review summary
    latest_review: ExtractedFieldReviewRead | InstitutionFieldReviewRead | None = None


class DocumentExtractionRead(BaseModel):
    """Complete document extraction container including job status and fields."""

    model_config = ConfigDict(from_attributes=True)

    document_extraction_id: UUID
    document_version_id: UUID
    processing_job_id: UUID | None = None
    extraction_status: str
    extraction_engine: str
    engine_version: str | None = None
    language_code: str | None = None
    created_at: datetime
    job: DocumentProcessingJobRead | None = None
    fields: list[ExtractedFieldRead] = []


class ExtractionTextPageRead(BaseModel):
    """Extracted text details for a single document page."""

    page_number: int
    extraction_method: str
    page_text: str
    char_count: int
    line_count: int
    ocr_line_count: int = 0


class DocumentExtractionTextResponse(BaseModel):
    """Response payload for page-by-page extracted text inspection."""

    document_version_id: UUID
    document_extraction_id: UUID | None = None
    total_pages: int
    overall_method: str
    selected_page: int | None = None
    pages: list[ExtractionTextPageRead]
    full_text: str | None = None

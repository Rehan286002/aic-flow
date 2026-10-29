import uuid
from datetime import date, datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from app.models.enums import ApplicationFamily, ApplicationStatus, RevisionStatus
from app.schemas.checklist import ApplicationRequirementResponse


class ApplicationCreateRequest(BaseModel):
    """Payload to create an initial draft application for an academic year."""

    academic_year: str = Field(
        default="2026-27",
        pattern=r"^\d{4}-\d{2}$",
        description="Target academic year, e.g. 2026-27",
    )
    process_type: str = Field(
        default="EOA_SELF_DISCLOSURE", min_length=3, max_length=60,
        description="AICTE application process category; route is pinned at creation."
    )
    application_family: ApplicationFamily = Field(
        default=ApplicationFamily.EXISTING_INSTITUTION,
        description="Application regulatory family",
    )
    completion_certificate_issue_date: date | None = Field(
        default=None,
        description="Date of issue of building Completion / Occupancy Certificate",
    )
    payment_applicable: bool | None = Field(
        default=None,
        description="Whether payment fee is applicable for this institution under Chapter II",
    )
    application_remarks: str | None = Field(
        default=None,
        max_length=2000,
        description="Self-disclosure remarks or notes from applicant representative",
    )


class ApplicationUpdateRequest(BaseModel):
    """Payload to update editable draft application self-disclosure declarations."""

    completion_certificate_issue_date: date | None = Field(
        default=None,
        description="Date of issue of building Completion / Occupancy Certificate",
    )
    payment_applicable: bool | None = Field(
        default=None,
        description="Whether payment fee is applicable for this institution under Chapter II",
    )
    application_remarks: str | None = Field(
        default=None,
        max_length=2000,
        description="Self-disclosure remarks or notes from applicant representative",
    )


class ApplicationRevisionResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    application_revision_id: uuid.UUID
    application_id: uuid.UUID
    revision_number: int
    status: RevisionStatus
    created_at: datetime
    submitted_at: datetime | None = None
    declarations: dict[str, Any] = Field(
        default_factory=dict,
        description="Dynamic self-disclosure field values for this revision",
    )


class ApplicationStatusHistoryResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    application_status_history_id: uuid.UUID
    application_id: uuid.UUID
    from_status: ApplicationStatus | None = None
    to_status: ApplicationStatus
    changed_by: uuid.UUID | None = None
    change_reason: str | None = None
    changed_at: datetime


class ApplicationListItemResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    application_id: uuid.UUID
    application_number: str
    institution_id: uuid.UUID
    application_family: ApplicationFamily
    process_type: str = "EOA_SELF_DISCLOSURE"
    academic_year: str
    status: ApplicationStatus
    current_revision_id: uuid.UUID | None = None
    current_revision_number: int | None = None
    created_at: datetime
    updated_at: datetime


class ApplicationDetailResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    application_id: uuid.UUID
    application_number: str
    institution_id: uuid.UUID
    application_family: ApplicationFamily
    process_type: str = "EOA_SELF_DISCLOSURE"
    academic_year: str
    status: ApplicationStatus
    current_revision: ApplicationRevisionResponse
    status_history: list[ApplicationStatusHistoryResponse] = Field(default_factory=list)
    requirements: list[ApplicationRequirementResponse] = Field(default_factory=list)

    total_requirements: int = 0
    applicable_requirements: int = 0
    not_applicable_requirements: int = 0
    pending_requirements: int = 0
    satisfied_requirements: int = 0

    created_at: datetime
    updated_at: datetime

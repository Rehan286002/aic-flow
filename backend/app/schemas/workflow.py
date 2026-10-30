import uuid
from datetime import date, datetime
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field

from app.schemas.checklist import ApplicationRequirementResponse


class WorkflowCaseListResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    workflow_case_id: uuid.UUID
    application_id: uuid.UUID
    application_number: str
    institution_id: uuid.UUID
    institution_name: str
    review_team_id: uuid.UUID | None = None
    review_team_name: str | None = None
    academic_year: str
    process_type: str
    route_code: str
    regulatory_version: str
    route_snapshot: dict[str, Any]
    current_stage: str
    assigned_role_code: str | None = None
    assigned_user_id: uuid.UUID | None = None
    due_at: datetime | None = None
    stage_entered_at: datetime
    updated_at: datetime


class WorkflowEventResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    workflow_event_id: uuid.UUID
    workflow_case_id: uuid.UUID
    application_id: uuid.UUID
    event_type: str
    from_stage: str | None = None
    to_stage: str | None = None
    summary: str
    event_payload: dict[str, Any]
    actor_user_id: uuid.UUID | None = None
    occurred_at: datetime


class ComplianceObligationResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    obligation_id: uuid.UUID
    workflow_case_id: uuid.UUID
    application_id: uuid.UUID
    condition_code: str | None = None
    title: str
    description: str
    source_condition: str
    due_at: datetime
    status: str
    evidence_document_id: uuid.UUID | None = None
    evidence_reference: str | None = None
    verification_note: str | None = None
    created_by: uuid.UUID
    verified_by: uuid.UUID | None = None
    submitted_at: datetime | None = None
    verified_at: datetime | None = None
    created_at: datetime
    updated_at: datetime


class WorkflowCaseDetailResponse(WorkflowCaseListResponse):
    requirements: list[ApplicationRequirementResponse] = Field(default_factory=list)
    events: list[WorkflowEventResponse] = Field(default_factory=list)
    obligations: list[ComplianceObligationResponse] = Field(default_factory=list)


class WorkflowTransitionRequest(BaseModel):
    to_stage: str = Field(min_length=2, max_length=50)
    reason: str = Field(min_length=8, max_length=2000)
    due_at: datetime | None = None


class WorkflowEventCreateRequest(BaseModel):
    event_type: Literal[
        "EVC_VISIT_SCHEDULED",
        "EVC_REPORT_RECORDED",
        "COMMITTEE_CONVENED",
        "COMMITTEE_MINUTES_RECORDED",
        "OFFICER_NOTE",
        "DECISION_RECORDED",
        "DOCUMENT_VALIDITY_RECORDED",
        "DOCUMENT_RENEWAL_SUBMITTED",
        "DOCUMENT_VALIDITY_CONFIRMED",
        "ESCALATION_ACKNOWLEDGED",
        "ESCALATION_RESOLVED",
    ]
    summary: str = Field(min_length=8, max_length=2000)
    event_payload: dict[str, Any] = Field(default_factory=dict)


class ComplianceObligationCreateRequest(BaseModel):
    condition_code: str | None = Field(default=None, max_length=60)
    title: str = Field(min_length=3, max_length=220)
    description: str = Field(min_length=5, max_length=4000)
    source_condition: str = Field(min_length=5, max_length=4000)
    due_at: datetime


class ComplianceObligationActionRequest(BaseModel):
    action: Literal["EVIDENCE_SUBMITTED", "START_VERIFICATION", "VERIFY", "RETURN", "CLOSE"]
    evidence_document_id: uuid.UUID | None = None
    evidence_reference: str | None = Field(default=None, max_length=500)
    note: str = Field(min_length=5, max_length=2000)


class NotificationResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    notification_id: uuid.UUID
    application_id: uuid.UUID | None = None
    event_key: str
    title: str
    body: str
    severity: str
    read_at: datetime | None = None
    acknowledged_at: datetime | None = None
    created_at: datetime


class WorkflowTeamAssignmentRequest(BaseModel):
    review_team_id: uuid.UUID
    assigned_role_code: Literal[
        "INTAKE_OFFICER", "SCRUTINY_OFFICER", "EVC_COORDINATOR", "COMMITTEE_SECRETARIAT", "BUREAU_SUPERVISOR"
    ] = "INTAKE_OFFICER"
    assigned_user_id: uuid.UUID | None = None
    note: str = Field(min_length=8, max_length=1000)


class DocumentValidityCreateRequest(BaseModel):
    document_id: uuid.UUID
    document_version_id: uuid.UUID
    document_type: str = Field(min_length=3, max_length=60)
    issuer: str = Field(min_length=2, max_length=300)
    valid_from: date | None = None
    valid_until: date
    document_reference: str = Field(min_length=3, max_length=500)


class DocumentValidityActionRequest(BaseModel):
    action: Literal["VERIFY", "RETURN"]
    note: str = Field(min_length=5, max_length=2000)


class DocumentValidityResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    document_validity_id: uuid.UUID
    workflow_case_id: uuid.UUID
    application_id: uuid.UUID
    institution_id: uuid.UUID
    document_id: uuid.UUID
    document_version_id: uuid.UUID
    document_type: str
    issuer: str
    valid_from: date | None = None
    valid_until: date
    document_reference: str
    verification_status: str
    verification_note: str | None = None
    replacement_of_id: uuid.UUID | None = None
    created_by: uuid.UUID
    verified_by: uuid.UUID | None = None
    verified_at: datetime | None = None
    created_at: datetime
    updated_at: datetime

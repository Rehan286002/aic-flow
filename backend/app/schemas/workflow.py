import uuid
from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from app.schemas.checklist import ApplicationRequirementResponse


class WorkflowCaseListResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    workflow_case_id: uuid.UUID
    application_id: uuid.UUID
    application_number: str
    institution_id: uuid.UUID
    institution_name: str
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
    actor_user_id: uuid.UUID
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


class EVCVisitResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    evc_visit_id: uuid.UUID
    workflow_case_id: uuid.UUID
    application_id: uuid.UUID
    status: str
    visit_mode: str | None = None
    scheduled_start_at: datetime | None = None
    scheduled_end_at: datetime | None = None
    venue_or_meeting_details: str | None = None
    official_schedule_reference: str | None = None
    institution_contact_name: str | None = None
    institution_contact_email: str | None = None
    coordination_note: str | None = None
    schedule_revision: int
    report_reference: str | None = None
    report_summary: str | None = None
    report_outcome: str | None = None
    report_recorded_by: uuid.UUID | None = None
    report_recorded_at: datetime | None = None
    cancellation_reason: str | None = None
    created_by: uuid.UUID
    updated_by: uuid.UUID | None = None
    created_at: datetime
    updated_at: datetime


class EVCVisitScheduleRequest(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    visit_mode: Literal["ONLINE", "OFFLINE"]
    scheduled_start_at: datetime
    scheduled_end_at: datetime | None = None
    venue_or_meeting_details: str = Field(min_length=5, max_length=2000)
    official_schedule_reference: str | None = Field(default=None, max_length=180)
    institution_contact_name: str | None = Field(default=None, max_length=160)
    institution_contact_email: str | None = Field(default=None, max_length=254)
    coordination_note: str = Field(min_length=8, max_length=2000)

    @model_validator(mode="after")
    def validate_schedule(self):
        if self.scheduled_start_at.tzinfo is None or self.scheduled_start_at.utcoffset() is None:
            raise ValueError("EVC schedule start must include a timezone.")
        if self.scheduled_end_at is not None:
            if self.scheduled_end_at.tzinfo is None or self.scheduled_end_at.utcoffset() is None:
                raise ValueError("EVC schedule end must include a timezone.")
            if self.scheduled_end_at <= self.scheduled_start_at:
                raise ValueError("EVC schedule end must be later than its start.")
        return self


class EVCVisitReportRequest(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    report_reference: str = Field(min_length=3, max_length=180)
    report_summary: str = Field(min_length=10, max_length=6000)
    report_outcome: Literal["NO_DEFICIENCY_RECORDED", "DEFICIENCIES_OBSERVED", "FOLLOW_UP_REQUIRED", "INCONCLUSIVE"]
    note: str = Field(min_length=8, max_length=2000)


class EVCVisitCancelRequest(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    reason: str = Field(min_length=8, max_length=2000)


class WorkflowCaseDetailResponse(WorkflowCaseListResponse):
    requirements: list[ApplicationRequirementResponse] = Field(default_factory=list)
    events: list[WorkflowEventResponse] = Field(default_factory=list)
    obligations: list[ComplianceObligationResponse] = Field(default_factory=list)
    evc_visit: EVCVisitResponse | None = None


class WorkflowTransitionRequest(BaseModel):
    to_stage: str = Field(min_length=2, max_length=50)
    reason: str = Field(min_length=8, max_length=2000)
    due_at: datetime | None = None


class WorkflowEventCreateRequest(BaseModel):
    event_type: Literal[
        "COMMITTEE_CONVENED",
        "COMMITTEE_MINUTES_RECORDED",
        "OFFICER_NOTE",
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

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


class SHCProceedingResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    shc_proceeding_id: uuid.UUID
    workflow_case_id: uuid.UUID
    application_id: uuid.UUID
    status: str
    notice_reference: str | None = None
    hearing_mode: str | None = None
    hearing_scheduled_at: datetime | None = None
    hearing_details: str | None = None
    official_schedule_reference: str | None = None
    schedule_revision: int
    institution_submission_reference: str | None = None
    representative_one_name: str | None = None
    representative_one_designation: str | None = None
    representative_two_name: str | None = None
    representative_two_designation: str | None = None
    hearing_summary: str | None = None
    hearing_recorded_by: uuid.UUID | None = None
    hearing_recorded_at: datetime | None = None
    recommendation_code: str | None = None
    recommendation_text: str | None = None
    recommendation_reference: str | None = None
    recommendation_recorded_by: uuid.UUID | None = None
    recommendation_recorded_at: datetime | None = None
    created_by: uuid.UUID
    updated_by: uuid.UUID | None = None
    created_at: datetime
    updated_at: datetime


class SHCHearingScheduleRequest(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    hearing_mode: Literal["ONLINE", "IN_PERSON"]
    hearing_scheduled_at: datetime
    hearing_details: str = Field(min_length=5, max_length=2000)
    notice_reference: str | None = Field(default=None, min_length=2, max_length=180)
    official_schedule_reference: str | None = Field(default=None, min_length=2, max_length=180)

    @model_validator(mode="after")
    def validate_hearing_schedule(self):
        if self.hearing_scheduled_at.tzinfo is None or self.hearing_scheduled_at.utcoffset() is None:
            raise ValueError("SHC hearing schedule must include a timezone.")
        return self


class SHCComplianceSubmissionRequest(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    submission_reference: str = Field(min_length=5, max_length=500)
    note: str = Field(min_length=8, max_length=2000)


class SHCHearingRecordRequest(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    representative_one_name: str = Field(min_length=2, max_length=160)
    representative_one_designation: str = Field(min_length=2, max_length=160)
    representative_two_name: str = Field(min_length=2, max_length=160)
    representative_two_designation: str = Field(min_length=2, max_length=160)
    hearing_summary: str = Field(min_length=15, max_length=6000)
    note: str = Field(min_length=8, max_length=2000)


class SHCRecommendationRequest(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    recommendation_code: Literal[
        "COMPLIANCE_REVIEWED",
        "FURTHER_COMPLIANCE_REQUIRED",
        "DEFICIENCIES_REMAIN",
        "INCONCLUSIVE",
    ]
    recommendation_text: str = Field(min_length=15, max_length=6000)
    recommendation_reference: str | None = Field(default=None, min_length=2, max_length=180)


class ExecutiveCommitteeDecisionResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    executive_committee_decision_id: uuid.UUID
    workflow_case_id: uuid.UUID
    application_id: uuid.UUID
    outcome_code: str
    decision_reference: str
    decision_reasons: str
    speaking_order_reference: str
    speaking_order_uploaded_at: datetime
    appeal_deadline_at: datetime
    recorded_by: uuid.UUID
    recorded_at: datetime
    created_at: datetime


class ExecutiveCommitteeDecisionRequest(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    outcome_code: Literal["APPROVED", "APPROVED_WITH_CONDITIONS", "REJECTED"]
    decision_reference: str = Field(min_length=2, max_length=180)
    decision_reasons: str = Field(min_length=15, max_length=6000)
    speaking_order_reference: str = Field(min_length=2, max_length=180)
    speaking_order_uploaded_at: datetime

    @model_validator(mode="after")
    def validate_speaking_order_timestamp(self):
        if self.speaking_order_uploaded_at.tzinfo is None or self.speaking_order_uploaded_at.utcoffset() is None:
            raise ValueError("Speaking Order upload time must include a timezone.")
        return self


class SACAppealResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    sac_appeal_id: uuid.UUID
    executive_committee_decision_id: uuid.UUID
    workflow_case_id: uuid.UUID
    application_id: uuid.UUID
    shc_proceeding_id: uuid.UUID | None = None
    status: str
    appeal_reference: str | None = None
    appeal_grounds: str
    supporting_material_reference: str
    filed_by: uuid.UUID
    filed_at: datetime
    appeal_deadline_at: datetime
    hearing_mode: str | None = None
    hearing_scheduled_at: datetime | None = None
    hearing_details: str | None = None
    official_schedule_reference: str | None = None
    schedule_revision: int
    regulation_bureau_observation_reference: str | None = None
    regulation_bureau_observations: str | None = None
    bureau_observations_recorded_by: uuid.UUID | None = None
    bureau_observations_recorded_at: datetime | None = None
    representative_one_name: str | None = None
    representative_one_designation: str | None = None
    representative_one_id_reference: str | None = None
    representative_one_id_self_attested: bool | None = None
    representative_two_name: str | None = None
    representative_two_designation: str | None = None
    representative_two_id_reference: str | None = None
    representative_two_id_self_attested: bool | None = None
    hearing_summary: str | None = None
    hearing_recorded_by: uuid.UUID | None = None
    hearing_recorded_at: datetime | None = None
    recommendation_code: str | None = None
    recommendation_text: str | None = None
    recommendation_reference: str | None = None
    recommendation_recorded_by: uuid.UUID | None = None
    recommendation_recorded_at: datetime | None = None
    council_outcome_code: str | None = None
    council_decision_reference: str | None = None
    council_decision_text: str | None = None
    council_decision_uploaded_at: datetime | None = None
    council_decision_recorded_by: uuid.UUID | None = None
    council_decision_recorded_at: datetime | None = None
    created_at: datetime
    updated_at: datetime


class SACAppealFileRequest(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    appeal_reference: str | None = Field(default=None, min_length=2, max_length=180)
    appeal_grounds: str = Field(min_length=20, max_length=8000)
    supporting_material_reference: str = Field(min_length=5, max_length=3000)


class SACHearingScheduleRequest(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    hearing_mode: Literal["ONLINE", "IN_PERSON"]
    hearing_scheduled_at: datetime
    hearing_details: str = Field(min_length=5, max_length=2000)
    official_schedule_reference: str | None = Field(default=None, min_length=2, max_length=180)

    @model_validator(mode="after")
    def validate_sac_schedule(self):
        if self.hearing_scheduled_at.tzinfo is None or self.hearing_scheduled_at.utcoffset() is None:
            raise ValueError("SAC hearing schedule must include a timezone.")
        return self


class SACBureauObservationsRequest(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    observation_reference: str = Field(min_length=2, max_length=180)
    observations: str = Field(min_length=15, max_length=6000)


class SACHearingRecordRequest(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    representative_one_name: str = Field(min_length=2, max_length=160)
    representative_one_designation: str = Field(min_length=2, max_length=160)
    representative_one_id_reference: str = Field(min_length=3, max_length=500)
    representative_one_id_self_attested: Literal[True]
    representative_two_name: str = Field(min_length=2, max_length=160)
    representative_two_designation: str = Field(min_length=2, max_length=160)
    representative_two_id_reference: str = Field(min_length=3, max_length=500)
    representative_two_id_self_attested: Literal[True]
    hearing_summary: str = Field(min_length=20, max_length=8000)


class SACRecommendationRequest(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    recommendation_code: Literal["RECOMMEND_TO_COUNCIL", "NOT_RECOMMEND_TO_COUNCIL", "FURTHER_REVIEW_REQUIRED"]
    recommendation_text: str = Field(min_length=15, max_length=6000)
    recommendation_reference: str | None = Field(default=None, min_length=2, max_length=180)


class CouncilDecisionRequest(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    outcome_code: Literal[
        "UPHOLD_EXECUTIVE_COMMITTEE",
        "SET_ASIDE_EXECUTIVE_COMMITTEE",
        "MODIFY_EXECUTIVE_COMMITTEE",
        "REMAND_FOR_RECONSIDERATION",
    ]
    decision_reference: str = Field(min_length=2, max_length=180)
    decision_text: str = Field(min_length=15, max_length=6000)
    decision_uploaded_at: datetime

    @model_validator(mode="after")
    def validate_council_decision_timestamp(self):
        if self.decision_uploaded_at.tzinfo is None or self.decision_uploaded_at.utcoffset() is None:
            raise ValueError("Council decision upload time must include a timezone.")
        return self


class WorkflowCaseDetailResponse(WorkflowCaseListResponse):
    requirements: list[ApplicationRequirementResponse] = Field(default_factory=list)
    events: list[WorkflowEventResponse] = Field(default_factory=list)
    obligations: list[ComplianceObligationResponse] = Field(default_factory=list)
    evc_visit: EVCVisitResponse | None = None
    shc_proceeding: SHCProceedingResponse | None = None
    executive_committee_decision: ExecutiveCommitteeDecisionResponse | None = None
    sac_appeal: SACAppealResponse | None = None


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
        "INTAKE_OFFICER", "SCRUTINY_OFFICER", "EVC_COORDINATOR", "COMMITTEE_SECRETARIAT", "SAC_SECRETARIAT", "COUNCIL_SECRETARIAT", "BUREAU_SUPERVISOR"
    ] = "INTAKE_OFFICER"
    assigned_user_id: uuid.UUID | None = None
    note: str = Field(min_length=8, max_length=1000)

"""Approval workflow services for PS 26262.

The route snapshot is stored on every case so later policy edits do not silently
rewrite an in-flight application's route. Only the role package permitted for a
transition may move the case to its next stage.
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime, timedelta
from typing import Any

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.application import Application
from app.models.application_status_history import ApplicationStatusHistory
from app.models.application_revision import ApplicationRevision
from app.models.enums import RevisionStatus
from app.models.enums import ApplicationStatus
from app.models.compliance_obligation import ComplianceObligation
from app.models.evc_visit import EVCVisit
from app.models.executive_committee_decision import ExecutiveCommitteeDecision
from app.models.shc_proceeding import SHCProceeding
from app.models.in_app_notification import InAppNotification
from app.models.institution_membership import InstitutionMembership
from app.models.review_team_member import ReviewTeamMember
from app.models.workflow_case import WorkflowCase
from app.models.workflow_event import WorkflowEvent

# Only the profile below is automatically resolved from the baseline handbook.
# Other categories remain explicitly pending effective-dated policy confirmation.
ROUTE_PROFILES: dict[str, dict[str, Any]] = {
    "EOA_SELF_DISCLOSURE": {
        "route_code": "EOA_SELF_DISCLOSURE",
        "regulatory_version": "APH_2024_2027_BASELINE",
        "route_status": "CONFIGURED_BASELINE",
        "requires_scrutiny": False,
        "requires_evc": False,
        "requires_committee": False,
        "steps": ["INTAKE_REVIEW", "AWAITING_AUTHORITY"],
    },
    "INCREASE_INTAKE": {
        "route_code": "INCREASE_INTAKE_SCRUTINY_EVC",
        "regulatory_version": "APH_2024_2027_BASELINE",
        "route_status": "CONFIGURED_BASELINE_PARTIAL",
        "requires_scrutiny": True,
        "requires_evc": True,
        "requires_committee": None,
        "steps": ["INTAKE_REVIEW", "SCRUTINY", "EVC_COORDINATION", "EVC_SCHEDULED", "EVC_COMPLETED", "COMMITTEE_APPLICABILITY_REVIEW", "AWAITING_AUTHORITY"],
        "committee_note": "Committee applicability must be confirmed for the exact application category, academic year and effective regulatory amendments before authority routing.",
    },
}

# Role packages are deliberately distinct from dashboard workspaces.
TRANSITION_ROLES: dict[tuple[str, str], set[str]] = {
    ("DRAFT", "SUBMITTED"): {"INSTITUTION_USER"},
    ("SUBMITTED", "INTAKE_REVIEW"): {"INTAKE_OFFICER", "AUDITOR"},
    ("INTAKE_REVIEW", "SCRUTINY"): {"SCRUTINY_OFFICER", "AUDITOR"},
    ("INTAKE_REVIEW", "AWAITING_AUTHORITY"): {"INTAKE_OFFICER", "AUDITOR"},
    ("INTAKE_REVIEW", "CLARIFICATION_REQUESTED"): {"INTAKE_OFFICER", "AUDITOR"},
    ("SCRUTINY", "CLARIFICATION_REQUESTED"): {"SCRUTINY_OFFICER", "AUDITOR"},
    ("SCRUTINY", "EVC_COORDINATION"): {"SCRUTINY_OFFICER", "AUDITOR"},
    ("SCRUTINY", "AWAITING_AUTHORITY"): {"SCRUTINY_OFFICER", "AUDITOR"},
    ("CLARIFICATION_REQUESTED", "RESUBMITTED"): {"INSTITUTION_USER"},
    ("RESUBMITTED", "INTAKE_REVIEW"): {"INTAKE_OFFICER", "AUDITOR"},
    ("RESUBMITTED", "SCRUTINY"): {"SCRUTINY_OFFICER", "AUDITOR"},
    ("EVC_COORDINATION", "EVC_SCHEDULED"): {"EVC_COORDINATOR", "REGIONAL_OFFICER", "LEAD_AUDITOR"},
    ("EVC_SCHEDULED", "EVC_COMPLETED"): {"EVC_COORDINATOR", "EVC_MEMBER", "REGIONAL_OFFICER", "LEAD_AUDITOR"},
    ("EVC_COMPLETED", "COMMITTEE_PROCEEDINGS"): {"COMMITTEE_SECRETARIAT"},
    ("EVC_COMPLETED", "AWAITING_AUTHORITY"): {"EVC_COORDINATOR", "REGIONAL_OFFICER", "LEAD_AUDITOR"},
    ("COMMITTEE_PROCEEDINGS", "AWAITING_AUTHORITY"): {"COMMITTEE_SECRETARIAT"},
    ("AWAITING_AUTHORITY", "APPROVED"): {"COMPETENT_AUTHORITY"},
    ("AWAITING_AUTHORITY", "APPROVED_WITH_CONDITIONS"): {"COMPETENT_AUTHORITY"},
    ("AWAITING_AUTHORITY", "REJECTED"): {"COMPETENT_AUTHORITY"},
    ("AWAITING_AUTHORITY", "ON_HOLD"): {"COMPETENT_AUTHORITY"},
    ("APPROVED_WITH_CONDITIONS", "OBLIGATION_TRACKING"): {"COMPETENT_AUTHORITY"},
    ("APPROVED", "CLOSED"): {"BUREAU_SUPERVISOR", "REGIONAL_OFFICER"},
    ("OBLIGATION_TRACKING", "CLOSED"): {"BUREAU_SUPERVISOR", "REGIONAL_OFFICER"},
    ("REJECTED", "CLOSED"): {"BUREAU_SUPERVISOR", "REGIONAL_OFFICER"},
    ("ON_HOLD", "SCRUTINY"): {"BUREAU_SUPERVISOR", "REGIONAL_OFFICER", "LEAD_AUDITOR"},
    ("ON_HOLD", "INTAKE_REVIEW"): {"BUREAU_SUPERVISOR", "REGIONAL_OFFICER", "LEAD_AUDITOR"},
}

EVENT_ROLE_ALLOWLIST: dict[str, set[str]] = {
    "COMMITTEE_CONVENED": {"COMMITTEE_SECRETARIAT"},
    "COMMITTEE_MINUTES_RECORDED": {"COMMITTEE_SECRETARIAT"},
    "OFFICER_NOTE": {"INTAKE_OFFICER", "SCRUTINY_OFFICER", "REGIONAL_OFFICER", "BUREAU_SUPERVISOR", "AUDITOR", "LEAD_AUDITOR"},
}

EVENT_STAGE_ALLOWLIST: dict[str, set[str]] = {
    "COMMITTEE_CONVENED": {"COMMITTEE_PROCEEDINGS"},
    "COMMITTEE_MINUTES_RECORDED": {"COMMITTEE_PROCEEDINGS"},
}


def validate_operational_event(case: WorkflowCase, event_type: str) -> None:
    """Reject operational events recorded outside their applicable workflow stage."""
    permitted_stages = EVENT_STAGE_ALLOWLIST.get(event_type)
    if permitted_stages and case.current_stage not in permitted_stages:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"{event_type} can only be recorded during: {', '.join(sorted(permitted_stages))}.",
        )
    if event_type in {"COMMITTEE_CONVENED", "COMMITTEE_MINUTES_RECORDED"}:
        if (case.route_snapshot or {}).get("requires_committee") is not True:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Committee proceedings are not configured as applicable for this application's route.",
            )


def validate_evc_schedule_stage(case: WorkflowCase, existing_visit: EVCVisit | None = None) -> None:
    """Validate that the case route and current stage permit EVC scheduling or rescheduling."""
    if (case.route_snapshot or {}).get("requires_evc") is not True:
        raise HTTPException(status_code=409, detail="The approved application route does not require an EVC visit.")
    if case.current_stage not in {"EVC_COORDINATION", "EVC_SCHEDULED"}:
        raise HTTPException(status_code=409, detail="EVC scheduling is available only during EVC coordination or a scheduled visit.")
    if existing_visit is not None and existing_visit.status == "COMPLETED":
        raise HTTPException(status_code=409, detail="A completed EVC visit cannot be rescheduled.")


def validate_evc_report_stage(case: WorkflowCase, visit: EVCVisit | None) -> None:
    """Require a scheduled visit before its report may be recorded."""
    if case.current_stage != "EVC_SCHEDULED":
        raise HTTPException(status_code=409, detail="An EVC report can be recorded only while the case is at the scheduled EVC stage.")
    if visit is None or visit.status != "SCHEDULED":
        raise HTTPException(status_code=409, detail="A current scheduled EVC visit is required before recording its report.")


def schedule_evc_visit(
    db: Session,
    case: WorkflowCase,
    actor_user_id: uuid.UUID,
    *,
    visit_mode: str,
    scheduled_start_at: datetime,
    scheduled_end_at: datetime | None,
    venue_or_meeting_details: str,
    official_schedule_reference: str | None,
    institution_contact_name: str | None,
    institution_contact_email: str | None,
    coordination_note: str,
) -> EVCVisit:
    visit = db.scalar(
        select(EVCVisit)
        .where(EVCVisit.workflow_case_id == case.workflow_case_id)
        .with_for_update()
    )
    validate_evc_schedule_stage(case, visit)
    if scheduled_start_at <= datetime.now(UTC):
        raise HTTPException(status_code=422, detail="The EVC visit start must be in the future.")
    if scheduled_end_at is not None and scheduled_end_at <= scheduled_start_at:
        raise HTTPException(status_code=422, detail="The EVC visit end must be later than its start.")

    previous_status = visit.status if visit is not None else None
    previous_start = visit.scheduled_start_at.isoformat() if visit and visit.scheduled_start_at else None
    previous_end = visit.scheduled_end_at.isoformat() if visit and visit.scheduled_end_at else None
    if visit is None:
        visit = EVCVisit(
            workflow_case_id=case.workflow_case_id,
            application_id=case.application_id,
            created_by=actor_user_id,
            schedule_revision=0,
        )
        db.add(visit)
        db.flush()

    event_type = "EVC_VISIT_RESCHEDULED" if previous_status == "SCHEDULED" else "EVC_VISIT_SCHEDULED"
    visit.status = "SCHEDULED"
    visit.visit_mode = visit_mode
    visit.scheduled_start_at = scheduled_start_at
    visit.scheduled_end_at = scheduled_end_at
    visit.venue_or_meeting_details = venue_or_meeting_details.strip()
    visit.official_schedule_reference = official_schedule_reference.strip() if official_schedule_reference else None
    visit.institution_contact_name = institution_contact_name.strip() if institution_contact_name else None
    visit.institution_contact_email = institution_contact_email.strip().lower() if institution_contact_email else None
    visit.coordination_note = coordination_note.strip()
    visit.schedule_revision = (visit.schedule_revision or 0) + 1
    visit.cancellation_reason = None
    visit.updated_by = actor_user_id
    visit.updated_at = datetime.now(UTC)
    add_workflow_event(
        db,
        case,
        actor_user_id,
        event_type=event_type,
        summary=f"{'EVC visit rescheduled' if event_type == 'EVC_VISIT_RESCHEDULED' else 'EVC visit scheduled'} for {scheduled_start_at.isoformat()}. {coordination_note.strip()}",
        event_payload={
            "evc_visit_id": str(visit.evc_visit_id),
            "schedule_revision": visit.schedule_revision,
            "previous_status": previous_status,
            "previous_start_at": previous_start,
            "previous_end_at": previous_end,
            "scheduled_start_at": scheduled_start_at.isoformat(),
            "scheduled_end_at": scheduled_end_at.isoformat() if scheduled_end_at else None,
            "visit_mode": visit_mode,
            "venue_or_meeting_details": venue_or_meeting_details.strip(),
            "official_schedule_reference": visit.official_schedule_reference,
        },
    )
    return visit


def record_evc_visit_report(
    db: Session,
    case: WorkflowCase,
    visit: EVCVisit | None,
    actor_user_id: uuid.UUID,
    *,
    report_reference: str,
    report_summary: str,
    report_outcome: str,
    note: str,
) -> EVCVisit:
    validate_evc_report_stage(case, visit)
    assert visit is not None
    now = datetime.now(UTC)
    if visit.scheduled_start_at is not None and visit.scheduled_start_at > now:
        raise HTTPException(status_code=409, detail="The EVC visit report can be recorded once the scheduled visit has started.")
    visit.status = "COMPLETED"
    visit.report_reference = report_reference.strip()
    visit.report_summary = report_summary.strip()
    visit.report_outcome = report_outcome
    visit.report_recorded_by = actor_user_id
    visit.report_recorded_at = now
    visit.updated_by = actor_user_id
    visit.updated_at = now
    add_workflow_event(
        db,
        case,
        actor_user_id,
        event_type="EVC_REPORT_RECORDED",
        summary=f"EVC report {report_reference.strip()} recorded. {note.strip()}",
        event_payload={
            "evc_visit_id": str(visit.evc_visit_id),
            "report_reference": visit.report_reference,
            "report_outcome": report_outcome,
            "report_summary": visit.report_summary,
        },
    )
    return visit


def cancel_evc_visit(
    db: Session,
    case: WorkflowCase,
    visit: EVCVisit | None,
    actor_user_id: uuid.UUID,
    reason: str,
) -> EVCVisit:
    if case.current_stage not in {"EVC_COORDINATION", "EVC_SCHEDULED"}:
        raise HTTPException(status_code=409, detail="An EVC visit can be cancelled only during coordination or before its report is recorded.")
    if visit is None or visit.status != "SCHEDULED":
        raise HTTPException(status_code=409, detail="There is no active scheduled EVC visit to cancel.")
    now = datetime.now(UTC)
    visit.status = "CANCELLED"
    visit.cancellation_reason = reason.strip()
    visit.updated_by = actor_user_id
    visit.updated_at = now
    add_workflow_event(
        db,
        case,
        actor_user_id,
        event_type="EVC_VISIT_CANCELLED",
        summary=f"EVC visit cancelled. {reason.strip()}",
        event_payload={
            "evc_visit_id": str(visit.evc_visit_id),
            "schedule_revision": visit.schedule_revision,
            "previous_start_at": visit.scheduled_start_at.isoformat() if visit.scheduled_start_at else None,
            "reason": reason.strip(),
        },
    )
    return visit


def validate_ec_decision_stage(case: WorkflowCase, role_code: str) -> None:
    validate_ec_decision_stage(case, role_code)


def calculate_appeal_deadline(speaking_order_uploaded_at: datetime) -> datetime:
    if speaking_order_uploaded_at.tzinfo is None or speaking_order_uploaded_at.utcoffset() is None:
        raise HTTPException(status_code=422, detail="Speaking Order upload time must include a timezone.")
    return speaking_order_uploaded_at.astimezone(UTC) + timedelta(days=7)


def record_executive_committee_decision(
    db: Session,
    case: WorkflowCase,
    actor_user_id: uuid.UUID,
    role_code: str,
    *,
    outcome_code: str,
    decision_reference: str,
    decision_reasons: str,
    speaking_order_reference: str,
    speaking_order_uploaded_at: datetime,
) -> ExecutiveCommitteeDecision:
    """Persist the EC outcome, calculate its appeal window and move the case atomically."""
    if role_code != "COMPETENT_AUTHORITY":
        raise HTTPException(status_code=403, detail="Only the authorised Competent Authority may record the Executive Committee decision.")
    if case.current_stage != "AWAITING_AUTHORITY":
        raise HTTPException(status_code=409, detail="The case must be at Executive Committee decision before recording the outcome.")
    existing = db.scalar(
        select(ExecutiveCommitteeDecision)
        .where(ExecutiveCommitteeDecision.workflow_case_id == case.workflow_case_id)
        .with_for_update()
    )
    if existing is not None:
        raise HTTPException(status_code=409, detail="An Executive Committee decision is already recorded for this case.")
    uploaded_at = speaking_order_uploaded_at.astimezone(UTC)
    now = datetime.now(UTC)
    if uploaded_at > now:
        raise HTTPException(status_code=422, detail="Speaking Order upload time cannot be in the future.")
    if uploaded_at < case.stage_entered_at:
        raise HTTPException(status_code=422, detail="Speaking Order upload time cannot be earlier than the Executive Committee decision stage.")

    decision = ExecutiveCommitteeDecision(
        workflow_case_id=case.workflow_case_id,
        application_id=case.application_id,
        outcome_code=outcome_code,
        decision_reference=decision_reference.strip(),
        decision_reasons=decision_reasons.strip(),
        speaking_order_reference=speaking_order_reference.strip(),
        speaking_order_uploaded_at=uploaded_at,
        appeal_deadline_at=calculate_appeal_deadline(uploaded_at),
        recorded_by=actor_user_id,
    )
    db.add(decision)
    db.flush()
    add_workflow_event(
        db,
        case,
        actor_user_id,
        event_type="EXECUTIVE_COMMITTEE_DECISION_RECORDED",
        summary=f"Executive Committee decision {decision_reference.strip()} recorded as {outcome_code.replace('_', ' ')}.",
        event_payload={
            "decision_id": str(decision.executive_committee_decision_id),
            "outcome_code": outcome_code,
            "decision_reference": decision.decision_reference,
            "speaking_order_reference": decision.speaking_order_reference,
            "speaking_order_uploaded_at": uploaded_at.isoformat(),
            "appeal_deadline_at": decision.appeal_deadline_at.isoformat(),
            "decision_reasons": decision.decision_reasons,
        },
    )
    transition_case(
        db,
        case,
        actor_user_id,
        role_code,
        outcome_code,
        f"Executive Committee decision {decision_reference.strip()} recorded. {decision_reasons.strip()}",
    )
    return decision


def validate_shc_stage(case: WorkflowCase) -> None:
    """SHC proceedings are available only on a route-confirmed SHC stage."""
    if (case.route_snapshot or {}).get("requires_committee") is not True:
        raise HTTPException(status_code=409, detail="The approved application route does not include an SHC proceeding.")
    if case.current_stage != "COMMITTEE_PROCEEDINGS":
        raise HTTPException(status_code=409, detail="SHC actions are available only during the SHC proceeding stage.")


def validate_shc_hearing_record(case: WorkflowCase, proceeding: SHCProceeding | None) -> None:
    validate_shc_stage(case)
    if proceeding is None or proceeding.status != "SCHEDULED":
        raise HTTPException(status_code=409, detail="A scheduled SHC hearing is required before recording the hearing.")
    if proceeding.hearing_scheduled_at is not None and proceeding.hearing_scheduled_at > datetime.now(UTC):
        raise HTTPException(status_code=409, detail="The SHC hearing cannot be recorded before its scheduled date and time.")


def validate_shc_recommendation(case: WorkflowCase, proceeding: SHCProceeding | None) -> None:
    validate_shc_stage(case)
    if proceeding is None or proceeding.status != "HEARING_RECORDED":
        raise HTTPException(status_code=409, detail="Record the SHC hearing before recording its recommendation.")


def schedule_shc_hearing(
    db: Session,
    case: WorkflowCase,
    actor_user_id: uuid.UUID,
    *,
    hearing_mode: str,
    hearing_scheduled_at: datetime,
    hearing_details: str,
    notice_reference: str | None,
    official_schedule_reference: str | None,
) -> SHCProceeding:
    validate_shc_stage(case)
    proceeding = db.scalar(
        select(SHCProceeding)
        .where(SHCProceeding.workflow_case_id == case.workflow_case_id)
        .with_for_update()
    )
    if proceeding is not None and proceeding.status in {"HEARING_RECORDED", "RECOMMENDATION_RECORDED"}:
        raise HTTPException(status_code=409, detail="The SHC hearing has already been recorded and cannot be rescheduled.")
    if hearing_scheduled_at <= datetime.now(UTC):
        raise HTTPException(status_code=422, detail="The SHC hearing must be scheduled for a future date and time.")

    if proceeding is None:
        proceeding = SHCProceeding(
            workflow_case_id=case.workflow_case_id,
            application_id=case.application_id,
            created_by=actor_user_id,
            schedule_revision=0,
        )
        db.add(proceeding)
        db.flush()

    previous_at = proceeding.hearing_scheduled_at.isoformat() if proceeding.hearing_scheduled_at else None
    event_type = "SHC_HEARING_RESCHEDULED" if proceeding.status == "SCHEDULED" else "SHC_HEARING_SCHEDULED"
    proceeding.status = "SCHEDULED"
    proceeding.hearing_mode = hearing_mode
    proceeding.hearing_scheduled_at = hearing_scheduled_at
    proceeding.hearing_details = hearing_details.strip()
    proceeding.notice_reference = notice_reference.strip() if notice_reference else None
    proceeding.official_schedule_reference = official_schedule_reference.strip() if official_schedule_reference else None
    proceeding.schedule_revision = (proceeding.schedule_revision or 0) + 1
    proceeding.updated_by = actor_user_id
    proceeding.updated_at = datetime.now(UTC)
    add_workflow_event(
        db,
        case,
        actor_user_id,
        event_type=event_type,
        summary=f"SHC hearing {'rescheduled' if event_type == 'SHC_HEARING_RESCHEDULED' else 'scheduled'} for {hearing_scheduled_at.isoformat()}.",
        event_payload={
            "shc_proceeding_id": str(proceeding.shc_proceeding_id),
            "schedule_revision": proceeding.schedule_revision,
            "previous_hearing_at": previous_at,
            "hearing_scheduled_at": hearing_scheduled_at.isoformat(),
            "hearing_mode": hearing_mode,
            "notice_reference": proceeding.notice_reference,
            "official_schedule_reference": proceeding.official_schedule_reference,
        },
    )
    return proceeding


def submit_shc_compliance_reference(
    db: Session,
    case: WorkflowCase,
    proceeding: SHCProceeding | None,
    actor_user_id: uuid.UUID,
    *,
    submission_reference: str,
    note: str,
) -> SHCProceeding:
    validate_shc_stage(case)
    if proceeding is None or proceeding.status != "SCHEDULED":
        raise HTTPException(status_code=409, detail="An SHC hearing must be scheduled before compliance material can be submitted.")
    if proceeding.hearing_scheduled_at is not None and proceeding.hearing_scheduled_at <= datetime.now(UTC):
        raise HTTPException(status_code=409, detail="The scheduled hearing time has passed; the compliance submission window for this hearing is closed.")
    proceeding.institution_submission_reference = submission_reference.strip()
    proceeding.updated_by = actor_user_id
    proceeding.updated_at = datetime.now(UTC)
    add_workflow_event(
        db,
        case,
        actor_user_id,
        event_type="SHC_COMPLIANCE_SUBMISSION_RECORDED",
        summary=f"Institution compliance submission recorded. {note.strip()}",
        event_payload={
            "shc_proceeding_id": str(proceeding.shc_proceeding_id),
            "submission_reference": proceeding.institution_submission_reference,
        },
    )
    return proceeding


def record_shc_hearing(
    db: Session,
    case: WorkflowCase,
    proceeding: SHCProceeding | None,
    actor_user_id: uuid.UUID,
    *,
    representative_one_name: str,
    representative_one_designation: str,
    representative_two_name: str,
    representative_two_designation: str,
    hearing_summary: str,
    note: str,
) -> SHCProceeding:
    validate_shc_hearing_record(case, proceeding)
    assert proceeding is not None
    if representative_one_name.strip().casefold() == representative_two_name.strip().casefold():
        raise HTTPException(status_code=422, detail="Record the two institution representatives separately.")
    now = datetime.now(UTC)
    proceeding.status = "HEARING_RECORDED"
    proceeding.representative_one_name = representative_one_name.strip()
    proceeding.representative_one_designation = representative_one_designation.strip()
    proceeding.representative_two_name = representative_two_name.strip()
    proceeding.representative_two_designation = representative_two_designation.strip()
    proceeding.hearing_summary = hearing_summary.strip()
    proceeding.hearing_recorded_by = actor_user_id
    proceeding.hearing_recorded_at = now
    proceeding.updated_by = actor_user_id
    proceeding.updated_at = now
    add_workflow_event(
        db,
        case,
        actor_user_id,
        event_type="SHC_HEARING_RECORDED",
        summary=f"SHC hearing record entered. {note.strip()}",
        event_payload={
            "shc_proceeding_id": str(proceeding.shc_proceeding_id),
            "representatives": [
                {"name": proceeding.representative_one_name, "designation": proceeding.representative_one_designation},
                {"name": proceeding.representative_two_name, "designation": proceeding.representative_two_designation},
            ],
            "institution_submission_reference": proceeding.institution_submission_reference,
        },
    )
    return proceeding


def record_shc_recommendation(
    db: Session,
    case: WorkflowCase,
    proceeding: SHCProceeding | None,
    actor_user_id: uuid.UUID,
    *,
    recommendation_code: str,
    recommendation_text: str,
    recommendation_reference: str | None,
) -> SHCProceeding:
    validate_shc_recommendation(case, proceeding)
    assert proceeding is not None
    now = datetime.now(UTC)
    proceeding.status = "RECOMMENDATION_RECORDED"
    proceeding.recommendation_code = recommendation_code
    proceeding.recommendation_text = recommendation_text.strip()
    proceeding.recommendation_reference = recommendation_reference.strip() if recommendation_reference else None
    proceeding.recommendation_recorded_by = actor_user_id
    proceeding.recommendation_recorded_at = now
    proceeding.updated_by = actor_user_id
    proceeding.updated_at = now
    add_workflow_event(
        db,
        case,
        actor_user_id,
        event_type="SHC_RECOMMENDATION_RECORDED",
        summary="SHC recommendation recorded for Executive Committee consideration.",
        event_payload={
            "shc_proceeding_id": str(proceeding.shc_proceeding_id),
            "recommendation_code": recommendation_code,
            "recommendation_reference": proceeding.recommendation_reference,
            "recommendation_text": proceeding.recommendation_text,
        },
    )
    return proceeding


def route_profile_for(process_type: str) -> tuple[str, str, dict[str, Any]]:
    key = process_type.strip().upper()
    if key in ROUTE_PROFILES:
        profile = ROUTE_PROFILES[key]
        return profile["route_code"], profile["regulatory_version"], dict(profile)
    return (
        "ROUTE_PENDING_POLICY_CONFIRMATION",
        "APH_2024_2027_BASELINE",
        {
            "route_status": "MANUAL_CONFIRMATION_REQUIRED",
            "requires_scrutiny": None,
            "requires_evc": None,
            "requires_committee": None,
            "steps": [],
            "reason": "No approved category-specific route profile is configured for this process type.",
        },
    )


def create_workflow_case(
    db: Session,
    application: Application,
    actor_user_id: uuid.UUID,
    process_type: str = "EOA_SELF_DISCLOSURE",
) -> WorkflowCase:
    existing = db.scalar(
        select(WorkflowCase).where(WorkflowCase.application_id == application.application_id)
    )
    if existing:
        return existing

    route_code, regulatory_version, snapshot = route_profile_for(process_type)
    case = WorkflowCase(
        application_id=application.application_id,
        process_type=process_type,
        route_code=route_code,
        regulatory_version=regulatory_version,
        route_snapshot=snapshot,
        current_stage="DRAFT",
        created_by=actor_user_id,
    )
    db.add(case)
    db.flush()
    add_workflow_event(
        db,
        case,
        actor_user_id,
        event_type="APPLICATION_CREATED",
        summary="Application workflow created and category route snapshot recorded.",
        event_payload={"process_type": process_type, "route_code": route_code, "regulatory_version": regulatory_version},
    )
    return case


def add_workflow_event(
    db: Session,
    case: WorkflowCase,
    actor_user_id: uuid.UUID,
    *,
    event_type: str,
    summary: str,
    from_stage: str | None = None,
    to_stage: str | None = None,
    event_payload: dict[str, Any] | None = None,
) -> WorkflowEvent:
    event = WorkflowEvent(
        workflow_case_id=case.workflow_case_id,
        application_id=case.application_id,
        event_type=event_type,
        from_stage=from_stage,
        to_stage=to_stage,
        summary=summary,
        event_payload=event_payload or {},
        actor_user_id=actor_user_id,
    )
    db.add(event)
    db.flush()
    notify_case_participants(db, case, event, summary)
    return event


def notify_case_participants(
    db: Session,
    case: WorkflowCase,
    event: WorkflowEvent,
    message: str,
) -> None:
    application = db.get(Application, case.application_id)
    if application is None:
        return

    recipients: set[uuid.UUID] = set(
        db.scalars(
            select(InstitutionMembership.user_id).where(
                InstitutionMembership.institution_id == application.institution_id,
                InstitutionMembership.is_active.is_(True),
            )
        ).all()
    )
    if application.review_team_id:
        team_members_query = select(ReviewTeamMember.user_id).where(
            ReviewTeamMember.review_team_id == application.review_team_id,
            ReviewTeamMember.is_active.is_(True),
        )
        if case.assigned_user_id:
            # Once individually assigned, notify the assignee and supervisory members,
            # not every officer in the team.
            team_members_query = team_members_query.where(
                ReviewTeamMember.team_role.in_(["BUREAU_SUPERVISOR", "REGIONAL_OFFICER", "LEAD_AUDITOR"])
            )
        recipients.update(db.scalars(team_members_query).all())
    if case.assigned_user_id:
        recipients.add(case.assigned_user_id)

    for recipient in recipients:
        db.add(
            InAppNotification(
                recipient_user_id=recipient,
                application_id=application.application_id,
                workflow_event_id=event.workflow_event_id,
                event_key=f"workflow-event:{event.workflow_event_id}",
                title="Application workflow updated",
                body=message[:2000],
                severity="WARNING" if event.event_type in {"CLARIFICATION_REQUESTED", "OBLIGATION_DUE"} else "INFO",
            )
        )


def validate_transition(case: WorkflowCase, role_code: str, to_stage: str) -> None:
    current = case.current_stage
    allowed_roles = TRANSITION_ROLES.get((current, to_stage))
    if not allowed_roles or role_code not in allowed_roles:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Role {role_code} cannot move this case from {current} to {to_stage}.",
        )

    snapshot = case.route_snapshot or {}
    if to_stage == "SCRUTINY" and snapshot.get("requires_scrutiny") is False:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="This application category does not use the scrutiny stage in its configured route.")
    if to_stage == "INTAKE_REVIEW" and current == "ON_HOLD" and snapshot.get("requires_scrutiny") is True:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="This category must return to scrutiny, not intake review, after a supervisory hold.")
    if to_stage == "INTAKE_REVIEW" and current == "RESUBMITTED" and snapshot.get("requires_scrutiny") is True:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="This category returns to scrutiny after resubmission, not intake review.")
    if to_stage == "COMMITTEE_PROCEEDINGS" and snapshot.get("requires_committee") is not True:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="A committee stage is not part of the configured route for this category.")
    if to_stage == "AWAITING_AUTHORITY":
        if snapshot.get("route_status") == "MANUAL_CONFIRMATION_REQUIRED":
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="The category-specific route must be confirmed by the regulatory policy publisher before authority review.",
            )
        if snapshot.get("requires_evc") and current not in {"EVC_COMPLETED", "COMMITTEE_PROCEEDINGS"}:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="This category route requires the EVC stage to be completed before authority review.",
            )
        if snapshot.get("requires_committee") is None and snapshot.get("requires_evc"):
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Committee applicability for this category must be confirmed against the effective regulatory route before authority review.",
            )
        if snapshot.get("requires_committee") and current != "COMMITTEE_PROCEEDINGS":
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="This category route requires its configured committee proceedings before authority review.",
            )


def intake_review_assignee(route_snapshot: dict[str, Any] | None) -> str:
    """Resolve the receiving role after intake using the case's immutable route snapshot."""
    return (
        "SCRUTINY_OFFICER"
        if (route_snapshot or {}).get("requires_scrutiny") is True
        else "INTAKE_OFFICER"
    )


def evc_completion_assignee(route_snapshot: dict[str, Any] | None) -> str:
    """Route a completed EVC to SHC only when its applicability is confirmed."""
    return (
        "COMMITTEE_SECRETARIAT"
        if (route_snapshot or {}).get("requires_committee") is True
        else "REGIONAL_OFFICER"
    )


def transition_case(
    db: Session,
    case: WorkflowCase,
    actor_user_id: uuid.UUID,
    role_code: str,
    to_stage: str,
    reason: str,
    due_at: datetime | None = None,
) -> WorkflowCase:
    validate_transition(case, role_code, to_stage)
    application = db.get(Application, case.application_id)
    if to_stage == "RESUBMITTED" and application is not None and application.current_revision_id:
        revision = db.get(ApplicationRevision, application.current_revision_id)
        if revision is None or revision.status != RevisionStatus.DRAFT:
            raise HTTPException(status_code=409, detail="Save at least one clarification response to create a new application revision before resubmission.")
    from_stage = case.current_stage
    previous_assigned_role = case.assigned_role_code
    case.current_stage = to_stage
    case.stage_entered_at = datetime.now(UTC)
    case.due_at = due_at
    if to_stage == "SUBMITTED":
        case.assigned_role_code = "INTAKE_OFFICER"
    elif to_stage == "INTAKE_REVIEW":
        case.assigned_role_code = intake_review_assignee(case.route_snapshot)
    elif to_stage == "SCRUTINY":
        case.assigned_role_code = "SCRUTINY_OFFICER"
    elif to_stage == "EVC_COORDINATION":
        case.assigned_role_code = "EVC_COORDINATOR"
    elif to_stage == "EVC_SCHEDULED":
        case.assigned_role_code = "EVC_MEMBER"
    elif to_stage == "EVC_COMPLETED":
        case.assigned_role_code = evc_completion_assignee(case.route_snapshot)
    elif to_stage == "COMMITTEE_PROCEEDINGS":
        case.assigned_role_code = "COMMITTEE_SECRETARIAT"
    elif to_stage in {"AWAITING_AUTHORITY", "APPROVED", "APPROVED_WITH_CONDITIONS", "REJECTED", "ON_HOLD"}:
        case.assigned_role_code = "COMPETENT_AUTHORITY"
    elif to_stage == "OBLIGATION_TRACKING":
        case.assigned_role_code = "SCRUTINY_OFFICER"
    elif to_stage in {"CLOSED"}:
        case.assigned_role_code = None
    if case.assigned_role_code != previous_assigned_role:
        # A stage hand-off invalidates any individual assignment from the prior stage.
        # The receiving team/role can then assign its own participant explicitly.
        case.assigned_user_id = None

    application = application or db.get(Application, case.application_id)
    if application is not None:
        if to_stage in {"SUBMITTED", "RESUBMITTED"} and application.current_revision_id:
            revision = db.get(ApplicationRevision, application.current_revision_id)
            if revision is not None:
                revision.status = RevisionStatus.SUBMITTED
                revision.submitted_by = actor_user_id
                revision.submitted_at = datetime.now(UTC)
        status_by_stage = {
            "SUBMITTED": ApplicationStatus.SUBMITTED,
            "INTAKE_REVIEW": ApplicationStatus.SUBMITTED,
            "SCRUTINY": ApplicationStatus.UNDER_AUDITOR_REVIEW,
            "CLARIFICATION_REQUESTED": ApplicationStatus.RECTIFICATION_REQUESTED,
            "RESUBMITTED": ApplicationStatus.RESUBMITTED,
            "EVC_COORDINATION": ApplicationStatus.UNDER_AUDITOR_REVIEW,
            "EVC_SCHEDULED": ApplicationStatus.UNDER_AUDITOR_REVIEW,
            "EVC_COMPLETED": ApplicationStatus.UNDER_AUDITOR_REVIEW,
            "COMMITTEE_PROCEEDINGS": ApplicationStatus.UNDER_LEAD_REVIEW,
            "AWAITING_AUTHORITY": ApplicationStatus.AWAITING_AUTHORITY_DISPOSITION,
            "APPROVED": ApplicationStatus.APPROVED,
            "APPROVED_WITH_CONDITIONS": ApplicationStatus.APPROVED_WITH_CONDITIONS,
            "REJECTED": ApplicationStatus.REJECTED,
            "ON_HOLD": ApplicationStatus.ON_HOLD,
            "OBLIGATION_TRACKING": ApplicationStatus.APPROVED_WITH_CONDITIONS,
            "CLOSED": ApplicationStatus.CLOSED,
        }
        new_status = status_by_stage.get(to_stage)
        if new_status is not None and application.status != new_status:
            db.add(ApplicationStatusHistory(
                application_id=application.application_id,
                from_status=application.status,
                to_status=new_status,
                changed_by=actor_user_id,
                change_reason=reason.strip(),
            ))
            application.status = new_status
        if to_stage == "SUBMITTED":
            application.submitted_at = datetime.now(UTC)

    add_workflow_event(
        db,
        case,
        actor_user_id,
        event_type="STAGE_TRANSITION",
        summary=reason.strip(),
        from_stage=from_stage,
        to_stage=to_stage,
        event_payload={"role_code": role_code, "due_at": due_at.isoformat() if due_at else None},
    )
    return case


def case_access_context(
    db: Session,
    application: Application,
    role_contexts: list[Any],
    *,
    case: WorkflowCase | None = None,
    user_id: uuid.UUID | None = None,
) -> Any:
    """Return a scoped active permission package or deny case access.

    Institution users are restricted to their own institution. Operational users
    are restricted to their active review team. An explicitly assigned officer
    is the only non-supervisory user who may open that individually assigned case.
    """
    for context in role_contexts:
        if context.role_code == "INSTITUTION_USER" and context.institution_id == application.institution_id:
            return context
        in_team_scope = bool(context.review_team_id and context.review_team_id == application.review_team_id)
        unassigned_intake = context.role_code == "INTAKE_OFFICER" and application.review_team_id is None
        if in_team_scope or unassigned_intake:
            is_supervisor = context.role_code in {"BUREAU_SUPERVISOR", "REGIONAL_OFFICER", "LEAD_AUDITOR"}
            if case and case.assigned_user_id and user_id and case.assigned_user_id != user_id and not is_supervisor:
                continue
            return context
    raise HTTPException(
        status_code=status.HTTP_403_FORBIDDEN,
        detail="This case is outside the user's authorised institution, review-team or individual assignment scope.",
    )


def create_obligation(
    db: Session,
    case: WorkflowCase,
    actor_user_id: uuid.UUID,
    *,
    title: str,
    description: str,
    source_condition: str,
    due_at: datetime,
    condition_code: str | None = None,
) -> ComplianceObligation:
    if case.current_stage not in {"APPROVED_WITH_CONDITIONS", "OBLIGATION_TRACKING"}:
        raise HTTPException(status_code=409, detail="Conditions can be entered only after an approved-with-conditions outcome.")
    obligation = ComplianceObligation(
        workflow_case_id=case.workflow_case_id,
        application_id=case.application_id,
        condition_code=condition_code,
        title=title.strip(),
        description=description.strip(),
        source_condition=source_condition.strip(),
        due_at=due_at,
        created_by=actor_user_id,
    )
    db.add(obligation)
    db.flush()
    add_workflow_event(
        db,
        case,
        actor_user_id,
        event_type="OBLIGATION_CREATED",
        summary=f"Condition recorded: {title.strip()}",
        event_payload={"obligation_id": str(obligation.obligation_id), "due_at": due_at.isoformat()},
    )
    return obligation


def list_case_obligations(db: Session, case_id: uuid.UUID) -> list[ComplianceObligation]:
    return list(
        db.scalars(
            select(ComplianceObligation)
            .where(ComplianceObligation.workflow_case_id == case_id)
            .order_by(ComplianceObligation.due_at.asc())
        ).all()
    )

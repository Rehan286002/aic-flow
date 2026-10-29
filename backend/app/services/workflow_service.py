"""Approval workflow services for PS 26262.

The route snapshot is stored on every case so later policy edits do not silently
rewrite an in-flight application's route. Only the role package permitted for a
transition may move the case to its next stage.
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
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
    "EVC_VISIT_SCHEDULED": {"EVC_COORDINATOR", "REGIONAL_OFFICER", "LEAD_AUDITOR"},
    "EVC_REPORT_RECORDED": {"EVC_COORDINATOR", "EVC_MEMBER"},
    "COMMITTEE_CONVENED": {"COMMITTEE_SECRETARIAT"},
    "COMMITTEE_MINUTES_RECORDED": {"COMMITTEE_SECRETARIAT"},
    "OFFICER_NOTE": {"INTAKE_OFFICER", "SCRUTINY_OFFICER", "REGIONAL_OFFICER", "BUREAU_SUPERVISOR", "AUDITOR", "LEAD_AUDITOR"},
}

EVENT_STAGE_ALLOWLIST: dict[str, set[str]] = {
    "EVC_VISIT_SCHEDULED": {"EVC_COORDINATION"},
    "EVC_REPORT_RECORDED": {"EVC_SCHEDULED"},
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
        case.assigned_role_code = "SCRUTINY_OFFICER"
    elif to_stage == "EVC_COORDINATION":
        case.assigned_role_code = "EVC_COORDINATOR"
    elif to_stage == "EVC_SCHEDULED":
        case.assigned_role_code = "EVC_MEMBER"
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

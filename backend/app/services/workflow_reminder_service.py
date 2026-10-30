from collections.abc import Iterable
from datetime import UTC, datetime, timedelta
from typing import Any
from zoneinfo import ZoneInfo

from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.orm import Session

from app.models.application import Application
from app.models.compliance_obligation import ComplianceObligation
from app.models.enums import TeamRole
from app.models.in_app_notification import InAppNotification
from app.models.institution_membership import InstitutionMembership
from app.models.review_team_member import ReviewTeamMember
from app.models.workflow_case import WorkflowCase
from app.models.workflow_reminder import WorkflowReminderDispatch, WorkflowReminderPolicy

INDIA_TIMEZONE = ZoneInfo("Asia/Kolkata")
TERMINAL_CASE_STAGES = {
    "APPROVED",
    "APPROVED_WITH_CONDITIONS",
    "REJECTED",
    "CLOSED",
    "ON_HOLD",
}
OPEN_OBLIGATION_STATES = {"OPEN", "RETURNED"}
ACTIVE_OBLIGATION_STATES = {"OPEN", "RETURNED", "EVIDENCE_SUBMITTED", "UNDER_VERIFICATION"}
SUPERVISOR_TEAM_ROLES = (
    TeamRole.BUREAU_SUPERVISOR,
    TeamRole.REGIONAL_OFFICER,
    TeamRole.LEAD_AUDITOR,
)


def reminder_trigger_at(due_at: datetime, days_from_due: int) -> datetime:
    """Return the configured reminder time relative to the target due date."""
    if due_at.tzinfo is None or due_at.utcoffset() is None:
        raise ValueError("Reminder due dates must include a timezone.")
    return due_at + timedelta(days=days_from_due)


def reminder_is_due(due_at: datetime, days_from_due: int, now: datetime) -> bool:
    if now.tzinfo is None or now.utcoffset() is None:
        raise ValueError("Reminder cycle time must include a timezone.")
    return now >= reminder_trigger_at(due_at, days_from_due)


def render_reminder_template(template: str, values: dict[str, str]) -> str:
    """Format only the approved reminder placeholders; invalid templates remain readable."""
    try:
        return template.format_map(values)[:2000]
    except (KeyError, ValueError):
        return template[:2000]


def _recipient_ids(
    db: Session,
    policy: WorkflowReminderPolicy,
    case: WorkflowCase,
    application: Application,
) -> set[Any]:
    if policy.recipient_group == "INSTITUTION":
        return set(
            db.scalars(
                select(InstitutionMembership.user_id).where(
                    InstitutionMembership.institution_id == application.institution_id,
                    InstitutionMembership.is_active.is_(True),
                )
            ).all()
        )

    if policy.recipient_group == "ASSIGNEE":
        if case.assigned_user_id:
            return {case.assigned_user_id}
        if not application.review_team_id or not case.assigned_role_code:
            return set()
        try:
            team_role = TeamRole(case.assigned_role_code)
        except ValueError:
            return set()
        return set(
            db.scalars(
                select(ReviewTeamMember.user_id).where(
                    ReviewTeamMember.review_team_id == application.review_team_id,
                    ReviewTeamMember.team_role == team_role,
                    ReviewTeamMember.is_active.is_(True),
                )
            ).all()
        )

    if policy.recipient_group == "SUPERVISORS":
        if not application.review_team_id:
            return set()
        return set(
            db.scalars(
                select(ReviewTeamMember.user_id).where(
                    ReviewTeamMember.review_team_id == application.review_team_id,
                    ReviewTeamMember.team_role.in_(SUPERVISOR_TEAM_ROLES),
                    ReviewTeamMember.is_active.is_(True),
                )
            ).all()
        )

    return set()


def _target_is_active(policy: WorkflowReminderPolicy, target: WorkflowCase | ComplianceObligation) -> bool:
    if policy.target_type == "WORKFLOW_CASE":
        return (
            isinstance(target, WorkflowCase)
            and target.current_stage not in TERMINAL_CASE_STAGES
            and target.due_at is not None
        )
    if policy.target_type == "OBLIGATION":
        if not isinstance(target, ComplianceObligation):
            return False
        if policy.recipient_group == "INSTITUTION":
            return target.status in OPEN_OBLIGATION_STATES
        return target.status in ACTIVE_OBLIGATION_STATES
    return False


def _target_due_at(target: WorkflowCase | ComplianceObligation) -> datetime | None:
    return target.due_at


def _notification_values(
    policy: WorkflowReminderPolicy,
    target_type: str,
    target_id: Any,
    recipient_id: Any,
    application: Application,
    due_at: datetime,
    target_title: str,
) -> dict[str, Any]:
    local_due = due_at.astimezone(INDIA_TIMEZONE)
    placeholders = {
        "application_number": application.application_number,
        "condition_title": target_title,
        "due_date": local_due.strftime("%d %b %Y, %I:%M %p IST"),
    }
    return {
        "recipient_user_id": recipient_id,
        "application_id": application.application_id,
        "workflow_event_id": None,
        "event_key": f"deadline-reminder:{policy.policy_code}:{target_type}:{target_id}",
        "title": render_reminder_template(policy.title_template, placeholders),
        "body": render_reminder_template(policy.body_template, placeholders),
        "severity": policy.severity,
    }


def _dispatch_target(
    db: Session,
    policy: WorkflowReminderPolicy,
    target_type: str,
    target: WorkflowCase | ComplianceObligation,
    case: WorkflowCase,
    application: Application,
    due_at: datetime,
    now: datetime,
) -> tuple[int, bool]:
    trigger_at = reminder_trigger_at(due_at, policy.days_from_due)
    if now < trigger_at or not _target_is_active(policy, target):
        return 0, False

    recipient_ids = _recipient_ids(db, policy, case, application)
    if not recipient_ids:
        return 0, False

    target_id = target.workflow_case_id if target_type == "WORKFLOW_CASE" else target.obligation_id
    dispatch_key = f"{policy.policy_code}:{target_type}:{target_id}"
    dispatch_values: dict[str, Any] = {
        "reminder_policy_id": policy.reminder_policy_id,
        "target_type": target_type,
        "workflow_case_id": case.workflow_case_id if target_type == "WORKFLOW_CASE" else None,
        "obligation_id": target.obligation_id if target_type == "OBLIGATION" else None,
        "dispatch_key": dispatch_key,
        "scheduled_for": trigger_at,
        "dispatched_at": now,
        "recipient_count": len(recipient_ids),
    }
    dispatch_stmt = (
        pg_insert(WorkflowReminderDispatch)
        .values(**dispatch_values)
        .on_conflict_do_nothing(index_elements=[WorkflowReminderDispatch.dispatch_key])
        .returning(WorkflowReminderDispatch.reminder_dispatch_id)
    )
    dispatch_id = db.scalar(dispatch_stmt)
    if dispatch_id is None:
        return 0, False

    target_title = target.title if isinstance(target, ComplianceObligation) else "Application processing"
    notification_rows = [
        _notification_values(policy, target_type, target_id, recipient_id, application, due_at, target_title)
        for recipient_id in sorted(recipient_ids, key=str)
    ]
    notification_stmt = (
        pg_insert(InAppNotification)
        .values(notification_rows)
        .on_conflict_do_nothing(
            index_elements=[
                InAppNotification.recipient_user_id,
                InAppNotification.event_key,
            ]
        )
    )
    result = db.execute(notification_stmt)
    return max(result.rowcount or 0, 0), True


def run_due_reminder_cycle(db: Session, now: datetime | None = None) -> dict[str, int]:
    """Create one durable dispatch per due policy/target and idempotent in-app alerts."""
    cycle_time = now or datetime.now(UTC)
    if cycle_time.tzinfo is None or cycle_time.utcoffset() is None:
        raise ValueError("Reminder cycle time must include a timezone.")

    policies = db.scalars(
        select(WorkflowReminderPolicy)
        .where(WorkflowReminderPolicy.is_enabled.is_(True))
        .order_by(WorkflowReminderPolicy.target_type, WorkflowReminderPolicy.days_from_due)
    ).all()

    active_cases = db.execute(
        select(WorkflowCase, Application)
        .join(Application, Application.application_id == WorkflowCase.application_id)
        .where(
            WorkflowCase.due_at.is_not(None),
            WorkflowCase.current_stage.not_in(TERMINAL_CASE_STAGES),
        )
    ).all()
    active_obligations = db.execute(
        select(ComplianceObligation, WorkflowCase, Application)
        .join(WorkflowCase, WorkflowCase.workflow_case_id == ComplianceObligation.workflow_case_id)
        .join(Application, Application.application_id == ComplianceObligation.application_id)
        .where(ComplianceObligation.status.in_(tuple(ACTIVE_OBLIGATION_STATES)))
    ).all()

    dispatches_created = 0
    notifications_created = 0
    for policy in policies:
        if policy.target_type == "WORKFLOW_CASE":
            for case, application in active_cases:
                if case.due_at is None:
                    continue
                created, dispatched = _dispatch_target(
                    db, policy, "WORKFLOW_CASE", case, case, application, case.due_at, cycle_time
                )
                notifications_created += created
                dispatches_created += int(dispatched)
        elif policy.target_type == "OBLIGATION":
            for obligation, case, application in active_obligations:
                created, dispatched = _dispatch_target(
                    db, policy, "OBLIGATION", obligation, case, application, obligation.due_at, cycle_time
                )
                notifications_created += created
                dispatches_created += int(dispatched)

    db.commit()
    return {
        "policies_checked": len(policies),
        "cases_checked": len(active_cases),
        "obligations_checked": len(active_obligations),
        "dispatches_created": dispatches_created,
        "notifications_created": notifications_created,
    }

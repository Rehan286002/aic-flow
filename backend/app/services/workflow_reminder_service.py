from datetime import UTC, date, datetime, time, timedelta
from typing import Any
from zoneinfo import ZoneInfo

from sqlalchemy import or_, select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.orm import Session

from app.models.application import Application
from app.models.compliance_obligation import ComplianceObligation
from app.models.enums import TeamRole
from app.models.in_app_notification import InAppNotification
from app.models.institution_membership import InstitutionMembership
from app.models.review_team_member import ReviewTeamMember
from app.models.workflow_case import WorkflowCase
from app.models.document_validity import DocumentValidityRecord
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


def reminder_trigger_at(due_at: datetime | date, days_from_due: int) -> datetime:
    """Return a timezone-aware trigger for datetime deadlines or India-local document expiry dates."""
    if isinstance(due_at, datetime):
        if due_at.tzinfo is None or due_at.utcoffset() is None:
            raise ValueError("Reminder due dates must include a timezone.")
        base = due_at
    elif isinstance(due_at, date):
        base = datetime.combine(due_at, time.min, tzinfo=INDIA_TIMEZONE)
    else:
        raise ValueError("Reminder due dates must be date or datetime values.")
    return base + timedelta(days=days_from_due)


def reminder_is_due(due_at: datetime | date, days_from_due: int, now: datetime) -> bool:
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


def _target_is_active(policy: WorkflowReminderPolicy, target: WorkflowCase | ComplianceObligation | DocumentValidityRecord) -> bool:
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
    if policy.target_type == "DOCUMENT_VALIDITY":
        return (
            isinstance(target, DocumentValidityRecord)
            and target.status == "VERIFIED"
            and (target.valid_until is not None or target.review_due_at is not None)
        )
    return False


def _target_due_at(target: WorkflowCase | ComplianceObligation | DocumentValidityRecord) -> datetime | date | None:
    if isinstance(target, DocumentValidityRecord):
        return target.valid_until or target.review_due_at
    return target.due_at


def _notification_values(
    policy: WorkflowReminderPolicy,
    target_type: str,
    target_id: Any,
    recipient_id: Any,
    application: Application,
    due_at: datetime | date,
    target_title: str,
) -> dict[str, Any]:
    local_due = due_at.astimezone(INDIA_TIMEZONE) if isinstance(due_at, datetime) else due_at
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
        "title": render_reminder_template(policy.title_template, placeholders)[:180],
        "body": render_reminder_template(policy.body_template, placeholders),
        "severity": policy.severity,
    }


def _dispatch_target(
    db: Session,
    policy: WorkflowReminderPolicy,
    target_type: str,
    target: WorkflowCase | ComplianceObligation | DocumentValidityRecord,
    case: WorkflowCase,
    application: Application,
    due_at: datetime | date,
    now: datetime,
) -> tuple[int, bool]:
    trigger_at = reminder_trigger_at(due_at, policy.days_from_due)
    if now < trigger_at or not _target_is_active(policy, target):
        return 0, False

    recipient_ids = _recipient_ids(db, policy, case, application)
    if not recipient_ids:
        return 0, False

    if target_type == "WORKFLOW_CASE":
        target_id = target.workflow_case_id
    elif target_type == "OBLIGATION":
        target_id = target.obligation_id
    else:
        target_id = target.document_validity_record_id
    dispatch_key = f"{policy.policy_code}:{target_type}:{target_id}"
    dispatch_values: dict[str, Any] = {
        "reminder_policy_id": policy.reminder_policy_id,
        "target_type": target_type,
        "workflow_case_id": case.workflow_case_id if target_type == "WORKFLOW_CASE" else None,
        "obligation_id": target.obligation_id if target_type == "OBLIGATION" else None,
        "document_validity_record_id": target.document_validity_record_id if target_type == "DOCUMENT_VALIDITY" else None,
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

    if isinstance(target, ComplianceObligation):
        target_title = target.title
    elif isinstance(target, DocumentValidityRecord):
        target_title = (
            "Structural Stability Certificate review trigger"
            if target.validity_type == "BUILDING_COMPLETION_CERTIFICATE"
            else target.validity_type.replace("_", " ").title()
        )
    else:
        target_title = "Application processing"
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
    active_validity_records = db.execute(
        select(DocumentValidityRecord, WorkflowCase, Application)
        .join(WorkflowCase, WorkflowCase.workflow_case_id == DocumentValidityRecord.workflow_case_id)
        .join(Application, Application.application_id == DocumentValidityRecord.application_id)
        .where(
            DocumentValidityRecord.status == "VERIFIED",
            or_(
                DocumentValidityRecord.valid_until.is_not(None),
                DocumentValidityRecord.review_due_at.is_not(None),
            ),
        )
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
        elif policy.target_type == "DOCUMENT_VALIDITY":
            for validity_record, case, application in active_validity_records:
                due_date = _target_due_at(validity_record)
                if due_date is None:
                    continue
                created, dispatched = _dispatch_target(
                    db, policy, "DOCUMENT_VALIDITY", validity_record, case, application, due_date, cycle_time
                )
                notifications_created += created
                dispatches_created += int(dispatched)

    db.commit()
    return {
        "policies_checked": len(policies),
        "cases_checked": len(active_cases),
        "obligations_checked": len(active_obligations),
        "document_validity_records_checked": len(active_validity_records),
        "dispatches_created": dispatches_created,
        "notifications_created": notifications_created,
    }

from datetime import UTC, date, datetime, timedelta

import pytest
from pydantic import ValidationError

from app.core.celery_app import celery_app
from app.schemas.workflow import WorkflowReminderPolicyUpdateRequest
from app.services.workflow_reminder_service import (
    reminder_is_due,
    reminder_trigger_at,
    render_reminder_template,
)


def test_reminder_offsets_are_calculated_from_the_due_timestamp():
    due_at = datetime(2026, 11, 20, 12, 0, tzinfo=UTC)
    assert reminder_trigger_at(due_at, -7) == due_at - timedelta(days=7)
    assert reminder_trigger_at(due_at, 0) == due_at
    assert reminder_trigger_at(due_at, 3) == due_at + timedelta(days=3)


def test_reminder_cycle_only_fires_after_the_configured_offset():
    due_at = datetime(2026, 11, 20, 12, 0, tzinfo=UTC)
    assert not reminder_is_due(due_at, -1, due_at - timedelta(days=1, seconds=1))
    assert reminder_is_due(due_at, -1, due_at - timedelta(days=1))
    assert reminder_is_due(due_at, 3, due_at + timedelta(days=3))


def test_reminder_schedule_requires_timezone_aware_dates():
    with pytest.raises(ValueError):
        reminder_trigger_at(datetime(2026, 11, 20, 12, 0), -1)
    with pytest.raises(ValueError):
        reminder_is_due(
            datetime(2026, 11, 20, 12, 0, tzinfo=UTC),
            -1,
            datetime(2026, 11, 19, 12, 0),
        )


def test_reminder_templates_fill_configured_placeholders():
    result = render_reminder_template(
        "{condition_title} for {application_number} is due on {due_date}.",
        {
            "condition_title": "Lease renewal",
            "application_number": "APP-2026-0012",
            "due_date": "20 Nov 2026, 05:30 PM IST",
        },
    )
    assert result == "Lease renewal for APP-2026-0012 is due on 20 Nov 2026, 05:30 PM IST."


def test_invalid_reminder_template_falls_back_without_crashing_worker():
    assert render_reminder_template("Due {unknown_field}", {}) == "Due {unknown_field}"


def test_policy_update_requires_a_change_and_bounds_offsets():
    with pytest.raises(ValidationError):
        WorkflowReminderPolicyUpdateRequest()
    with pytest.raises(ValidationError):
        WorkflowReminderPolicyUpdateRequest(days_from_due=400)

    update = WorkflowReminderPolicyUpdateRequest(
        is_enabled=False,
        days_from_due=2,
        recipient_group="SUPERVISORS",
        severity="CRITICAL",
    )
    assert update.days_from_due == 2
    assert update.recipient_group == "SUPERVISORS"


def test_celery_beat_runs_the_deadline_reminder_cycle_every_fifteen_minutes():
    schedule = celery_app.conf.beat_schedule["dispatch-workflow-deadline-reminders"]
    assert schedule["task"] == "app.tasks.workflow_reminders.dispatch_due_notifications"
    assert schedule["schedule"] == 900.0



def test_document_validity_reminder_dates_use_midnight_india_time():
    from zoneinfo import ZoneInfo

    due_date = date(2026, 12, 31)
    trigger = reminder_trigger_at(due_date, -90)
    assert trigger.tzinfo == ZoneInfo("Asia/Kolkata")
    assert trigger.date() == date(2026, 10, 2)
    assert reminder_is_due(due_date, -90, trigger)

from datetime import UTC, datetime, timedelta

import pytest
from pydantic import ValidationError

from app.schemas.workflow import EVCVisitReportRequest, EVCVisitScheduleRequest


def test_evc_schedule_requires_timezone_aware_visit_times():
    with pytest.raises(ValidationError):
        EVCVisitScheduleRequest(
            visit_mode="ONLINE",
            scheduled_start_at=datetime(2026, 11, 15, 10, 0),
            venue_or_meeting_details="Official online meeting instructions",
            coordination_note="Schedule communicated to the institution.",
        )


def test_evc_schedule_end_must_follow_start():
    start = datetime(2026, 11, 15, 10, 0, tzinfo=UTC)
    with pytest.raises(ValidationError):
        EVCVisitScheduleRequest(
            visit_mode="OFFLINE",
            scheduled_start_at=start,
            scheduled_end_at=start - timedelta(minutes=30),
            venue_or_meeting_details="AICTE notified institution campus venue",
            coordination_note="Schedule communicated to the institution.",
        )


def test_evc_schedule_rejects_whitespace_only_required_fields():
    with pytest.raises(ValidationError):
        EVCVisitScheduleRequest(
            visit_mode="ONLINE",
            scheduled_start_at=datetime(2026, 11, 15, 10, 0, tzinfo=UTC),
            venue_or_meeting_details="     ",
            coordination_note="       ",
        )


def test_evc_report_accepts_observation_outcome_and_rejects_blank_content():
    valid = EVCVisitReportRequest(
        report_reference="EVC-RPT-2026-018",
        report_summary="The visit observations and supporting records are summarised in this report.",
        report_outcome="DEFICIENCIES_OBSERVED",
        note="Report reference checked and recorded.",
    )
    assert valid.report_outcome == "DEFICIENCIES_OBSERVED"

    with pytest.raises(ValidationError):
        EVCVisitReportRequest(
            report_reference="   ",
            report_summary="          ",
            report_outcome="COMPLIANT",
            note="         ",
        )

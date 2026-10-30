from datetime import UTC, datetime

import pytest
from pydantic import ValidationError

from app.schemas.workflow import (
    SHCComplianceSubmissionRequest,
    SHCHearingRecordRequest,
    SHCHearingScheduleRequest,
    SHCRecommendationRequest,
)


def test_shc_hearing_schedule_requires_timezone_aware_datetime():
    with pytest.raises(ValidationError):
        SHCHearingScheduleRequest(
            hearing_mode="ONLINE",
            hearing_scheduled_at=datetime(2026, 11, 30, 11, 0),
            hearing_details="Online hearing access details and joining instructions",
        )


def test_shc_hearing_schedule_accepts_timezone_aware_datetime():
    value = SHCHearingScheduleRequest(
        hearing_mode="IN_PERSON",
        hearing_scheduled_at=datetime(2026, 11, 30, 11, 0, tzinfo=UTC),
        hearing_details="Hearing venue and reporting instructions",
    )
    assert value.hearing_mode == "IN_PERSON"


def test_shc_submission_requires_reference_and_note():
    with pytest.raises(ValidationError):
        SHCComplianceSubmissionRequest(submission_reference="   ", note="        ")


def test_shc_hearing_record_requires_two_representatives_and_summary():
    with pytest.raises(ValidationError):
        SHCHearingRecordRequest(
            representative_one_name="A",
            representative_one_designation="B",
            representative_two_name="",
            representative_two_designation="",
            hearing_summary="Too short",
            note="Also short",
        )


def test_shc_recommendation_requires_reasoned_text():
    with pytest.raises(ValidationError):
        SHCRecommendationRequest(
            recommendation_code="INCONCLUSIVE",
            recommendation_text="   ",
        )

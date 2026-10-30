from datetime import UTC, datetime

import pytest
from pydantic import ValidationError

from app.schemas.workflow import (
    CouncilDecisionRequest,
    SACAppealFileRequest,
    SACHearingRecordRequest,
    SACHearingScheduleRequest,
)


def test_sac_appeal_requires_grounds_and_supporting_material_reference():
    with pytest.raises(ValidationError):
        SACAppealFileRequest(
            appeal_grounds="Too short",
            supporting_material_reference="  ",
        )


def test_sac_hearing_schedule_requires_timezone_aware_datetime():
    with pytest.raises(ValidationError):
        SACHearingScheduleRequest(
            hearing_mode="ONLINE",
            hearing_scheduled_at=datetime(2026, 11, 20, 11, 0),
            hearing_details="Online SAC hearing details and joining instructions",
        )


def test_sac_hearing_requires_two_self_attested_representative_id_references():
    with pytest.raises(ValidationError):
        SACHearingRecordRequest(
            representative_one_name="Applicant Representative One",
            representative_one_designation="Trust Secretary",
            representative_one_id_reference="ID-PROOF-1",
            representative_one_id_self_attested=False,
            representative_two_name="Applicant Representative Two",
            representative_two_designation="Institution Principal",
            representative_two_id_reference="ID-PROOF-2",
            representative_two_id_self_attested=True,
            hearing_summary="Both representatives presented the appeal and supporting compliance material.",
        )


def test_council_decision_requires_timezone_aware_upload_time():
    with pytest.raises(ValidationError):
        CouncilDecisionRequest(
            outcome_code="UPHOLD_EXECUTIVE_COMMITTEE",
            decision_reference="COUNCIL/2026/18",
            decision_text="The Council decision and reasons are recorded for portal publication.",
            decision_uploaded_at=datetime(2026, 11, 25, 12, 0),
        )

    valid = CouncilDecisionRequest(
        outcome_code="REMAND_FOR_RECONSIDERATION",
        decision_reference="COUNCIL/2026/19",
        decision_text="The matter is remanded for reconsideration in accordance with the Council's directions.",
        decision_uploaded_at=datetime(2026, 11, 25, 12, 0, tzinfo=UTC),
    )
    assert valid.outcome_code == "REMAND_FOR_RECONSIDERATION"

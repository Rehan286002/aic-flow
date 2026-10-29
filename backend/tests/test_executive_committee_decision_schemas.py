from datetime import UTC, datetime

import pytest
from pydantic import ValidationError

from app.schemas.workflow import ExecutiveCommitteeDecisionRequest


def test_executive_committee_decision_requires_timezone_aware_speaking_order_upload_time():
    with pytest.raises(ValidationError):
        ExecutiveCommitteeDecisionRequest(
            outcome_code="APPROVED",
            decision_reference="EC/2026/104",
            decision_reasons="The application was considered against the applicable requirements.",
            speaking_order_reference="SO/2026/104",
            speaking_order_uploaded_at=datetime(2026, 10, 30, 12, 0),
        )


def test_executive_committee_decision_accepts_complete_speaking_order_record():
    value = ExecutiveCommitteeDecisionRequest(
        outcome_code="APPROVED_WITH_CONDITIONS",
        decision_reference="EC/2026/105",
        decision_reasons="Approval is granted subject to the conditions recorded in the accompanying order.",
        speaking_order_reference="SO/2026/105",
        speaking_order_uploaded_at=datetime(2026, 10, 30, 12, 0, tzinfo=UTC),
    )
    assert value.outcome_code == "APPROVED_WITH_CONDITIONS"


def test_executive_committee_decision_rejects_blank_references_and_reasons():
    with pytest.raises(ValidationError):
        ExecutiveCommitteeDecisionRequest(
            outcome_code="REJECTED",
            decision_reference="   ",
            decision_reasons="               ",
            speaking_order_reference="  ",
            speaking_order_uploaded_at=datetime(2026, 10, 30, 12, 0, tzinfo=UTC),
        )

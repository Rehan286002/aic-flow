from datetime import UTC, datetime, timedelta
from types import SimpleNamespace

import pytest
from fastapi import HTTPException

from app.services.workflow_service import validate_sac_appeal_filing


def test_sac_appeal_must_be_filed_within_seven_day_window():
    uploaded = datetime(2026, 10, 30, 10, 0, tzinfo=UTC)
    decision = SimpleNamespace(
        speaking_order_uploaded_at=uploaded,
        appeal_deadline_at=uploaded + timedelta(days=7),
    )
    validate_sac_appeal_filing(decision, None, uploaded + timedelta(days=3))
    validate_sac_appeal_filing(decision, None, uploaded + timedelta(days=7))

    with pytest.raises(HTTPException) as exc:
        validate_sac_appeal_filing(decision, None, uploaded + timedelta(days=7, seconds=1))
    assert exc.value.status_code == 409


def test_sac_appeal_cannot_precede_speaking_order_upload():
    uploaded = datetime(2026, 10, 30, 10, 0, tzinfo=UTC)
    decision = SimpleNamespace(
        speaking_order_uploaded_at=uploaded,
        appeal_deadline_at=uploaded + timedelta(days=7),
    )
    with pytest.raises(HTTPException) as exc:
        validate_sac_appeal_filing(decision, None, uploaded - timedelta(seconds=1))
    assert exc.value.status_code == 409


def test_sac_appeal_is_limited_to_one_filing_per_executive_decision():
    uploaded = datetime(2026, 10, 30, 10, 0, tzinfo=UTC)
    decision = SimpleNamespace(
        speaking_order_uploaded_at=uploaded,
        appeal_deadline_at=uploaded + timedelta(days=7),
    )
    existing = SimpleNamespace(sac_appeal_id="already-filed")
    with pytest.raises(HTTPException) as exc:
        validate_sac_appeal_filing(decision, existing, uploaded + timedelta(days=1))
    assert exc.value.status_code == 409


def test_sac_appeal_requires_an_executive_committee_decision():
    with pytest.raises(HTTPException) as exc:
        validate_sac_appeal_filing(None, None, datetime.now(UTC))
    assert exc.value.status_code == 409

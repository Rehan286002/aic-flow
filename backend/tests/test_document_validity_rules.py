from datetime import date, datetime, UTC

import pytest
from fastapi import HTTPException

from app.services.document_validity_service import (
    add_calendar_years,
    calculate_document_validity,
)


def test_structural_stability_certificate_validity_is_five_calendar_years():
    result = calculate_document_validity(
        validity_type="STRUCTURAL_STABILITY_CERTIFICATE",
        issue_date=date(2024, 2, 29),
        valid_from=None,
        valid_until=None,
        lease_start_date=None,
        lease_end_date=None,
        maximum_course_duration_years=None,
        application_submitted_at=None,
        validity_basis_reference="AICTE APH 2024-27 Clause 6.17(h)",
    )
    assert result["valid_from"] == date(2024, 2, 29)
    assert result["valid_until"] == date(2029, 2, 28)
    assert result["review_due_at"] == date(2029, 2, 28)


def test_building_completion_certificate_creates_thirty_year_structural_review_date():
    result = calculate_document_validity(
        validity_type="BUILDING_COMPLETION_CERTIFICATE",
        issue_date=date(1996, 7, 1),
        valid_from=None,
        valid_until=None,
        lease_start_date=None,
        lease_end_date=None,
        maximum_course_duration_years=None,
        application_submitted_at=None,
        validity_basis_reference="AICTE APH 2024-27 Clause 6.17(h)",
    )
    assert result["review_due_at"] == date(2026, 7, 1)
    assert result["valid_until"] is None


def test_fire_safety_certificate_requires_issuer_defined_expiry():
    with pytest.raises(HTTPException) as exc:
        calculate_document_validity(
            validity_type="FIRE_SAFETY_CERTIFICATE",
            issue_date=date(2026, 1, 1),
            valid_from=None,
            valid_until=None,
            lease_start_date=None,
            lease_end_date=None,
            maximum_course_duration_years=None,
            application_submitted_at=None,
            validity_basis_reference="Issuing Authority Certificate",
        )
    assert exc.value.status_code == 422


def test_fire_safety_certificate_uses_issuer_expiry_not_a_fixed_platform_period():
    result = calculate_document_validity(
        validity_type="FIRE_SAFETY_CERTIFICATE",
        issue_date=date(2026, 1, 1),
        valid_from=None,
        valid_until=date(2027, 8, 15),
        lease_start_date=None,
        lease_end_date=None,
        maximum_course_duration_years=None,
        application_submitted_at=None,
        validity_basis_reference="Validity date printed by the issuing authority",
    )
    assert result["valid_until"] == date(2027, 8, 15)


def test_lease_tracks_thirty_year_total_term_and_live_course_duration_at_submission():
    submitted_at = datetime(2026, 10, 30, 12, 0, tzinfo=UTC)
    result = calculate_document_validity(
        validity_type="LEASE_DEED",
        issue_date=None,
        valid_from=None,
        valid_until=None,
        lease_start_date=date(1998, 10, 30),
        lease_end_date=date(2028, 10, 30),
        maximum_course_duration_years=2,
        application_submitted_at=submitted_at,
        validity_basis_reference="AICTE APH 2024-27 Clauses 2.2(e) and 6.17(a)",
    )
    assert result["lease_minimum_term_met"] is True
    assert result["lease_live_term_met_at_submission"] is True
    assert result["lease_eoa_cutoff_year_triggered"] is True
    assert result["lease_assessed_on"] == date(2026, 10, 30)


def test_lease_with_less_than_thirty_years_records_a_review_observation():
    result = calculate_document_validity(
        validity_type="LEASE_DEED",
        issue_date=None,
        valid_from=None,
        valid_until=None,
        lease_start_date=date(2000, 1, 1),
        lease_end_date=date(2029, 12, 31),
        maximum_course_duration_years=4,
        application_submitted_at=datetime(2026, 10, 30, 12, 0, tzinfo=UTC),
        validity_basis_reference="AICTE APH 2024-27 Clause 6.17(a)",
    )
    assert result["lease_minimum_term_met"] is False
    assert result["lease_live_term_met_at_submission"] is False
    assert result["lease_eoa_cutoff_year_triggered"] is False


def test_issuer_defined_document_requires_dates_and_basis():
    with pytest.raises(HTTPException):
        calculate_document_validity(
            validity_type="ISSUER_DATED_DOCUMENT",
            issue_date=date(2026, 1, 1),
            valid_from=None,
            valid_until=None,
            lease_start_date=None,
            lease_end_date=None,
            maximum_course_duration_years=None,
            application_submitted_at=None,
            validity_basis_reference="Registrar",
        )


def test_calendar_year_helper_handles_february_leap_years():
    assert add_calendar_years(date(2024, 2, 29), 1) == date(2025, 2, 28)

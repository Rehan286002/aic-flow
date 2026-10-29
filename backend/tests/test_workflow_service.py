from types import SimpleNamespace
from datetime import UTC, datetime

import pytest
from fastapi import HTTPException

from app.services.workflow_service import (
    calculate_appeal_deadline,
    case_access_context,
    evc_completion_assignee,
    intake_review_assignee,
    route_profile_for,
    validate_ec_decision_stage,
    validate_shc_hearing_record,
    validate_shc_recommendation,
    validate_shc_stage,
    validate_evc_report_stage,
    validate_evc_schedule_stage,
    validate_operational_event,
    validate_transition,
)


def case(stage: str, route: dict):
    return SimpleNamespace(current_stage=stage, route_snapshot=route)


def test_intake_review_assignment_stays_with_intake_for_eoa_route():
    _code, _version, snapshot = route_profile_for("EOA_SELF_DISCLOSURE")
    assert intake_review_assignee(snapshot) == "INTAKE_OFFICER"


def test_intake_review_assignment_hands_increase_intake_to_scrutiny():
    _code, _version, snapshot = route_profile_for("INCREASE_INTAKE")
    assert intake_review_assignee(snapshot) == "SCRUTINY_OFFICER"


def test_unknown_route_does_not_auto_assign_scrutiny():
    _code, _version, snapshot = route_profile_for("UNCONFIGURED_CATEGORY")
    assert intake_review_assignee(snapshot) == "INTAKE_OFFICER"


def test_evc_completion_routes_to_shc_only_when_applicability_is_confirmed():
    assert evc_completion_assignee({"requires_committee": True}) == "COMMITTEE_SECRETARIAT"
    assert evc_completion_assignee({"requires_committee": False}) == "REGIONAL_OFFICER"
    assert evc_completion_assignee({"requires_committee": None}) == "REGIONAL_OFFICER"


def test_shc_proceeding_requires_route_confirmed_committee_stage():
    validate_shc_stage(case("COMMITTEE_PROCEEDINGS", {"requires_committee": True}))
    with pytest.raises(HTTPException) as exc:
        validate_shc_stage(case("COMMITTEE_PROCEEDINGS", {"requires_committee": None}))
    assert exc.value.status_code == 409
    with pytest.raises(HTTPException) as exc:
        validate_shc_stage(case("EVC_COMPLETED", {"requires_committee": True}))
    assert exc.value.status_code == 409


def test_shc_hearing_requires_a_scheduled_proceeding():
    validate_shc_hearing_record(
        case("COMMITTEE_PROCEEDINGS", {"requires_committee": True}),
        SimpleNamespace(status="SCHEDULED", hearing_scheduled_at=None),
    )
    with pytest.raises(HTTPException) as exc:
        validate_shc_hearing_record(case("COMMITTEE_PROCEEDINGS", {"requires_committee": True}), None)
    assert exc.value.status_code == 409


def test_shc_recommendation_requires_hearing_record():
    validate_shc_recommendation(
        case("COMMITTEE_PROCEEDINGS", {"requires_committee": True}),
        SimpleNamespace(status="HEARING_RECORDED"),
    )
    with pytest.raises(HTTPException) as exc:
        validate_shc_recommendation(
            case("COMMITTEE_PROCEEDINGS", {"requires_committee": True}),
            SimpleNamespace(status="SCHEDULED"),
        )
    assert exc.value.status_code == 409


def test_executive_committee_decision_requires_authority_and_correct_stage():
    validate_ec_decision_stage(case("AWAITING_AUTHORITY", {}), "COMPETENT_AUTHORITY")
    with pytest.raises(HTTPException) as exc:
        validate_ec_decision_stage(case("AWAITING_AUTHORITY", {}), "COMMITTEE_SECRETARIAT")
    assert exc.value.status_code == 403
    with pytest.raises(HTTPException) as exc:
        validate_ec_decision_stage(case("EVC_COMPLETED", {}), "COMPETENT_AUTHORITY")
    assert exc.value.status_code == 409


def test_speaking_order_upload_starts_seven_day_appeal_window():
    uploaded_at = datetime(2026, 10, 30, 12, 0, tzinfo=UTC)
    assert calculate_appeal_deadline(uploaded_at) == datetime(2026, 11, 6, 12, 0, tzinfo=UTC)


def test_eoa_self_disclosure_has_no_scrutiny_or_evc_stage():
    route_code, version, snapshot = route_profile_for("EOA_SELF_DISCLOSURE")
    assert route_code == "EOA_SELF_DISCLOSURE"
    assert version == "APH_2024_2027_BASELINE"
    assert snapshot["requires_scrutiny"] is False
    assert snapshot["requires_evc"] is False


def test_increase_intake_requires_scrutiny_and_evc_before_authority():
    _code, _version, snapshot = route_profile_for("INCREASE_INTAKE")
    with pytest.raises(HTTPException) as exc:
        validate_transition(case("SCRUTINY", snapshot), "SCRUTINY_OFFICER", "AWAITING_AUTHORITY")
    assert exc.value.status_code == 409


def test_increase_intake_cannot_skip_evc_to_committee():
    _code, _version, snapshot = route_profile_for("INCREASE_INTAKE")
    with pytest.raises(HTTPException) as exc:
        validate_transition(case("SCRUTINY", snapshot), "SCRUTINY_OFFICER", "COMMITTEE_PROCEEDINGS")
    assert exc.value.status_code == 403


def test_unknown_category_requires_manual_policy_confirmation():
    _code, _version, snapshot = route_profile_for("UNCONFIGURED_CATEGORY")
    assert snapshot["route_status"] == "MANUAL_CONFIRMATION_REQUIRED"
    with pytest.raises(HTTPException) as exc:
        validate_transition(case("INTAKE_REVIEW", snapshot), "INTAKE_OFFICER", "AWAITING_AUTHORITY")
    assert exc.value.status_code == 409


def test_eoa_category_cannot_enter_scrutiny():
    _code, _version, snapshot = route_profile_for("EOA_SELF_DISCLOSURE")
    with pytest.raises(HTTPException) as exc:
        validate_transition(case("INTAKE_REVIEW", snapshot), "SCRUTINY_OFFICER", "SCRUTINY")
    assert exc.value.status_code == 409


def test_increase_intake_keeps_committee_applicability_unconfirmed():
    _code, _version, snapshot = route_profile_for("INCREASE_INTAKE")
    assert snapshot["requires_committee"] is None
    with pytest.raises(HTTPException) as exc:
        validate_transition(case("EVC_COMPLETED", snapshot), "EVC_COORDINATOR", "AWAITING_AUTHORITY")
    assert exc.value.status_code == 409


def test_eoa_supervisory_hold_returns_to_intake_not_scrutiny():
    _code, _version, snapshot = route_profile_for("EOA_SELF_DISCLOSURE")
    with pytest.raises(HTTPException) as exc:
        validate_transition(case("ON_HOLD", snapshot), "BUREAU_SUPERVISOR", "SCRUTINY")
    assert exc.value.status_code == 409
    validate_transition(case("ON_HOLD", snapshot), "BUREAU_SUPERVISOR", "INTAKE_REVIEW")


def test_evc_schedule_requires_route_applicability_and_coordination_stage():
    validate_evc_schedule_stage(case("EVC_COORDINATION", {"requires_evc": True}))
    validate_evc_schedule_stage(case("EVC_SCHEDULED", {"requires_evc": True}), SimpleNamespace(status="SCHEDULED"))
    with pytest.raises(HTTPException) as exc:
        validate_evc_schedule_stage(case("SCRUTINY", {"requires_evc": True}))
    assert exc.value.status_code == 409
    with pytest.raises(HTTPException) as exc:
        validate_evc_schedule_stage(case("EVC_COORDINATION", {"requires_evc": False}))
    assert exc.value.status_code == 409


def test_evc_completed_visit_cannot_be_rescheduled():
    with pytest.raises(HTTPException) as exc:
        validate_evc_schedule_stage(
            case("EVC_SCHEDULED", {"requires_evc": True}),
            SimpleNamespace(status="COMPLETED"),
        )
    assert exc.value.status_code == 409


def test_evc_report_requires_a_current_scheduled_visit():
    validate_evc_report_stage(
        case("EVC_SCHEDULED", {"requires_evc": True}),
        SimpleNamespace(status="SCHEDULED"),
    )
    with pytest.raises(HTTPException) as exc:
        validate_evc_report_stage(case("EVC_SCHEDULED", {}), None)
    assert exc.value.status_code == 409
    with pytest.raises(HTTPException) as exc:
        validate_evc_report_stage(case("EVC_COORDINATION", {}), SimpleNamespace(status="SCHEDULED"))
    assert exc.value.status_code == 409


def test_committee_events_require_confirmed_applicability_and_proceedings_stage():
    validate_operational_event(case("COMMITTEE_PROCEEDINGS", {"requires_committee": True}), "COMMITTEE_CONVENED")
    with pytest.raises(HTTPException) as exc:
        validate_operational_event(case("COMMITTEE_PROCEEDINGS", {"requires_committee": None}), "COMMITTEE_CONVENED")
    assert exc.value.status_code == 409
    with pytest.raises(HTTPException) as exc:
        validate_operational_event(case("EVC_COMPLETED", {"requires_committee": True}), "COMMITTEE_MINUTES_RECORDED")
    assert exc.value.status_code == 409


def test_individually_assigned_case_is_not_visible_to_other_officers():
    app = SimpleNamespace(institution_id="institution-1", review_team_id="team-1")
    workflow_case = SimpleNamespace(assigned_user_id="officer-1")
    contexts = [SimpleNamespace(role_code="SCRUTINY_OFFICER", review_team_id="team-1", institution_id=None)]
    with pytest.raises(HTTPException) as exc:
        case_access_context(None, app, contexts, case=workflow_case, user_id="officer-2")
    assert exc.value.status_code == 403
    assert case_access_context(None, app, contexts, case=workflow_case, user_id="officer-1") is contexts[0]


def test_supervisor_can_view_individually_assigned_case_within_team_scope():
    app = SimpleNamespace(institution_id="institution-1", review_team_id="team-1")
    workflow_case = SimpleNamespace(assigned_user_id="officer-1")
    context = SimpleNamespace(role_code="BUREAU_SUPERVISOR", review_team_id="team-1", institution_id=None)
    assert case_access_context(None, app, [context], case=workflow_case, user_id="supervisor-1") is context

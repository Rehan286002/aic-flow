from types import SimpleNamespace

import pytest
from fastapi import HTTPException

from app.services.workflow_service import (
    case_access_context,
    institution_notification_projection,
    route_profile_for,
    validate_operational_event,
    validate_transition,
)


def case(stage: str, route: dict):
    return SimpleNamespace(current_stage=stage, route_snapshot=route)


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


def test_evc_schedule_event_is_restricted_to_coordination_stage():
    validate_operational_event(case("EVC_COORDINATION", {}), "EVC_VISIT_SCHEDULED")
    with pytest.raises(HTTPException) as exc:
        validate_operational_event(case("SCRUTINY", {}), "EVC_VISIT_SCHEDULED")
    assert exc.value.status_code == 409


def test_evc_report_event_is_restricted_to_scheduled_stage():
    validate_operational_event(case("EVC_SCHEDULED", {}), "EVC_REPORT_RECORDED")
    with pytest.raises(HTTPException) as exc:
        validate_operational_event(case("EVC_COORDINATION", {}), "EVC_REPORT_RECORDED")
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
    workflow_case = SimpleNamespace(
        assigned_user_id="officer-1",
        assigned_role_code="SCRUTINY_OFFICER",
        current_stage="SCRUTINY",
        route_snapshot={"requires_committee": False},
    )
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



def test_committee_secretariat_can_open_evc_completed_route_handoff():
    app = SimpleNamespace(institution_id="institution-1", review_team_id="team-1")
    workflow_case = SimpleNamespace(
        assigned_user_id="evc-member-1",
        assigned_role_code="EVC_MEMBER",
        current_stage="EVC_COMPLETED",
        route_snapshot={"requires_committee": True},
    )
    context = SimpleNamespace(
        role_code="COMMITTEE_SECRETARIAT",
        review_team_id="team-1",
        institution_id=None,
    )
    assert case_access_context(
        None, app, [context], case=workflow_case, user_id="committee-officer-1"
    ) is context


def test_evc_coordinator_can_open_evc_completed_route_without_committee():
    app = SimpleNamespace(institution_id="institution-1", review_team_id="team-1")
    workflow_case = SimpleNamespace(
        assigned_user_id="evc-member-1",
        assigned_role_code="EVC_MEMBER",
        current_stage="EVC_COMPLETED",
        route_snapshot={"requires_committee": False},
    )
    context = SimpleNamespace(
        role_code="EVC_COORDINATOR",
        review_team_id="team-1",
        institution_id=None,
    )
    assert case_access_context(
        None, app, [context], case=workflow_case, user_id="evc-coordinator-1"
    ) is context



@pytest.mark.parametrize(
    "event_type",
    [
        "OFFICER_NOTE",
        "EVC_REPORT_RECORDED",
        "COMMITTEE_CONVENED",
        "COMMITTEE_MINUTES_RECORDED",
        "DECISION_RECORDED",
        "ESCALATION_ACKNOWLEDGED",
        "ESCALATION_RESOLVED",
        "DEMO_ESCALATION_CREATED",
    ],
)
def test_internal_workflow_events_are_not_projected_to_institution(event_type):
    event = SimpleNamespace(
        event_type=event_type,
        event_payload={"internal_note": "Confidential officer or committee details"},
        summary="Confidential internal summary",
        to_stage=None,
    )
    assert institution_notification_projection(event) is None


def test_clarification_notification_requires_explicit_institution_visibility():
    private_event = SimpleNamespace(
        event_type="CLARIFICATION_REQUESTED",
        event_payload={"institution_visible": False},
        summary="Internal-only scrutiny observation",
        to_stage=None,
    )
    assert institution_notification_projection(private_event) is None

    public_event = SimpleNamespace(
        event_type="CLARIFICATION_REQUESTED",
        event_payload={"institution_visible": True},
        summary="Please upload the revised certificate.",
        to_stage=None,
    )
    title, body, severity = institution_notification_projection(public_event)
    assert title == "Clarification response required"
    assert body == "Please upload the revised certificate."
    assert severity == "WARNING"


def test_stage_transition_uses_a_safe_status_message_not_internal_reason():
    event = SimpleNamespace(
        event_type="STAGE_TRANSITION",
        event_payload={},
        summary="Internal officer note: evidence concern and escalation context.",
        to_stage="CLARIFICATION_REQUESTED",
    )
    title, body, severity = institution_notification_projection(event)
    assert title == "Clarification response required"
    assert "Internal officer note" not in body
    assert "Open Clarifications" in body
    assert severity == "WARNING"


def test_institution_notification_for_evc_contains_only_visit_date():
    event = SimpleNamespace(
        event_type="EVC_VISIT_SCHEDULED",
        event_payload={
            "visit_date": "2026-11-15",
            "location": "Restricted internal location notes",
        },
        summary="Internal schedule summary with confidential details.",
        to_stage=None,
    )
    title, body, severity = institution_notification_projection(event)
    assert title == "EVC visit scheduled"
    assert "2026-11-15" in body
    assert "Restricted internal location notes" not in body
    assert "confidential" not in body.lower()
    assert severity == "INFO"

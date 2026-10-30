"""Seed a complete, synthetic AIC-Flow walkthrough for local development.

This is intentionally separate from seed_ci_test_data.py. It creates clearly
marked demo records only and refuses production/test environments. It does
not publish APH policy, create real AICTE records, or create statutory outcomes.
"""

from __future__ import annotations

import getpass
import hashlib
import os
import sys
from datetime import UTC, date, datetime, timedelta
from pathlib import Path

from sqlalchemy.engine import make_url

BACKEND_DIR = Path(__file__).resolve().parents[1]
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError

from app.core.config import settings
from app.core.security import hash_password
from app.db.session import SessionLocal
from app.models.application import Application
from app.models.application_revision import ApplicationRevision
from app.models.application_status_history import ApplicationStatusHistory
from app.models.compliance_obligation import ComplianceObligation
from app.models.document import Document
from app.models.document_type import DocumentType
from app.models.document_validity_record import DocumentValidityRecord
from app.models.document_version import DocumentVersion
from app.models.enums import (
    ApplicationFamily,
    ApplicationStatus,
    RevisionStatus,
    RoleCode,
    TeamRole,
    UserStatus,
)
from app.models.institution import Institution
from app.models.institution_membership import InstitutionMembership
from app.models.review_team import ReviewTeam
from app.models.review_team_member import ReviewTeamMember
from app.models.role import Role
from app.models.user import User
from app.models.user_role_assignment import UserRoleAssignment
from app.models.workflow_case import WorkflowCase
from app.models.workflow_event import WorkflowEvent
from app.services.checklist_service import (
    get_published_template_for_application,
    initialize_revision_requirements,
    seed_standard_references,
)
from app.services.workflow_service import add_workflow_event, create_workflow_case

DEMO_INSTITUTION_CODE = "DEMO-AICTE-LOCAL-0001"
DEMO_TEAM_NAME = "AIC-Flow Local Demonstration Team"
DEMO_TEAM_CODE = "AIC-FLOW-DEMO-TEAM-2026"
DEMO_ACADEMIC_YEAR = "2026-27"

ROLE_ACCOUNTS = [
    ("institution", "demo.institution@aic-flow.internal", "Demo Institution Representative", RoleCode.INSTITUTION_USER),
    ("intake", "demo.intake@aic-flow.internal", "Demo Registry Intake Officer", RoleCode.INTAKE_OFFICER),
    ("scrutiny", "demo.scrutiny@aic-flow.internal", "Demo Scrutiny Officer", RoleCode.SCRUTINY_OFFICER),
    ("regional", "demo.regional@aic-flow.internal", "Demo Regional Coordinator", RoleCode.REGIONAL_OFFICER),
    ("evc_coordinator", "demo.evc@aic-flow.internal", "Demo EVC Coordinator", RoleCode.EVC_COORDINATOR),
    ("evc_member", "demo.evc.member@aic-flow.internal", "Demo EVC Participant", RoleCode.EVC_MEMBER),
    ("committee", "demo.committee@aic-flow.internal", "Demo Committee Secretariat", RoleCode.COMMITTEE_SECRETARIAT),
    ("supervisor", "demo.supervisor@aic-flow.internal", "Demo Bureau Supervisor", RoleCode.BUREAU_SUPERVISOR),
    ("authority", "demo.authority@aic-flow.internal", "Demo Competent Authority", RoleCode.COMPETENT_AUTHORITY),
    ("admin", "demo.admin@aic-flow.internal", "Demo Platform Administrator", RoleCode.ADMIN),
    ("policy", "demo.policy@aic-flow.internal", "Demo Regulatory Policy Publisher", RoleCode.REGULATORY_POLICY_PUBLISHER),
]

SCENARIOS = [
    {
        "suffix": "0001", "process_type": "EOA_SELF_DISCLOSURE", "stage": "DRAFT",
        "assigned_role": None, "owner": None, "scrutiny": False, "evc": False, "committee": False,
        "due_days": 8, "summary": "Draft application awaiting institution submission.",
    },
    {
        "suffix": "0002", "process_type": "DEMO_INTAKE_QUEUE", "stage": "SUBMITTED",
        "assigned_role": "INTAKE_OFFICER", "owner": "intake", "scrutiny": True, "evc": True, "committee": False,
        "due_days": 2, "summary": "Newly submitted application awaiting registry receipt checks.",
    },
    {
        "suffix": "0003", "process_type": "DEMO_CLARIFICATION", "stage": "CLARIFICATION_REQUESTED",
        "assigned_role": "SCRUTINY_OFFICER", "owner": "scrutiny", "scrutiny": True, "evc": False, "committee": False,
        "due_days": 5, "summary": "Institution response requested for a synthetic document discrepancy.",
    },
    {
        "suffix": "0004", "process_type": "DEMO_SCRUTINY_EVC", "stage": "SCRUTINY",
        "assigned_role": "SCRUTINY_OFFICER", "owner": "scrutiny", "scrutiny": True, "evc": True, "committee": False,
        "due_days": -1, "summary": "Scrutiny case with an overdue internal demo service target.",
    },
    {
        "suffix": "0005", "process_type": "DEMO_EVC_COORDINATION", "stage": "EVC_COORDINATION",
        "assigned_role": "EVC_COORDINATOR", "owner": "evc_coordinator", "scrutiny": True, "evc": True, "committee": False,
        "due_days": -2, "summary": "EVC coordination task awaiting an administrative schedule.",
    },
    {
        "suffix": "0006", "process_type": "DEMO_EVC_SCHEDULED", "stage": "EVC_SCHEDULED",
        "assigned_role": "EVC_MEMBER", "owner": "evc_member", "scrutiny": True, "evc": True, "committee": False,
        "due_days": 4, "summary": "Scheduled synthetic EVC visit awaiting the participant report.",
    },
    {
        "suffix": "0007", "process_type": "DEMO_SHC_PROCEEDING", "stage": "COMMITTEE_PROCEEDINGS",
        "assigned_role": "COMMITTEE_SECRETARIAT", "owner": "committee", "scrutiny": True, "evc": True, "committee": True,
        "due_days": 6, "summary": "Synthetic SHC proceeding with a recorded recommendation workflow.",
    },
    {
        "suffix": "0008", "process_type": "DEMO_AUTHORITY_DOCKET", "stage": "AWAITING_AUTHORITY",
        "assigned_role": "COMPETENT_AUTHORITY", "owner": "authority", "scrutiny": True, "evc": False, "committee": False,
        "due_days": 1, "summary": "Consolidated case dossier awaiting human authority review.",
    },
    {
        "suffix": "0009", "process_type": "DEMO_COMPLIANCE_TRACKING", "stage": "OBLIGATION_TRACKING",
        "assigned_role": "SCRUTINY_OFFICER", "owner": "scrutiny", "scrutiny": False, "evc": False, "committee": False,
        "due_days": 20, "summary": "Approved-with-conditions demo case with open undertakings and evidence verification.",
    },
]


def require_local_environment() -> None:
    environment = settings.app_env.strip().lower()
    if environment not in {"local", "development"}:
        raise SystemExit(
            "Refusing demo seeding. APP_ENV must be local or development. "
            "This script must never run against test or production."
        )
    database_url = make_url(settings.database_url)
    if database_url.host not in {"localhost", "127.0.0.1", "::1"}:
        raise SystemExit(
            "Refusing demo seeding: DATABASE_URL must point to a loopback host. "
            "Use the local PostgreSQL service from compose.yaml."
        )
    if database_url.database != "aic_flow":
        raise SystemExit(
            "Refusing demo seeding: DATABASE_URL must target the local 'aic_flow' database. "
            f"Received {database_url.database!r}."
        )


def prompt_demo_password() -> str:
    configured = os.getenv("AIC_FLOW_DEMO_PASSWORD")
    if configured:
        if len(configured) < 12:
            raise SystemExit("AIC_FLOW_DEMO_PASSWORD must contain at least 12 characters.")
        return configured
    while True:
        password = getpass.getpass("Set one local demo password for newly created demo accounts (12+ characters): ")
        confirmation = getpass.getpass("Confirm local demo password: ")
        if password != confirmation:
            print("Passwords do not match.")
            continue
        if len(password) < 12:
            print("Use at least 12 characters.")
            continue
        return password


def get_or_create_user(db, email: str, name: str, password: str) -> User:
    user = db.scalar(select(User).where(func.lower(User.email) == email.lower()))
    if user is None:
        user = User(
            email=email,
            full_name=name,
            password_hash=hash_password(password),
            status=UserStatus.ACTIVE,
        )
        db.add(user)
        db.flush()
    elif user.status != UserStatus.ACTIVE:
        raise RuntimeError(f"Existing demo account {email} is not ACTIVE; no account state was changed.")
    elif not user.password_hash:
        user.password_hash = hash_password(password)
    return user


def ensure_institution_membership(db, institution_id, user_id) -> None:
    membership = db.scalar(select(InstitutionMembership).where(
        InstitutionMembership.institution_id == institution_id,
        InstitutionMembership.user_id == user_id,
    ))
    if membership is None:
        db.add(InstitutionMembership(institution_id=institution_id, user_id=user_id, is_active=True))
    elif not membership.is_active:
        raise RuntimeError("The existing demo institution membership is inactive; refusing to reactivate it.")


def ensure_team_membership(db, team_id, user_id, role_code: RoleCode) -> None:
    membership = db.scalar(select(ReviewTeamMember).where(
        ReviewTeamMember.review_team_id == team_id,
        ReviewTeamMember.user_id == user_id,
    ))
    if membership is None:
        db.add(ReviewTeamMember(
            review_team_id=team_id,
            user_id=user_id,
            team_role=TeamRole(role_code.value),
            is_active=True,
        ))
    elif membership.team_role != TeamRole(role_code.value) or not membership.is_active:
        raise RuntimeError(f"Existing team membership for {role_code.value} conflicts with the demo role; no change was made.")


def ensure_role_assignment(db, user: User, role_code: RoleCode, *, institution_id=None, team_id=None) -> None:
    role = db.scalar(select(Role).where(Role.role_code == role_code.value))
    if role is None:
        raise RuntimeError(f"Role {role_code.value} is missing. Apply migrations first.")
    existing = db.scalar(select(UserRoleAssignment).where(
        UserRoleAssignment.user_id == user.user_id,
        UserRoleAssignment.role_id == role.role_id,
        UserRoleAssignment.institution_id == institution_id,
        UserRoleAssignment.review_team_id == team_id,
        UserRoleAssignment.revoked_at.is_(None),
    ))
    if existing is None:
        db.add(UserRoleAssignment(
            user_id=user.user_id,
            role_id=role.role_id,
            institution_id=institution_id,
            review_team_id=team_id,
        ))


def seed_identity(db, password: str):
    institution = db.scalar(select(Institution).where(
        Institution.aicte_permanent_institution_id == DEMO_INSTITUTION_CODE
    ))
    if institution is None:
        institution = Institution(
            aicte_permanent_institution_id=DEMO_INSTITUTION_CODE,
            institution_name="Apex Institute of Technology (Synthetic Demo)",
            institution_type="PRIVATE_SELF_FINANCING",
            address_line="Synthetic demonstration address; not an AICTE registry address",
            district="Chennai",
            state="Tamil Nadu",
            postal_code="600000",
            is_active=True,
        )
        db.add(institution)
        db.flush()

    team = db.scalar(select(ReviewTeam).where(ReviewTeam.team_name == DEMO_TEAM_NAME))
    if team is None:
        team = ReviewTeam(
            team_name=DEMO_TEAM_NAME,
            description="Synthetic local demonstration team. Not an AICTE regional office.",
            is_active=True,
        )
        db.add(team)
        db.flush()
    elif not team.is_active:
        raise RuntimeError("The synthetic demo team exists but is inactive.")

    people = {}
    for key, email, name, role_code in ROLE_ACCOUNTS:
        user = get_or_create_user(db, email, name, password)
        people[key] = user
        if role_code == RoleCode.INSTITUTION_USER:
            ensure_institution_membership(db, institution.institution_id, user.user_id)
            ensure_role_assignment(db, user, role_code, institution_id=institution.institution_id)
        elif role_code in {RoleCode.ADMIN, RoleCode.REGULATORY_POLICY_PUBLISHER}:
            ensure_role_assignment(db, user, role_code)
        else:
            ensure_team_membership(db, team.review_team_id, user.user_id, role_code)
            ensure_role_assignment(db, user, role_code, team_id=team.review_team_id)

    db.flush()
    return institution, team, people


def stage_status(stage: str) -> ApplicationStatus:
    if stage == "DRAFT":
        return ApplicationStatus.DRAFT
    if stage == "CLARIFICATION_REQUESTED":
        return ApplicationStatus.RECTIFICATION_REQUESTED
    if stage in {"SUBMITTED", "INTAKE_REVIEW"}:
        return ApplicationStatus.SUBMITTED
    if stage in {"SCRUTINY", "RESUBMITTED", "EVC_COORDINATION", "EVC_SCHEDULED", "EVC_COMPLETED"}:
        return ApplicationStatus.UNDER_AUDITOR_REVIEW
    if stage == "COMMITTEE_PROCEEDINGS":
        return ApplicationStatus.UNDER_LEAD_REVIEW
    if stage == "AWAITING_AUTHORITY":
        return ApplicationStatus.AWAITING_AUTHORITY_DISPOSITION
    if stage == "OBLIGATION_TRACKING":
        return ApplicationStatus.APPROVED_WITH_CONDITIONS
    raise ValueError(f"Unsupported demo stage {stage}")


def make_route_snapshot(spec: dict) -> dict:
    stages = ["INTAKE_REVIEW"]
    if spec["scrutiny"]:
        stages.append("SCRUTINY")
    if spec["evc"]:
        stages.extend(["EVC_COORDINATION", "EVC_SCHEDULED", "EVC_COMPLETED"])
    if spec["committee"]:
        stages.append("COMMITTEE_PROCEEDINGS")
    stages.append("AWAITING_AUTHORITY")
    if spec["stage"] == "OBLIGATION_TRACKING":
        stages.append("OBLIGATION_TRACKING")
    return {
        "route_status": "SIMULATION_ONLY",
        "simulation": True,
        "simulation_code": "PS26262_ROLE_WORKFLOW_WALKTHROUGH",
        "requires_scrutiny": spec["scrutiny"],
        "requires_evc": spec["evc"],
        "requires_committee": spec["committee"],
        "steps": stages,
        "explanation": "Synthetic local demo path used to exercise role hand-offs. It is not an AICTE route determination.",
        "regulatory_policy_publication": "NOT_PUBLISHED",
    }



def stage_path_for(spec: dict) -> list[str]:
    if spec["stage"] == "DRAFT":
        return ["DRAFT"]
    if spec["stage"] == "SUBMITTED":
        return ["DRAFT", "SUBMITTED"]
    if spec["stage"] == "CLARIFICATION_REQUESTED":
        return ["DRAFT", "SUBMITTED", "INTAKE_REVIEW", "SCRUTINY", "CLARIFICATION_REQUESTED"]
    path = ["DRAFT", "SUBMITTED", "INTAKE_REVIEW"]
    if spec["scrutiny"]:
        path.append("SCRUTINY")
    if spec["evc"] and spec["stage"] in {
        "EVC_COORDINATION", "EVC_SCHEDULED", "EVC_COMPLETED", "COMMITTEE_PROCEEDINGS"
    }:
        path.append("EVC_COORDINATION")
        if spec["stage"] in {"EVC_SCHEDULED", "EVC_COMPLETED", "COMMITTEE_PROCEEDINGS"}:
            path.append("EVC_SCHEDULED")
        if spec["stage"] in {"EVC_COMPLETED", "COMMITTEE_PROCEEDINGS"}:
            path.append("EVC_COMPLETED")
        if spec["stage"] == "COMMITTEE_PROCEEDINGS":
            path.append("COMMITTEE_PROCEEDINGS")
    if spec["stage"] == "AWAITING_AUTHORITY":
        path.append("AWAITING_AUTHORITY")
    elif spec["stage"] == "OBLIGATION_TRACKING":
        path.extend(["AWAITING_AUTHORITY", "APPROVED_WITH_CONDITIONS", "OBLIGATION_TRACKING"])
    elif spec["stage"] not in path:
        path.append(spec["stage"])
    return path


STAGE_STATUS = {
    "DRAFT": ApplicationStatus.DRAFT,
    "SUBMITTED": ApplicationStatus.SUBMITTED,
    "INTAKE_REVIEW": ApplicationStatus.SUBMITTED,
    "SCRUTINY": ApplicationStatus.UNDER_AUDITOR_REVIEW,
    "CLARIFICATION_REQUESTED": ApplicationStatus.RECTIFICATION_REQUESTED,
    "RESUBMITTED": ApplicationStatus.RESUBMITTED,
    "EVC_COORDINATION": ApplicationStatus.UNDER_AUDITOR_REVIEW,
    "EVC_SCHEDULED": ApplicationStatus.UNDER_AUDITOR_REVIEW,
    "EVC_COMPLETED": ApplicationStatus.UNDER_AUDITOR_REVIEW,
    "COMMITTEE_PROCEEDINGS": ApplicationStatus.UNDER_LEAD_REVIEW,
    "AWAITING_AUTHORITY": ApplicationStatus.AWAITING_AUTHORITY_DISPOSITION,
    "APPROVED_WITH_CONDITIONS": ApplicationStatus.APPROVED_WITH_CONDITIONS,
    "OBLIGATION_TRACKING": ApplicationStatus.APPROVED_WITH_CONDITIONS,
}


def stage_actor_key(to_stage: str) -> str:
    if to_stage == "SUBMITTED":
        return "institution"
    if to_stage == "INTAKE_REVIEW":
        return "intake"
    if to_stage in {"SCRUTINY", "CLARIFICATION_REQUESTED", "EVC_COORDINATION"}:
        return "scrutiny"
    if to_stage == "EVC_SCHEDULED":
        return "evc_coordinator"
    if to_stage == "EVC_COMPLETED":
        return "evc_member"
    if to_stage == "COMMITTEE_PROCEEDINGS":
        return "committee"
    if to_stage in {"AWAITING_AUTHORITY", "APPROVED_WITH_CONDITIONS", "OBLIGATION_TRACKING"}:
        return "authority"
    return "institution"


def stage_transition_actor_key(from_stage: str, to_stage: str) -> str:
    if to_stage == "AWAITING_AUTHORITY":
        return {
            "INTAKE_REVIEW": "intake",
            "SCRUTINY": "scrutiny",
            "EVC_COMPLETED": "evc_coordinator",
            "COMMITTEE_PROCEEDINGS": "committee",
        }.get(from_stage, "authority")
    return stage_actor_key(to_stage)


STAGE_RECEIVING_ASSIGNMENT = {
    "DRAFT": (None, None),
    "SUBMITTED": ("INTAKE_OFFICER", "intake"),
    "INTAKE_REVIEW": ("SCRUTINY_OFFICER", "scrutiny"),
    "SCRUTINY": ("SCRUTINY_OFFICER", "scrutiny"),
    "CLARIFICATION_REQUESTED": ("SCRUTINY_OFFICER", "scrutiny"),
    "EVC_COORDINATION": ("EVC_COORDINATOR", "evc_coordinator"),
    "EVC_SCHEDULED": ("EVC_MEMBER", "evc_member"),
    "EVC_COMPLETED": ("EVC_MEMBER", "evc_member"),
    "COMMITTEE_PROCEEDINGS": ("COMMITTEE_SECRETARIAT", "committee"),
    "AWAITING_AUTHORITY": ("COMPETENT_AUTHORITY", "authority"),
    "APPROVED_WITH_CONDITIONS": ("COMPETENT_AUTHORITY", "authority"),
    "OBLIGATION_TRACKING": ("SCRUTINY_OFFICER", "scrutiny"),
}


def seed_stage_history(db, application, case, people, path: list[str]) -> None:
    previous_status = None
    previous_stage = None
    for stage in path:
        current_status = STAGE_STATUS[stage]
        actor_key = (
            stage_actor_key(stage)
            if previous_stage is None
            else stage_transition_actor_key(previous_stage, stage)
        )
        actor = people[actor_key]
        receiving_role, receiving_user_key = STAGE_RECEIVING_ASSIGNMENT[stage]
        case.assigned_role_code = receiving_role
        case.assigned_user_id = (
            people[receiving_user_key].user_id if receiving_user_key else None
        )
        if current_status != previous_status:
            db.add(ApplicationStatusHistory(
                application_id=application.application_id,
                from_status=previous_status,
                to_status=current_status,
                changed_by=actor.user_id,
                change_reason=(
                    "Synthetic local demo status history. "
                    "This does not represent an official AICTE decision or regulatory deadline."
                ),
            ))
            previous_status = current_status

        if previous_stage is not None:
            add_workflow_event(
                db,
                case,
                actor.user_id,
                event_type="STAGE_TRANSITION",
                summary=(
                    "Synthetic walkthrough movement from "
                    + previous_stage.replace("_", " ").lower()
                    + " to "
                    + stage.replace("_", " ").lower()
                    + "."
                ),
                from_stage=previous_stage,
                to_stage=stage,
                event_payload={
                    "demo_only": True,
                    "simulation_code": "PS26262_ROLE_WORKFLOW_WALKTHROUGH",
                    "actor_role": actor_key.upper(),
                    "historical_seed_event": True,
                },
            )
        previous_stage = stage


def seed_application_case(db, institution, team, people, spec: dict):
    application_number = "DEMO-26262-" + spec["suffix"]
    application = db.scalar(select(Application).where(Application.application_number == application_number))
    if application is not None:
        case = db.scalar(select(WorkflowCase).where(WorkflowCase.application_id == application.application_id))
        if case is None:
            raise RuntimeError(f"Demo application {application_number} exists without its workflow case.")
        return application, case, False

    user = people["institution"]
    status = stage_status(spec["stage"])
    application = Application(
        application_number=application_number,
        institution_id=institution.institution_id,
        application_family=ApplicationFamily.EXISTING_INSTITUTION,
        process_type=spec["process_type"],
        academic_year=DEMO_ACADEMIC_YEAR,
        status=status,
        review_team_id=team.review_team_id,
        created_by=user.user_id,
    )
    db.add(application)
    db.flush()

    revision_status = RevisionStatus.DRAFT if spec["stage"] in {"DRAFT", "CLARIFICATION_REQUESTED"} else RevisionStatus.SUBMITTED
    revision = ApplicationRevision(
        application_id=application.application_id,
        revision_number=1,
        status=revision_status,
        created_by=user.user_id,
        submitted_by=user.user_id if revision_status == RevisionStatus.SUBMITTED else None,
        submitted_at=datetime.now(UTC) if revision_status == RevisionStatus.SUBMITTED else None,
    )
    db.add(revision)
    db.flush()
    application.current_revision_id = revision.application_revision_id
    if revision_status == RevisionStatus.SUBMITTED:
        application.submitted_at = revision.submitted_at

    # A realistic chronological status history is added after the pinned demo path
    # is known. The application itself remains at the final scenario status.

    template = get_published_template_for_application(
        db, DEMO_ACADEMIC_YEAR, ApplicationFamily.EXISTING_INSTITUTION
    )
    if template is None:
        raise RuntimeError("Published baseline checklist not found. Run scripts/seed_checklist.py first.")
    initialize_revision_requirements(
        db,
        revision.application_revision_id,
        template.checklist_template_id,
        {
            "completion_certificate_issue_date": "1990-05-15",
            "payment_applicable": True,
            "application_remarks": "Synthetic local PS 26262 role simulation. Not for statutory submission.",
        },
    )

    case = create_workflow_case(db, application, user.user_id, spec["process_type"])
    path = stage_path_for(spec)
    seed_stage_history(db, application, case, people, path)
    now = datetime.now(UTC)
    owner = people.get(spec["owner"]) if spec["owner"] else None
    case.current_stage = spec["stage"]
    case.assigned_role_code = spec["assigned_role"]
    case.assigned_user_id = owner.user_id if owner else None
    case.route_code = "DEMO_ONLY_" + spec["suffix"]
    case.regulatory_version = "DEMO_SIMULATION_ONLY"
    case.route_snapshot = make_route_snapshot(spec)
    case.stage_entered_at = now - timedelta(days=max(1, abs(spec["due_days"]) + 1))
    case.due_at = now + timedelta(days=spec["due_days"])
    db.flush()

    actor = owner or user
    add_workflow_event(
        db,
        case,
        actor.user_id,
        event_type="DEMO_STAGE_CONTEXT",
        summary="Synthetic demo case prepared for the " + spec["stage"].replace("_", " ").lower() + " walkthrough.",
        event_payload={
            "demo_only": True,
            "simulation_code": "PS26262_ROLE_WORKFLOW_WALKTHROUGH",
            "stage": spec["stage"],
            "note": spec["summary"],
        },
    )

    if spec["stage"] == "CLARIFICATION_REQUESTED":
        add_workflow_event(
            db, case, people["scrutiny"].user_id,
            event_type="CLARIFICATION_REQUESTED",
            summary="Please upload the revised supporting document and provide the requested clarification.",
            event_payload={"demo_only": True, "institution_visible": True, "requested_item": "Revised supporting evidence"},
        )
    if spec["stage"] == "EVC_SCHEDULED":
        add_workflow_event(
            db, case, people["evc_coordinator"].user_id,
            event_type="EVC_VISIT_SCHEDULED",
            summary="Synthetic EVC visit scheduled for the local demonstration.",
            event_payload={
                "demo_only": True,
                "visit_date": (date.today() + timedelta(days=4)).isoformat(),
                "visit_mode": "PHYSICAL",
                "location": "Apex Institute synthetic campus, Chennai",
                "schedule_status": "PROPOSED",
                "coordination_only": True,
            },
        )
    if spec["stage"] == "COMMITTEE_PROCEEDINGS":
        add_workflow_event(
            db, case, people["evc_member"].user_id,
            event_type="EVC_REPORT_RECORDED",
            summary="Synthetic EVC report reference recorded for the proceeding walkthrough.",
            event_payload={"demo_only": True, "report_reference": "DEMO-EVC-REPORT-0007"},
        )
        add_workflow_event(
            db, case, people["committee"].user_id,
            event_type="COMMITTEE_CONVENED",
            summary="Synthetic SHC proceeding convened for the local role walkthrough.",
            event_payload={"demo_only": True, "proceeding_type": "SHC", "status": "CONVENED"},
        )
        add_workflow_event(
            db, case, people["committee"].user_id,
            event_type="COMMITTEE_MINUTES_RECORDED",
            summary="Synthetic SHC minutes reference recorded; this is a recommendation record only.",
            event_payload={"demo_only": True, "proceeding_type": "SHC", "minutes_reference": "DEMO-SHC-MINUTES-0007", "outcome_type": "OBSERVATION_OR_RECOMMENDATION"},
        )
    if spec["stage"] == "OBLIGATION_TRACKING":
        add_workflow_event(
            db, case, people["authority"].user_id,
            event_type="DECISION_RECORDED",
            summary="Synthetic approved-with-conditions order recorded for compliance tracking demonstration.",
            event_payload={
                "demo_only": True,
                "outcome": "APPROVED_WITH_CONDITIONS",
                "official_order_reference": "DEMO-ORDER-26262-0009",
                "decision_date": date.today().isoformat(),
                "statutory_decision_made_by_human": True,
            },
        )
    db.flush()
    return application, case, True


def seed_obligations(db, application, case, people) -> int:
    created = 0
    rows = [
        {
            "title": "Submit revised affidavit and undertaking evidence",
            "description": "Upload the synthetic supporting affidavit / undertaking requested in the demo condition.",
            "source_condition": "DEMO-ORDER-26262-0009 · Condition 1 · Synthetic demonstration only",
            "status": "OPEN",
            "due_at": datetime.now(UTC) + timedelta(days=12),
        },
        {
            "title": "Submit outstanding fire-safety compliance evidence",
            "description": "Provide supporting evidence for the pending fire-safety compliance condition.",
            "source_condition": "DEMO-ORDER-26262-0009 · Condition 2 · Synthetic demonstration only",
            "status": "OPEN",
            "due_at": datetime.now(UTC) - timedelta(days=4),
        },
        {
            "title": "Evidence received and awaiting officer verification",
            "description": "A synthetic submission is waiting in the verifier queue for a human review.",
            "source_condition": "DEMO-ORDER-26262-0009 · Condition 3 · Synthetic demonstration only",
            "status": "EVIDENCE_SUBMITTED",
            "due_at": datetime.now(UTC) + timedelta(days=2),
            "evidence_reference": "DEMO-COMPLIANCE-SUBMISSION-0003",
        },
    ]
    for row in rows:
        existing = db.scalar(select(ComplianceObligation).where(
            ComplianceObligation.workflow_case_id == case.workflow_case_id,
            ComplianceObligation.title == row["title"],
        ))
        if existing:
            continue
        obligation = ComplianceObligation(
            workflow_case_id=case.workflow_case_id,
            application_id=application.application_id,
            condition_code="DEMO-CONDITION-" + str(created + 1).zfill(2),
            title=row["title"],
            description=row["description"],
            source_condition=row["source_condition"],
            due_at=row["due_at"],
            status=row["status"],
            evidence_reference=row.get("evidence_reference"),
            submitted_at=datetime.now(UTC) - timedelta(hours=5) if row["status"] == "EVIDENCE_SUBMITTED" else None,
            created_by=people["authority"].user_id,
        )
        db.add(obligation)
        db.flush()
        add_workflow_event(
            db, case, people["authority"].user_id,
            event_type="DEMO_OBLIGATION_SEEDED",
            summary="Synthetic approval condition added to the local compliance ledger.",
            event_payload={"demo_only": True, "obligation_id": str(obligation.obligation_id), "status": obligation.status},
        )
        created += 1
    return created


def seed_document_validity(db, application, case, institution, people) -> int:
    document_type = db.scalar(select(DocumentType).where(DocumentType.type_code == "LEASE_DOCUMENT"))
    if document_type is None:
        document_type = DocumentType(
            type_code="LEASE_DOCUMENT",
            type_name="Lease Document (Demo Register)",
            description="Local synthetic metadata used to demonstrate expiry tracking; not a regulatory checklist declaration.",
            is_active=True,
        )
        db.add(document_type)
        db.flush()

    document = db.scalar(select(Document).where(
        Document.institution_id == institution.institution_id,
        Document.document_label == "DEMO_ONLY Lease Record",
    ))
    if document is None:
        document = Document(
            institution_id=institution.institution_id,
            document_type_id=document_type.document_type_id,
            document_label="DEMO_ONLY Lease Record",
            created_by=people["institution"].user_id,
        )
        db.add(document)
        db.flush()

    existing_versions = db.scalars(select(DocumentVersion).where(
        DocumentVersion.document_id == document.document_id
    ).order_by(DocumentVersion.version_number.asc())).all()
    if not existing_versions:
        previous = DocumentVersion(
            document_id=document.document_id,
            version_number=1,
            original_filename="DEMO-LEASE-OLD-V1-METADATA-ONLY.pdf",
            storage_key="demo-only/not-downloadable/lease-old-v1.pdf",
            mime_type="application/pdf",
            file_size_bytes=512,
            sha256_hex=hashlib.sha256(b"AIC-FLOW-DEMO-LEASE-OLD-V1").hexdigest(),
            page_count=1,
            uploaded_by=people["institution"].user_id,
        )
        db.add(previous)
        db.flush()
        replacement = DocumentVersion(
            document_id=document.document_id,
            version_number=2,
            original_filename="DEMO-LEASE-RENEWAL-V2-METADATA-ONLY.pdf",
            storage_key="demo-only/not-downloadable/lease-renewal-v2.pdf",
            mime_type="application/pdf",
            file_size_bytes=640,
            sha256_hex=hashlib.sha256(b"AIC-FLOW-DEMO-LEASE-RENEWAL-V2").hexdigest(),
            page_count=1,
            uploaded_by=people["institution"].user_id,
            replaces_document_version_id=previous.document_version_id,
        )
        db.add(replacement)
        db.flush()
        previous_record = DocumentValidityRecord(
            workflow_case_id=case.workflow_case_id,
            application_id=application.application_id,
            institution_id=institution.institution_id,
            document_id=document.document_id,
            document_version_id=previous.document_version_id,
            document_type="LEASE_DOCUMENT",
            issuer="Synthetic Property Trust",
            valid_from=date.today() - timedelta(days=365 * 3),
            valid_until=date.today() - timedelta(days=3),
            document_reference="DEMO-LEASE-OLD-V1 · metadata only · not downloadable",
            verification_status="VERIFIED",
            verification_note="Synthetic demo record; not an official verification.",
            created_by=people["institution"].user_id,
            verified_by=people["scrutiny"].user_id,
            verified_at=datetime.now(UTC) - timedelta(days=30),
        )
        db.add(previous_record)
        db.flush()
        current_record = DocumentValidityRecord(
            workflow_case_id=case.workflow_case_id,
            application_id=application.application_id,
            institution_id=institution.institution_id,
            document_id=document.document_id,
            document_version_id=replacement.document_version_id,
            document_type="LEASE_DOCUMENT",
            issuer="Synthetic Property Trust",
            valid_from=date.today() - timedelta(days=1),
            valid_until=date.today() + timedelta(days=20),
            document_reference="DEMO-LEASE-RENEWAL-V2 · metadata only · not downloadable",
            verification_status="PENDING_VERIFICATION",
            replacement_of_id=previous_record.document_validity_id,
            created_by=people["institution"].user_id,
        )
        db.add(current_record)
        add_workflow_event(
            db, case, people["institution"].user_id,
            event_type="DOCUMENT_RENEWAL_SUBMITTED",
            summary="Synthetic lease renewal metadata submitted for officer verification.",
            event_payload={
                "demo_only": True,
                "document_type": "LEASE_DOCUMENT",
                "document_reference": current_record.document_reference,
                "valid_until": current_record.valid_until.isoformat(),
                "verification_status": current_record.verification_status,
            },
        )
        return 2
    return 0


def add_demo_alert(
    db,
    case: WorkflowCase,
    actor: User,
    *,
    event_type: str,
    summary: str,
    payload: dict,
) -> bool:
    existing = db.scalar(
        select(WorkflowEvent).where(
            WorkflowEvent.workflow_case_id == case.workflow_case_id,
            WorkflowEvent.event_type == event_type,
            WorkflowEvent.summary == summary,
        )
    )
    if existing is not None:
        return False
    add_workflow_event(
        db,
        case,
        actor.user_id,
        event_type=event_type,
        summary=summary,
        event_payload={
            "demo_only": True,
            "simulation_code": "PS26262_ROLE_WORKFLOW_WALKTHROUGH",
            "alert_source": "SYNTHETIC_LOCAL_SEED",
            **payload,
        },
    )
    return True


def seed_deadline_alerts(db, cases_by_suffix: dict, people: dict) -> int:
    """Create persistent, explicitly synthetic deadline and escalation alerts."""
    created = 0
    now = datetime.now(UTC)

    for suffix, event_type, actor_key, summary, alert_level in [
        (
            "0004",
            "DEMO_DEADLINE_ALERT",
            "scrutiny",
            "Synthetic alert: the scrutiny stage is past its demonstration service target.",
            "STAGE_OVERDUE",
        ),
        (
            "0005",
            "DEMO_EVC_REMINDER",
            "evc_coordinator",
            "Synthetic alert: EVC coordination is overdue and needs scheduling follow-up.",
            "EVC_OVERDUE",
        ),
    ]:
        _application, case = cases_by_suffix[suffix]
        created += int(add_demo_alert(
            db,
            case,
            people[actor_key],
            event_type=event_type,
            summary=summary,
            payload={
                "alert_level": alert_level,
                "deadline_class": "ADMIN_TARGET",
                "due_at": case.due_at.isoformat() if case.due_at else None,
                "days_overdue": max(0, (now.date() - case.due_at.date()).days) if case.due_at else None,
                "recipient_resolution": "CURRENT_ASSIGNEE_AND_SUPERVISORS",
            },
        ))

    overdue_case = cases_by_suffix["0004"][1]
    created += int(add_demo_alert(
        db,
        overdue_case,
        people["scrutiny"],
        event_type="DEMO_ESCALATION_CREATED",
        summary="Synthetic supervisory escalation created for an overdue scrutiny stage.",
        payload={
            "escalation_level": "SUPERVISORY_REVIEW",
            "trigger_type": "STAGE_OVERDUE",
            "due_at": overdue_case.due_at.isoformat() if overdue_case.due_at else None,
            "recipient_resolution": "REGIONAL_AND_BUREAU_SUPERVISORS",
        },
    ))

    _compliance_application, compliance_case = cases_by_suffix["0009"]
    obligations = db.scalars(
        select(ComplianceObligation).where(
            ComplianceObligation.workflow_case_id == compliance_case.workflow_case_id
        )
    ).all()
    for item in obligations:
        remaining = (item.due_at.date() - now.date()).days
        if remaining < 0:
            event_type = "DEMO_COMPLIANCE_ALERT"
            summary = "Synthetic alert: compliance condition is overdue — " + item.title + "."
            alert_kind = "OBLIGATION_OVERDUE"
        elif remaining <= 15:
            event_type = "DEMO_COMPLIANCE_ALERT"
            summary = "Synthetic reminder: compliance evidence is due soon — " + item.title + "."
            alert_kind = "OBLIGATION_DUE_SOON"
        else:
            continue
        created += int(add_demo_alert(
            db,
            compliance_case,
            people["scrutiny"],
            event_type=event_type,
            summary=summary,
            payload={
                "alert_level": alert_kind,
                "obligation_id": str(item.obligation_id),
                "due_at": item.due_at.isoformat(),
                "days_until_due": remaining,
                "deadline_class": "CASE_ORDER",
                "source_reference": item.source_condition,
            },
        ))

    validity_records = db.scalars(
        select(DocumentValidityRecord).where(
            DocumentValidityRecord.workflow_case_id == compliance_case.workflow_case_id
        )
    ).all()
    for record in validity_records:
        remaining = (record.valid_until - date.today()).days
        if remaining < 0:
            alert_kind = "DOCUMENT_EXPIRED"
            summary = "Synthetic alert: a previous lease validity period has expired; verify its replacement."
        elif remaining <= 30:
            alert_kind = "DOCUMENT_EXPIRY_APPROACHING"
            summary = "Synthetic reminder: lease document validity is approaching expiry."
        else:
            continue
        created += int(add_demo_alert(
            db,
            compliance_case,
            people["scrutiny"],
            event_type="DEMO_DOCUMENT_EXPIRY_ALERT",
            summary=summary,
            payload={
                "alert_level": alert_kind,
                "document_validity_id": str(record.document_validity_id),
                "document_type": record.document_type,
                "valid_until": record.valid_until.isoformat(),
                "days_until_expiry": remaining,
                "verification_status": record.verification_status,
            },
        ))
    return created


def main() -> int:
    require_local_environment()
    password = prompt_demo_password()
    db = SessionLocal()
    try:
        seed_standard_references(db)
        institution, team, people = seed_identity(db, password)
        created_cases = 0
        existing_cases = 0
        applications_by_suffix = {}
        for spec in SCENARIOS:
            application, case, created = seed_application_case(db, institution, team, people, spec)
            applications_by_suffix[spec["suffix"]] = (application, case)
            created_cases += int(created)
            existing_cases += int(not created)

        compliance_application, compliance_case = applications_by_suffix["0009"]
        obligations_created = seed_obligations(db, compliance_application, compliance_case, people)
        validity_created = seed_document_validity(db, compliance_application, compliance_case, institution, people)
        alerts_created = seed_deadline_alerts(db, applications_by_suffix, people)

        db.commit()
        print("\nAIC-Flow local demo data is ready.")
        print("All cases, route snapshots, events, obligations and validity dates are synthetic.")
        print("No APH route was published and no statutory approval or rejection was generated.")
        print(f"Created workflow cases: {created_cases}")
        print(f"Existing workflow cases left unchanged: {existing_cases}")
        print(f"Created compliance obligations: {obligations_created}")
        print(f"Created document-validity metadata records: {validity_created}")
        print(f"Created synthetic deadline and escalation alerts: {alerts_created}")
        print(f"Institution: {institution.institution_name} ({DEMO_INSTITUTION_CODE})")
        print(f"Operational team: {team.team_name}")
        print("\nLocal demo accounts (same password entered at the prompt for newly created accounts):")
        for key, email, _name, _role in ROLE_ACCOUNTS:
            print(f"  {key:16} {email}")
        print("\nThe lease document versions are metadata-only demo references and cannot be downloaded.")
        print("To upload actual local demo files, use the Institution Document Centre or the obligation evidence action.")
        return 0
    except Exception as exc:  # noqa: BLE001
        db.rollback()
        print(f"ERROR: local demo seeding failed; transaction rolled back: {exc}", file=sys.stderr)
        return 1
    finally:
        db.close()


if __name__ == "__main__":
    raise SystemExit(main())

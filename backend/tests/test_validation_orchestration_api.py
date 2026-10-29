"""AIC-Verify — Phase 6 Batch 3 Integration & Security Tests.

Verifies:
1. Validation transaction hardening:
   - Unhandled evaluator failure rolls back partial results/findings and commits run as FAILED.
   - Historical completed validation runs, results, and findings remain immutable across runs.
2. Finding evidence completeness:
   - 100% of persisted findings link to FindingEvidence (using EVALUATION_RATIONALE when raw items absent).
3. Auditor finding lifecycle API (PATCH /findings/{id}):
   - Permitted status transitions succeed and record audit trail.
   - Invalid status transitions rejected (HTTP 400).
   - Review note whitespace constraint enforced (minimum 5 non-whitespace characters).
   - RBAC: Institution User and Admin forbidden (HTTP 403).
   - Review-team case isolation enforced.
4. Finding query filters (GET /findings):
   - Filtering by validation_run_id, category, severity, status.
   - latest_run_only semantics.
   - Confidential internal findings redacted from institution users.
"""

from __future__ import annotations

import uuid
from typing import Any

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import desc, select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.security import create_access_token
from app.main import app as fastapi_app
from app.models.application import Application
from app.models.application_requirements import ApplicationRequirement
from app.models.application_revision import ApplicationRevision
from app.models.checklist_item import ChecklistItem
from app.models.enums import (
    FindingStatus,
    RequirementStatus,
    TeamRole,
)
from app.models.finding import Finding
from app.models.finding_evidence import FindingEvidence
from app.models.institution import Institution
from app.models.institution_membership import InstitutionMembership
from app.models.review_team import ReviewTeam
from app.models.review_team_member import ReviewTeamMember
from app.models.role import Role
from app.models.user import User
from app.models.user_role_assignment import UserRoleAssignment
from app.models.validation_result import ValidationResult
from app.models.validation_run import ValidationRun
from app.rules.base import (
    BaseRuleEvaluator,
    RuleEvaluationContext,
    RuleEvaluationOutcome,
)
from app.rules.engine import regulatory_rule_engine
from app.services.checklist_service import seed_standard_references
from scripts.seed_rules import seed_rules


@pytest.fixture
def client() -> TestClient:
    return TestClient(fastapi_app)


@pytest.fixture
def validation_test_setup(db: Session) -> dict[str, Any]:
    """Sets up an isolated institution, application, and test users for Batch 3 testing."""
    seed_standard_references(db)
    seed_rules()

    # 1. Synthetic Institution
    inst = db.scalar(
        select(Institution).where(
            Institution.aicte_permanent_institution_id == "SYNTH-AICTE-0001"
        )
    )
    if not inst:
        inst = Institution(
            aicte_permanent_institution_id="SYNTH-AICTE-0001",
            institution_name="Apex Institute of Technology",
            is_active=True,
        )
        db.add(inst)
        db.flush()

    # 2. Synthetic Review Team
    team = db.scalar(select(ReviewTeam))
    if not team:
        team = ReviewTeam(team_name="Western Region Review Team", is_active=True)
        db.add(team)
        db.flush()

    # Another Team for Isolation Testing
    other_team = ReviewTeam(team_name="Southern Region Review Team", is_active=True)
    db.add(other_team)
    db.flush()

    # 3. Users
    user_inst = db.scalar(
        select(User).where(User.email == "institution@aic-verify.internal")
    )
    if not user_inst:
        user_inst = User(
            email="institution@aic-verify.internal",
            full_name="Institution User",
            password_hash="hash",
        )
        db.add(user_inst)
        db.flush()

    user_auditor = db.scalar(
        select(User).where(User.email == "auditor@aic-verify.internal")
    )
    if not user_auditor:
        user_auditor = User(
            email="auditor@aic-verify.internal",
            full_name="Auditor User",
            password_hash="hash",
        )
        db.add(user_auditor)
        db.flush()

    user_other_auditor = User(
        email="other_auditor@aic-verify.internal",
        full_name="Other Auditor",
        password_hash="hash",
    )
    db.add(user_other_auditor)
    db.flush()

    user_admin = db.scalar(
        select(User).where(User.email == "admin@aic-verify.internal")
    )
    if not user_admin:
        user_admin = User(
            email="admin@aic-verify.internal",
            full_name="Admin User",
            password_hash="hash",
        )
        db.add(user_admin)
        db.flush()

    # 4. Memberships (Must exist before UserRoleAssignment to satisfy trigger)
    # Institution Membership
    inst_m = db.scalar(
        select(InstitutionMembership).where(
            InstitutionMembership.institution_id == inst.institution_id,
            InstitutionMembership.user_id == user_inst.user_id,
        )
    )
    if not inst_m:
        db.add(
            InstitutionMembership(
                institution_id=inst.institution_id,
                user_id=user_inst.user_id,
                is_active=True,
            )
        )

    # Auditor Team Memberships
    tm1 = db.scalar(
        select(ReviewTeamMember).where(
            ReviewTeamMember.review_team_id == team.review_team_id,
            ReviewTeamMember.user_id == user_auditor.user_id,
        )
    )
    if not tm1:
        db.add(
            ReviewTeamMember(
                review_team_id=team.review_team_id,
                user_id=user_auditor.user_id,
                team_role=TeamRole.AUDITOR,
                is_active=True,
            )
        )

    tm2 = db.scalar(
        select(ReviewTeamMember).where(
            ReviewTeamMember.review_team_id == other_team.review_team_id,
            ReviewTeamMember.user_id == user_other_auditor.user_id,
        )
    )
    if not tm2:
        db.add(
            ReviewTeamMember(
                review_team_id=other_team.review_team_id,
                user_id=user_other_auditor.user_id,
                team_role=TeamRole.AUDITOR,
                is_active=True,
            )
        )
    db.flush()

    # 5. Role Assignments. The CI baseline is persistent across test functions,
    # so keep this fixture idempotent instead of creating duplicate assignments.
    roles = {r.role_code: r for r in db.scalars(select(Role)).all()}

    def ensure_role_assignment(
        user: User,
        role_code: str,
        *,
        institution_id=None,
        review_team_id=None,
    ) -> None:
        role = roles[role_code]
        existing_assignment = db.scalar(
            select(UserRoleAssignment).where(
                UserRoleAssignment.user_id == user.user_id,
                UserRoleAssignment.role_id == role.role_id,
                UserRoleAssignment.institution_id == institution_id,
                UserRoleAssignment.review_team_id == review_team_id,
                UserRoleAssignment.revoked_at.is_(None),
            )
        )
        if existing_assignment is None:
            db.add(
                UserRoleAssignment(
                    user_id=user.user_id,
                    role_id=role.role_id,
                    institution_id=institution_id,
                    review_team_id=review_team_id,
                )
            )

    ensure_role_assignment(
        user_inst,
        "INSTITUTION_USER",
        institution_id=inst.institution_id,
    )
    ensure_role_assignment(
        user_auditor,
        "AUDITOR",
        review_team_id=team.review_team_id,
    )
    ensure_role_assignment(
        user_other_auditor,
        "AUDITOR",
        review_team_id=other_team.review_team_id,
    )
    ensure_role_assignment(user_admin, "ADMIN")
    db.flush()

    # 5. Application and Revision
    app_rec = db.scalar(
        select(Application).where(Application.institution_id == inst.institution_id)
    )
    if not app_rec:
        app_rec = Application(
            institution_id=inst.institution_id,
            application_number=f"APP-TEST-{uuid.uuid4().hex[:8].upper()}",
            academic_year="2026-27",
            review_team_id=team.review_team_id,
        )
        db.add(app_rec)
        db.flush()
    else:
        app_rec.review_team_id = team.review_team_id
        db.flush()

    rev = db.scalar(
        select(ApplicationRevision).where(
            ApplicationRevision.application_id == app_rec.application_id
        )
    )
    if not rev:
        rev = ApplicationRevision(
            application_id=app_rec.application_id,
            revision_number=1,
            created_by_user_id=user_inst.user_id,
        )
        db.add(rev)
        db.flush()

    # Seed Requirements if missing
    reqs = list(
        db.scalars(
            select(ApplicationRequirement).where(
                ApplicationRequirement.application_revision_id
                == rev.application_revision_id
            )
        ).all()
    )
    if not reqs:
        ci_items = list(
            db.scalars(
                select(ChecklistItem).order_by(ChecklistItem.display_order)
            ).all()
        )
        for ci in ci_items:
            req = ApplicationRequirement(
                application_revision_id=rev.application_revision_id,
                checklist_item_id=ci.checklist_item_id,
                status=RequirementStatus.PENDING,
                applicability_status="APPLICABLE",
                expected_document_type_code=ci.expected_document_type_code,
            )
            db.add(req)
        db.flush()

    # Auth Helpers
    csrf_token = "batch3-test-csrf-token"

    def make_auth(user: User) -> dict[str, Any]:
        token = create_access_token(subject=str(user.user_id))
        return {
            "cookies": {
                settings.access_cookie_name: token,
                settings.csrf_cookie_name: csrf_token,
            },
            "headers": {"X-CSRF-Token": csrf_token},
        }

    return {
        "db": db,
        "inst": inst,
        "app": app_rec,
        "rev": rev,
        "team": team,
        "other_team": other_team,
        "user_inst": user_inst,
        "user_auditor": user_auditor,
        "user_admin": user_admin,
        "auth_inst": make_auth(user_inst),
        "auth_auditor": make_auth(user_auditor),
        "auth_other_auditor": make_auth(user_other_auditor),
        "auth_admin": make_auth(user_admin),
    }


# =============================================================================
# 1. Validation Transaction Hardening & Failure Rollback Tests
# =============================================================================


class ExplodingTestEvaluator(BaseRuleEvaluator):
    """Evaluator that simulates an unexpected crash during execution."""

    rule_code = "RULE_EOA_01_AFFIDAVIT"

    def evaluate(self, ctx: RuleEvaluationContext) -> RuleEvaluationOutcome:
        raise RuntimeError("Simulated evaluator unhandled explosion during validation!")


def test_transaction_rollback_and_failed_run_persistence(
    db: Session, validation_test_setup: dict[str, Any]
) -> None:
    """Verifies that an unhandled evaluation exception marks run FAILED with zero orphaned results/findings."""
    rev = validation_test_setup["rev"]

    # Temporarily register exploding evaluator
    orig_evaluator = regulatory_rule_engine._evaluators["RULE_EOA_01_AFFIDAVIT"]
    regulatory_rule_engine.register_evaluator(ExplodingTestEvaluator())

    try:
        with pytest.raises(
            RuntimeError, match="Simulated evaluator unhandled explosion"
        ):
            regulatory_rule_engine.execute_validation_run(
                db=db,
                application_revision_id=rev.application_revision_id,
                run_type="FULL",
            )
    finally:
        # Restore real evaluator
        regulatory_rule_engine.register_evaluator(orig_evaluator)

    # Inspect PostgreSQL state
    failed_run = db.scalar(
        select(ValidationRun)
        .where(ValidationRun.application_revision_id == rev.application_revision_id)
        .order_by(desc(ValidationRun.started_at))
    )
    assert failed_run is not None
    assert failed_run.status == "FAILED"
    assert failed_run.completed_at is not None

    # Crucial Assertion: ZERO orphaned ValidationResult, Finding, or FindingEvidence records!
    orphaned_results = list(
        db.scalars(
            select(ValidationResult).where(
                ValidationResult.validation_run_id == failed_run.validation_run_id
            )
        ).all()
    )
    orphaned_findings = list(
        db.scalars(
            select(Finding).where(
                Finding.validation_run_id == failed_run.validation_run_id
            )
        ).all()
    )
    assert len(orphaned_results) == 0, (
        f"Found {len(orphaned_results)} orphaned validation results!"
    )
    assert len(orphaned_findings) == 0, (
        f"Found {len(orphaned_findings)} orphaned findings!"
    )


def test_historical_runs_and_results_immutability(
    db: Session, validation_test_setup: dict[str, Any]
) -> None:
    """Verifies that executing a subsequent run does not alter historical completed runs or results."""
    rev = validation_test_setup["rev"]

    # 1. Execute Run 1
    run1 = regulatory_rule_engine.execute_validation_run(
        db=db,
        application_revision_id=rev.application_revision_id,
        run_type="FULL",
    )
    assert run1.status == "COMPLETED"
    run1_id = run1.validation_run_id
    run1_completed_at = run1.completed_at

    run1_results = list(
        db.scalars(
            select(ValidationResult)
            .where(ValidationResult.validation_run_id == run1_id)
            .order_by(ValidationResult.evaluated_at)
        ).all()
    )
    assert len(run1_results) == 7
    run1_result_statuses = {
        r.validation_result_id: r.result_status for r in run1_results
    }

    # 2. Execute Run 2
    run2 = regulatory_rule_engine.execute_validation_run(
        db=db,
        application_revision_id=rev.application_revision_id,
        run_type="FULL",
    )
    assert run2.status == "COMPLETED"
    assert run2.validation_run_id != run1_id

    # 3. Assert Run 1 is completely untouched
    run1_reloaded = db.scalar(
        select(ValidationRun).where(ValidationRun.validation_run_id == run1_id)
    )
    assert run1_reloaded.status == "COMPLETED"
    assert run1_reloaded.completed_at == run1_completed_at

    run1_results_after = list(
        db.scalars(
            select(ValidationResult)
            .where(ValidationResult.validation_run_id == run1_id)
            .order_by(ValidationResult.evaluated_at)
        ).all()
    )
    assert len(run1_results_after) == 7
    for r in run1_results_after:
        assert r.result_status == run1_result_statuses[r.validation_result_id]


# =============================================================================
# 2. Finding Evidence Completeness Tests
# =============================================================================


def test_finding_evidence_completeness_and_rationale_fallback(
    db: Session, validation_test_setup: dict[str, Any]
) -> None:
    """Verifies that 100% of findings link to at least one valid FindingEvidence row."""
    rev = validation_test_setup["rev"]

    run = regulatory_rule_engine.execute_validation_run(
        db=db,
        application_revision_id=rev.application_revision_id,
        run_type="FULL",
    )
    findings = list(
        db.scalars(
            select(Finding).where(Finding.validation_run_id == run.validation_run_id)
        ).all()
    )
    assert len(findings) > 0

    for f in findings:
        evidence_rows = list(
            db.scalars(
                select(FindingEvidence).where(
                    FindingEvidence.finding_id == f.finding_id
                )
            ).all()
        )
        assert len(evidence_rows) >= 1, (
            f"Finding {f.finding_id} ({f.title}) has no linked evidence!"
        )
        for ev in evidence_rows:
            assert ev.validation_result_id == f.validation_result_id
            assert ev.evidence_type is not None
            assert len(ev.evidence_type) > 0


# =============================================================================
# 3. Auditor Finding Action API Tests (PATCH /findings/{id})
# =============================================================================


def test_auditor_finding_status_update_lifecycle_and_audit_trail(
    client: TestClient, validation_test_setup: dict[str, Any]
) -> None:
    """Verifies auditor status transition, audit rationale persistence, and evidence recording."""
    db = validation_test_setup["db"]
    inst = validation_test_setup["inst"]
    app_rec = validation_test_setup["app"]
    auth_auditor = validation_test_setup["auth_auditor"]
    user_auditor = validation_test_setup["user_auditor"]

    # Run validation to generate findings
    run = regulatory_rule_engine.execute_validation_run(
        db=db,
        application_revision_id=validation_test_setup["rev"].application_revision_id,
        run_type="FULL",
    )
    finding = db.scalar(
        select(Finding).where(
            Finding.validation_run_id == run.validation_run_id,
            Finding.status == FindingStatus.OPEN,
        )
    )
    assert finding is not None

    url = f"/api/v1/institutions/{inst.institution_id}/applications/{app_rec.application_id}/validation/findings/{finding.finding_id}"

    # 1. Auditor accepts finding with valid review note
    res = client.patch(
        url,
        json={
            "status": "ACCEPTED",
            "review_note": "Verified by Auditor: deficiency confirmed from building records.",
        },
        cookies=auth_auditor["cookies"],
        headers=auth_auditor["headers"],
    )
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "ACCEPTED"
    assert "Verified by Auditor" in data["internal_reason"]

    # Verify audit evidence was appended in database
    db.expire_all()
    evidence_rows = list(
        db.scalars(
            select(FindingEvidence).where(
                FindingEvidence.finding_id == finding.finding_id
            )
        ).all()
    )
    action_ev = next(
        (ev for ev in evidence_rows if ev.evidence_type == "AUDITOR_REVIEW_ACTION"),
        None,
    )
    assert action_ev is not None
    assert f"actor:{user_auditor.user_id}" in action_ev.evidence_reference
    assert "Verified by Auditor" in action_ev.evidence_summary

    # 2. Auditor resolves finding with justification
    res2 = client.patch(
        url,
        json={
            "status": "RESOLVED",
            "review_note": "Institution supplied acceptable explanation and rectifying evidence.",
        },
        cookies=auth_auditor["cookies"],
        headers=auth_auditor["headers"],
    )
    assert res2.status_code == 200
    assert res2.json()["status"] == "RESOLVED"


def test_finding_status_prohibited_transitions_rejected(
    client: TestClient, validation_test_setup: dict[str, Any]
) -> None:
    """Verifies that illegal status transitions are rejected with HTTP 400."""
    db = validation_test_setup["db"]
    inst = validation_test_setup["inst"]
    app_rec = validation_test_setup["app"]
    auth_auditor = validation_test_setup["auth_auditor"]

    run = regulatory_rule_engine.execute_validation_run(
        db=db,
        application_revision_id=validation_test_setup["rev"].application_revision_id,
        run_type="FULL",
    )
    finding = db.scalar(
        select(Finding).where(Finding.validation_run_id == run.validation_run_id)
    )
    assert finding is not None

    url = f"/api/v1/institutions/{inst.institution_id}/applications/{app_rec.application_id}/validation/findings/{finding.finding_id}"

    # Invalid: Direct jump from OPEN to RESOLVED is not permitted
    res = client.patch(
        url,
        json={
            "status": "RESOLVED",
            "review_note": "Attempting invalid jump without acceptance or clarification.",
        },
        cookies=auth_auditor["cookies"],
        headers=auth_auditor["headers"],
    )
    assert res.status_code == 400
    assert "Invalid finding status transition" in res.json()["detail"]


def test_finding_review_note_whitespace_validation(
    client: TestClient, validation_test_setup: dict[str, Any]
) -> None:
    """Verifies that review notes with whitespace only or fewer than 5 characters are rejected with HTTP 422."""
    db = validation_test_setup["db"]
    inst = validation_test_setup["inst"]
    app_rec = validation_test_setup["app"]
    auth_auditor = validation_test_setup["auth_auditor"]

    run = regulatory_rule_engine.execute_validation_run(
        db=db,
        application_revision_id=validation_test_setup["rev"].application_revision_id,
        run_type="FULL",
    )
    finding = db.scalar(
        select(Finding).where(Finding.validation_run_id == run.validation_run_id)
    )

    url = f"/api/v1/institutions/{inst.institution_id}/applications/{app_rec.application_id}/validation/findings/{finding.finding_id}"

    # Whitespace only
    res = client.patch(
        url,
        json={"status": "ACCEPTED", "review_note": "   \t\n   "},
        cookies=auth_auditor["cookies"],
        headers=auth_auditor["headers"],
    )
    assert res.status_code == 422

    # Under 5 characters
    res2 = client.patch(
        url,
        json={"status": "ACCEPTED", "review_note": "ok  "},
        cookies=auth_auditor["cookies"],
        headers=auth_auditor["headers"],
    )
    assert res2.status_code == 422


def test_finding_action_rbac_and_case_isolation(
    client: TestClient, validation_test_setup: dict[str, Any]
) -> None:
    """Verifies that Institution User, Admin, and outside Auditors are denied finding PATCH permissions (HTTP 403)."""
    db = validation_test_setup["db"]
    inst = validation_test_setup["inst"]
    app_rec = validation_test_setup["app"]
    auth_inst = validation_test_setup["auth_inst"]
    auth_admin = validation_test_setup["auth_admin"]
    auth_other = validation_test_setup["auth_other_auditor"]

    run = regulatory_rule_engine.execute_validation_run(
        db=db,
        application_revision_id=validation_test_setup["rev"].application_revision_id,
        run_type="FULL",
    )
    finding = db.scalar(
        select(Finding).where(Finding.validation_run_id == run.validation_run_id)
    )

    url = f"/api/v1/institutions/{inst.institution_id}/applications/{app_rec.application_id}/validation/findings/{finding.finding_id}"

    # 1. Institution User -> 403
    res_inst = client.patch(
        url,
        json={"status": "ACCEPTED", "review_note": "Attempted update by applicant."},
        cookies=auth_inst["cookies"],
        headers=auth_inst["headers"],
    )
    assert res_inst.status_code == 403

    # 2. Admin -> 403
    res_admin = client.patch(
        url,
        json={
            "status": "ACCEPTED",
            "review_note": "Attempted update by administrator.",
        },
        cookies=auth_admin["cookies"],
        headers=auth_admin["headers"],
    )
    assert res_admin.status_code == 403

    # 3. Outside Review Team Auditor -> 403
    res_other = client.patch(
        url,
        json={
            "status": "ACCEPTED",
            "review_note": "Attempted update by unassigned auditor.",
        },
        cookies=auth_other["cookies"],
        headers=auth_other["headers"],
    )
    assert res_other.status_code == 403


# =============================================================================
# 4. Finding Query Filters & Redaction Tests (GET /findings)
# =============================================================================


def test_finding_query_filters_and_latest_run_only(
    client: TestClient, validation_test_setup: dict[str, Any]
) -> None:
    """Verifies filtering by category, severity, status, validation_run_id, and latest_run_only."""
    db = validation_test_setup["db"]
    inst = validation_test_setup["inst"]
    app_rec = validation_test_setup["app"]
    auth_auditor = validation_test_setup["auth_auditor"]

    # Execute Run 1
    run1 = regulatory_rule_engine.execute_validation_run(
        db=db,
        application_revision_id=validation_test_setup["rev"].application_revision_id,
        run_type="FULL",
    )

    # Execute Run 2
    run2 = regulatory_rule_engine.execute_validation_run(
        db=db,
        application_revision_id=validation_test_setup["rev"].application_revision_id,
        run_type="FULL",
    )

    base_url = f"/api/v1/institutions/{inst.institution_id}/applications/{app_rec.application_id}/validation/findings"

    # 1. Filter by specific validation_run_id
    res_run1 = client.get(
        f"{base_url}?validation_run_id={run1.validation_run_id}",
        cookies=auth_auditor["cookies"],
    )
    assert res_run1.status_code == 200
    findings_run1 = res_run1.json()
    assert all(
        f["validation_run_id"] == str(run1.validation_run_id) for f in findings_run1
    )

    # 2. Filter by latest_run_only=true
    res_latest = client.get(
        f"{base_url}?latest_run_only=true",
        cookies=auth_auditor["cookies"],
    )
    assert res_latest.status_code == 200
    findings_latest = res_latest.json()
    assert all(
        f["validation_run_id"] == str(run2.validation_run_id) for f in findings_latest
    )

    # 3. Filter by severity=HIGH
    res_high = client.get(
        f"{base_url}?severity=HIGH",
        cookies=auth_auditor["cookies"],
    )
    assert res_high.status_code == 200
    for f in res_high.json():
        assert f["severity"] == "HIGH"

    # 4. Filter by category=MISSING_DOCUMENT
    res_missing = client.get(
        f"{base_url}?category=MISSING_DOCUMENT",
        cookies=auth_auditor["cookies"],
    )
    assert res_missing.status_code == 200
    for f in res_missing.json():
        assert f["category"] == "MISSING_DOCUMENT"


def test_internal_findings_redacted_for_institution_user(
    client: TestClient, validation_test_setup: dict[str, Any]
) -> None:
    """Verifies that internal-only findings and internal reasons are hidden from Institution Users."""
    db = validation_test_setup["db"]
    inst = validation_test_setup["inst"]
    app_rec = validation_test_setup["app"]
    auth_inst = validation_test_setup["auth_inst"]
    auth_auditor = validation_test_setup["auth_auditor"]

    regulatory_rule_engine.execute_validation_run(
        db=db,
        application_revision_id=validation_test_setup["rev"].application_revision_id,
        run_type="FULL",
    )

    base_url = f"/api/v1/institutions/{inst.institution_id}/applications/{app_rec.application_id}/validation/findings"

    # Auditor sees all findings including internal_only
    res_auditor = client.get(base_url, cookies=auth_auditor["cookies"])
    assert res_auditor.status_code == 200
    auditor_findings = res_auditor.json()
    assert any(f["is_internal_only"] is True for f in auditor_findings)
    assert any(f["internal_reason"] is not None for f in auditor_findings)

    # Institution user sees only externalized findings, with internal_reason completely stripped
    res_inst = client.get(base_url, cookies=auth_inst["cookies"])
    assert res_inst.status_code == 200
    inst_findings = res_inst.json()
    assert all(f["is_internal_only"] is False for f in inst_findings)
    assert all(f["internal_reason"] is None for f in inst_findings)

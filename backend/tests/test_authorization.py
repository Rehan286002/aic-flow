import secrets
import sys
import uuid
from datetime import UTC, datetime
from pathlib import Path

# Ensure backend root is in sys.path for pytest discovery
BACKEND_DIR = str(Path(__file__).resolve().parents[1])
if BACKEND_DIR not in sys.path:
    sys.path.insert(0, BACKEND_DIR)

from typing import Annotated

import pytest
from fastapi import APIRouter, Depends
from fastapi.testclient import TestClient
from pydantic import SecretStr

from app.api.deps import (
    RoleAssignmentContext,
    get_active_role_assignments,
    require_admin,
    require_institution_access,
    require_review_team_access,
)
from app.core.config import settings
from app.core.security import create_access_token, hash_password
from app.db.session import SessionLocal
from app.main import app
from app.models.enums import TeamRole, UserStatus
from app.models.institution import Institution
from app.models.institution_membership import InstitutionMembership
from app.models.review_team import ReviewTeam
from app.models.review_team_member import ReviewTeamMember
from app.models.user import User
from app.models.user_role_assignment import UserRoleAssignment

# Helper test router to verify dependency injection against live HTTP requests
rbac_test_router = APIRouter(prefix="/test-rbac", tags=["test-rbac"])


@rbac_test_router.get("/admin-only")
def admin_only_endpoint(
    _: Annotated[list[RoleAssignmentContext], Depends(require_admin)],
):
    return {"access": "granted", "role": "ADMIN"}


@rbac_test_router.get("/institution/{institution_id}")
def institution_scoped_endpoint(
    ctx: Annotated[RoleAssignmentContext, Depends(require_institution_access)],
):
    return {"access": "granted", "institution_id": str(ctx.institution_id)}


@rbac_test_router.get("/review-team/{review_team_id}")
def review_team_scoped_endpoint(
    ctx: Annotated[RoleAssignmentContext, Depends(require_review_team_access)],
):
    return {"access": "granted", "review_team_id": str(ctx.review_team_id)}


@rbac_test_router.get("/missing-institution-path-param")
def missing_institution_path_param_endpoint(
    ctx: Annotated[RoleAssignmentContext, Depends(require_institution_access)],
):
    return {"access": "granted", "institution_id": str(ctx.institution_id)}


@rbac_test_router.get("/missing-review-team-path-param")
def missing_review_team_path_param_endpoint(
    ctx: Annotated[RoleAssignmentContext, Depends(require_review_team_access)],
):
    return {"access": "granted", "review_team_id": str(ctx.review_team_id)}


# Mount test router on app once
if not any(r.path.startswith("/test-rbac") for r in app.routes if hasattr(r, "path")):
    app.include_router(rbac_test_router)


@pytest.fixture(autouse=True)
def configure_test_security(monkeypatch):
    """Configure ephemeral JWT secret and cookies for tests."""
    test_secret = secrets.token_urlsafe(32)
    monkeypatch.setattr(settings, "jwt_secret_key", SecretStr(test_secret))
    monkeypatch.setattr(settings, "cookie_secure", False)
    return test_secret


@pytest.fixture
def client():
    """Provide a TestClient for testing HTTP authorization endpoints."""
    return TestClient(app)


# ==============================================================================
# Helper Factories with Strict Primary-Key Tracking and Ordered Cleanup
# ==============================================================================


@pytest.fixture
def rbac_env():
    """Manage database test entities with strict ID tracking and ordered foreign-key cleanup.

    Deletion order ensures dependent records are deleted before parent records:
    1. UserRoleAssignment
    2. InstitutionMembership / ReviewTeamMember
    3. Institution / ReviewTeam
    4. User
    """
    db = SessionLocal()
    created_assignment_ids = []
    created_membership_ids = []
    created_team_member_ids = []
    created_institution_ids = []
    created_team_ids = []
    created_user_ids = []

    class Factory:
        def create_user(
            self, name_prefix="Test User", status=UserStatus.ACTIVE
        ) -> User:
            user_id = uuid.uuid4()
            u = User(
                user_id=user_id,
                full_name=f"{name_prefix} {user_id.hex[:6]}",
                email=f"rbac.{user_id.hex[:8]}@test.aic-verify.internal",
                password_hash=hash_password("SecurePassword#2026"),
                status=status,
            )
            db.add(u)
            db.commit()
            db.refresh(u)
            created_user_ids.append(user_id)
            return u

        def create_institution(self, name_prefix="Institution") -> Institution:
            inst_id = uuid.uuid4()
            inst = Institution(
                institution_id=inst_id,
                aicte_permanent_institution_id=f"AICTE-{inst_id.hex[:8].upper()}",
                institution_name=f"{name_prefix} {inst_id.hex[:6]}",
                is_active=True,
            )
            db.add(inst)
            db.commit()
            db.refresh(inst)
            created_institution_ids.append(inst_id)
            return inst

        def create_review_team(self, name_prefix="Team") -> ReviewTeam:
            team_id = uuid.uuid4()
            team = ReviewTeam(
                review_team_id=team_id,
                team_name=f"{name_prefix} {team_id.hex[:6]}",
                is_active=True,
            )
            db.add(team)
            db.commit()
            db.refresh(team)
            created_team_ids.append(team_id)
            return team

        def add_institution_membership(
            self, institution_id: uuid.UUID, user_id: uuid.UUID, is_active=True
        ) -> InstitutionMembership:
            m_id = uuid.uuid4()
            m = InstitutionMembership(
                institution_membership_id=m_id,
                institution_id=institution_id,
                user_id=user_id,
                is_active=is_active,
            )
            db.add(m)
            db.commit()
            db.refresh(m)
            created_membership_ids.append(m_id)
            return m

        def add_review_team_member(
            self,
            review_team_id: uuid.UUID,
            user_id: uuid.UUID,
            team_role: TeamRole,
            is_active=True,
        ) -> ReviewTeamMember:
            tm_id = uuid.uuid4()
            tm = ReviewTeamMember(
                review_team_member_id=tm_id,
                review_team_id=review_team_id,
                user_id=user_id,
                team_role=team_role,
                is_active=is_active,
            )
            db.add(tm)
            db.commit()
            db.refresh(tm)
            created_team_member_ids.append(tm_id)
            return tm

        def assign_role(
            self,
            user_id: uuid.UUID,
            role_id: int,
            institution_id: uuid.UUID | None = None,
            review_team_id: uuid.UUID | None = None,
            revoked=False,
        ) -> UserRoleAssignment:
            a_id = uuid.uuid4()
            assignment = UserRoleAssignment(
                user_role_assignment_id=a_id,
                user_id=user_id,
                role_id=role_id,
                institution_id=institution_id,
                review_team_id=review_team_id,
                revoked_at=datetime.now(UTC) if revoked else None,
            )
            db.add(assignment)
            db.commit()
            db.refresh(assignment)
            created_assignment_ids.append(a_id)
            return assignment

    factory = Factory()
    try:
        yield factory, db
    finally:
        # Ordered teardown: dependents before parents
        cleanup_db = SessionLocal()
        try:
            # 1. Delete UserRoleAssignment
            for aid in created_assignment_ids:
                row = cleanup_db.get(UserRoleAssignment, aid)
                if row:
                    cleanup_db.delete(row)
            cleanup_db.commit()

            # 2. Delete InstitutionMembership & ReviewTeamMember
            for mid in created_membership_ids:
                row = cleanup_db.get(InstitutionMembership, mid)
                if row:
                    cleanup_db.delete(row)
            for tmid in created_team_member_ids:
                row = cleanup_db.get(ReviewTeamMember, tmid)
                if row:
                    cleanup_db.delete(row)
            cleanup_db.commit()

            # 3. Delete Institution & ReviewTeam
            for iid in created_institution_ids:
                row = cleanup_db.get(Institution, iid)
                if row:
                    cleanup_db.delete(row)
            for tid in created_team_ids:
                row = cleanup_db.get(ReviewTeam, tid)
                if row:
                    cleanup_db.delete(row)
            cleanup_db.commit()

            # 4. Delete User
            for uid in created_user_ids:
                row = cleanup_db.get(User, uid)
                if row:
                    cleanup_db.delete(row)
            cleanup_db.commit()

            # Verify that each specific test-created ID is completely gone
            for aid in created_assignment_ids:
                assert cleanup_db.get(UserRoleAssignment, aid) is None
            for mid in created_membership_ids:
                assert cleanup_db.get(InstitutionMembership, mid) is None
            for tmid in created_team_member_ids:
                assert cleanup_db.get(ReviewTeamMember, tmid) is None
            for iid in created_institution_ids:
                assert cleanup_db.get(Institution, iid) is None
            for tid in created_team_ids:
                assert cleanup_db.get(ReviewTeam, tid) is None
            for uid in created_user_ids:
                assert cleanup_db.get(User, uid) is None
        finally:
            cleanup_db.close()
            db.close()


# ==============================================================================
# Focused Authorization Tests (Requirements 1 - 16)
# ==============================================================================


def test_institution_user_can_access_own_institution_scope(rbac_env, client):
    """1. Verify that Institution User can access their own institution scope."""
    factory, _ = rbac_env
    user = factory.create_user("InstUser")
    inst = factory.create_institution("College A")
    factory.add_institution_membership(
        inst.institution_id, user.user_id, is_active=True
    )
    factory.assign_role(user.user_id, role_id=1, institution_id=inst.institution_id)

    token = create_access_token(subject=user.user_id)
    client.cookies.set(settings.access_cookie_name, token)

    response = client.get(f"/test-rbac/institution/{inst.institution_id}")
    assert response.status_code == 200
    assert response.json()["access"] == "granted"
    assert response.json()["institution_id"] == str(inst.institution_id)


def test_institution_user_cannot_access_another_institution(rbac_env, client):
    """2. Verify that Institution User cannot access another institution (cross-institution blocked)."""
    factory, _ = rbac_env
    user = factory.create_user("InstUser")
    inst_a = factory.create_institution("College A")
    inst_b = factory.create_institution("College B")
    factory.add_institution_membership(
        inst_a.institution_id, user.user_id, is_active=True
    )
    factory.assign_role(user.user_id, role_id=1, institution_id=inst_a.institution_id)

    token = create_access_token(subject=user.user_id)
    client.cookies.set(settings.access_cookie_name, token)

    # Attempt to access College B
    response = client.get(f"/test-rbac/institution/{inst_b.institution_id}")
    assert response.status_code == 403
    assert (
        f"access denied for institution {inst_b.institution_id}"
        in response.json()["detail"]
    )


def test_institution_access_rejected_after_membership_becomes_inactive(
    rbac_env, client
):
    """3. Verify that institution access is rejected if membership is no longer active."""
    factory, db = rbac_env
    user = factory.create_user("InstUser")
    inst = factory.create_institution("College Inactive")
    membership = factory.add_institution_membership(
        inst.institution_id, user.user_id, is_active=True
    )
    factory.assign_role(user.user_id, role_id=1, institution_id=inst.institution_id)

    # Deactivate the membership post-assignment
    membership.is_active = False
    db.commit()

    token = create_access_token(subject=user.user_id)
    client.cookies.set(settings.access_cookie_name, token)

    response = client.get(f"/test-rbac/institution/{inst.institution_id}")
    assert response.status_code == 403


def test_revoked_institution_role_assignment_rejected(rbac_env, client):
    """4. Verify that revoked role assignment is excluded and denied."""
    factory, _ = rbac_env
    user = factory.create_user("InstUser")
    inst = factory.create_institution("College Revoked")
    factory.add_institution_membership(
        inst.institution_id, user.user_id, is_active=True
    )
    factory.assign_role(
        user.user_id, role_id=1, institution_id=inst.institution_id, revoked=True
    )

    token = create_access_token(subject=user.user_id)
    client.cookies.set(settings.access_cookie_name, token)

    response = client.get(f"/test-rbac/institution/{inst.institution_id}")
    assert response.status_code == 403


def test_auditor_can_access_own_review_team_scope(rbac_env, client):
    """5. Verify that Auditor can access their permitted review-team scope."""
    factory, _ = rbac_env
    user = factory.create_user("AuditorUser")
    team = factory.create_review_team("Scrutiny Team 1")
    factory.add_review_team_member(
        team.review_team_id, user.user_id, team_role=TeamRole.AUDITOR, is_active=True
    )
    factory.assign_role(user.user_id, role_id=2, review_team_id=team.review_team_id)

    token = create_access_token(subject=user.user_id)
    client.cookies.set(settings.access_cookie_name, token)

    response = client.get(f"/test-rbac/review-team/{team.review_team_id}")
    assert response.status_code == 200
    assert response.json()["access"] == "granted"
    assert response.json()["review_team_id"] == str(team.review_team_id)


def test_auditor_cannot_access_another_team(rbac_env, client):
    """6. Verify that Auditor cannot access another review team."""
    factory, _ = rbac_env
    user = factory.create_user("AuditorUser")
    team_1 = factory.create_review_team("Scrutiny Team 1")
    team_2 = factory.create_review_team("Scrutiny Team 2")
    factory.add_review_team_member(
        team_1.review_team_id, user.user_id, team_role=TeamRole.AUDITOR, is_active=True
    )
    factory.assign_role(user.user_id, role_id=2, review_team_id=team_1.review_team_id)

    token = create_access_token(subject=user.user_id)
    client.cookies.set(settings.access_cookie_name, token)

    response = client.get(f"/test-rbac/review-team/{team_2.review_team_id}")
    assert response.status_code == 403
    assert (
        f"access denied for review team {team_2.review_team_id}"
        in response.json()["detail"]
    )


def test_auditor_rejected_if_team_membership_becomes_inactive(rbac_env, client):
    """7. Verify that Auditor is rejected if team membership is deactivated."""
    factory, db = rbac_env
    user = factory.create_user("AuditorUser")
    team = factory.create_review_team("Deactivated Team")
    membership = factory.add_review_team_member(
        team.review_team_id, user.user_id, team_role=TeamRole.AUDITOR, is_active=True
    )
    factory.assign_role(user.user_id, role_id=2, review_team_id=team.review_team_id)

    # Deactivate the review team membership post-assignment
    membership.is_active = False
    db.commit()

    token = create_access_token(subject=user.user_id)
    client.cookies.set(settings.access_cookie_name, token)

    response = client.get(f"/test-rbac/review-team/{team.review_team_id}")
    assert response.status_code == 403


def test_lead_auditor_can_access_permitted_team_scope(rbac_env, client):
    """8. Verify that Lead Auditor can access permitted team scope."""
    factory, _ = rbac_env
    user = factory.create_user("LeadAuditor")
    team = factory.create_review_team("Lead Team")
    factory.add_review_team_member(
        team.review_team_id,
        user.user_id,
        team_role=TeamRole.LEAD_AUDITOR,
        is_active=True,
    )
    factory.assign_role(user.user_id, role_id=3, review_team_id=team.review_team_id)

    token = create_access_token(subject=user.user_id)
    client.cookies.set(settings.access_cookie_name, token)

    response = client.get(f"/test-rbac/review-team/{team.review_team_id}")
    assert response.status_code == 200
    assert response.json()["access"] == "granted"


def test_lead_auditor_cannot_use_auditor_membership_as_lead_auditor_permission(
    rbac_env,
):
    """9. Verify that Lead Auditor role requires LEAD_AUDITOR team role, not merely AUDITOR."""
    factory, db = rbac_env
    user = factory.create_user("MismatchedAuditor")
    team = factory.create_review_team("Audit Team")

    # Initially assigned with valid LEAD_AUDITOR team membership to satisfy the database trigger
    membership = factory.add_review_team_member(
        team.review_team_id,
        user.user_id,
        team_role=TeamRole.LEAD_AUDITOR,
        is_active=True,
    )
    factory.assign_role(user.user_id, role_id=3, review_team_id=team.review_team_id)

    # Membership team_role changes to AUDITOR
    membership.team_role = TeamRole.AUDITOR
    db.commit()

    active_assignments = get_active_role_assignments(user, db)
    # The LEAD_AUDITOR assignment must be invalidated due to team_role mismatch
    assert len(active_assignments) == 0


def test_revoked_lead_auditor_assignment_rejected(rbac_env, client):
    """10. Verify that revoked Lead Auditor assignment is rejected."""
    factory, _ = rbac_env
    user = factory.create_user("LeadAuditorRevoked")
    team = factory.create_review_team("Lead Team Revoked")
    factory.add_review_team_member(
        team.review_team_id,
        user.user_id,
        team_role=TeamRole.LEAD_AUDITOR,
        is_active=True,
    )
    factory.assign_role(
        user.user_id, role_id=3, review_team_id=team.review_team_id, revoked=True
    )

    token = create_access_token(subject=user.user_id)
    client.cookies.set(settings.access_cookie_name, token)

    response = client.get(f"/test-rbac/review-team/{team.review_team_id}")
    assert response.status_code == 403


def test_admin_satisfies_global_admin_role_requirement(rbac_env, client):
    """11. Verify that Admin role satisfies the global admin requirement."""
    factory, _ = rbac_env
    user = factory.create_user("AdminUser")
    factory.assign_role(user.user_id, role_id=4)  # ADMIN has null scopes

    token = create_access_token(subject=user.user_id)
    client.cookies.set(settings.access_cookie_name, token)

    response = client.get("/test-rbac/admin-only")
    assert response.status_code == 200
    assert response.json()["access"] == "granted"


def test_admin_cannot_bypass_institution_or_review_team_scope(rbac_env, client):
    """12. Verify that Admin cannot bypass institution or review-team data isolation boundaries."""
    factory, _ = rbac_env
    admin_user = factory.create_user("AdminUser")
    factory.assign_role(admin_user.user_id, role_id=4)

    inst = factory.create_institution("Confidential College")
    team = factory.create_review_team("Confidential Team")

    token = create_access_token(subject=admin_user.user_id)
    client.cookies.set(settings.access_cookie_name, token)

    # Admin must not access institution-scoped endpoint
    inst_resp = client.get(f"/test-rbac/institution/{inst.institution_id}")
    assert inst_resp.status_code == 403

    # Admin must not access review-team-scoped endpoint
    team_resp = client.get(f"/test-rbac/review-team/{team.review_team_id}")
    assert team_resp.status_code == 403


def test_role_not_present_in_active_assignment_returns_http_403(rbac_env, client):
    """13. Verify that user without required role returns HTTP 403."""
    factory, _ = rbac_env
    inst_user = factory.create_user("InstOnlyUser")
    inst = factory.create_institution("My College")
    factory.add_institution_membership(
        inst.institution_id, inst_user.user_id, is_active=True
    )
    factory.assign_role(
        inst_user.user_id, role_id=1, institution_id=inst.institution_id
    )

    token = create_access_token(subject=inst_user.user_id)
    client.cookies.set(settings.access_cookie_name, token)

    # Institution user attempts to hit admin-only endpoint
    response = client.get("/test-rbac/admin-only")
    assert response.status_code == 403
    assert "insufficient permissions" in response.json()["detail"]


def test_multiple_valid_assignments_returned_correctly(rbac_env, db_session=None):
    """14. Verify that multiple valid active assignments are all resolved without dropping."""
    factory, db = rbac_env
    user = factory.create_user("MultiScopeUser")

    inst_1 = factory.create_institution("Campus 1")
    inst_2 = factory.create_institution("Campus 2")

    factory.add_institution_membership(
        inst_1.institution_id, user.user_id, is_active=True
    )
    factory.add_institution_membership(
        inst_2.institution_id, user.user_id, is_active=True
    )

    factory.assign_role(user.user_id, role_id=1, institution_id=inst_1.institution_id)
    factory.assign_role(user.user_id, role_id=1, institution_id=inst_2.institution_id)

    active_assignments = get_active_role_assignments(user, db)
    assert len(active_assignments) == 2
    inst_ids = {a.institution_id for a in active_assignments}
    assert inst_1.institution_id in inst_ids
    assert inst_2.institution_id in inst_ids


def test_me_exposes_only_valid_role_contexts(rbac_env, client):
    """15. Verify that GET /api/v1/auth/me exposes active validated role contexts."""
    factory, _ = rbac_env
    user = factory.create_user("ProfileUser")
    inst = factory.create_institution("Polytechnic")
    factory.add_institution_membership(
        inst.institution_id, user.user_id, is_active=True
    )
    factory.assign_role(user.user_id, role_id=1, institution_id=inst.institution_id)

    token = create_access_token(subject=user.user_id)
    client.cookies.set(settings.access_cookie_name, token)

    response = client.get("/api/v1/auth/me")
    assert response.status_code == 200
    data = response.json()
    assert data["user"]["user_id"] == str(user.user_id)
    assert len(data["roles"]) == 1
    assert data["roles"][0]["role_code"] == "INSTITUTION_USER"
    assert data["roles"][0]["institution_id"] == str(inst.institution_id)
    assert data["roles"][0]["review_team_id"] is None


def test_me_excludes_revoked_assignments_and_inactive_memberships(rbac_env, client):
    """16. Verify that GET /api/v1/auth/me excludes revoked or inactive assignments."""
    factory, db = rbac_env
    user = factory.create_user("MixedStatusUser")

    # Valid active institution assignment
    inst_valid = factory.create_institution("Valid Campus")
    factory.add_institution_membership(
        inst_valid.institution_id, user.user_id, is_active=True
    )
    factory.assign_role(
        user.user_id, role_id=1, institution_id=inst_valid.institution_id
    )

    # Inactive membership assignment (initially active for trigger, then deactivated)
    inst_inactive = factory.create_institution("Inactive Campus")
    m_inactive = factory.add_institution_membership(
        inst_inactive.institution_id, user.user_id, is_active=True
    )
    factory.assign_role(
        user.user_id, role_id=1, institution_id=inst_inactive.institution_id
    )
    m_inactive.is_active = False
    db.commit()

    # Revoked assignment
    inst_revoked = factory.create_institution("Revoked Campus")
    factory.add_institution_membership(
        inst_revoked.institution_id, user.user_id, is_active=True
    )
    factory.assign_role(
        user.user_id,
        role_id=1,
        institution_id=inst_revoked.institution_id,
        revoked=True,
    )

    token = create_access_token(subject=user.user_id)
    client.cookies.set(settings.access_cookie_name, token)

    response = client.get("/api/v1/auth/me")
    assert response.status_code == 200
    data = response.json()
    assert len(data["roles"]) == 1
    assert data["roles"][0]["institution_id"] == str(inst_valid.institution_id)


def test_institution_access_missing_path_param_returns_http_400(rbac_env, client):
    """17. Verify that missing institution_id path parameter returns HTTP 400."""
    factory, _ = rbac_env
    user = factory.create_user("InstUser")
    inst = factory.create_institution("College Missing Param")
    factory.add_institution_membership(
        inst.institution_id, user.user_id, is_active=True
    )
    factory.assign_role(user.user_id, role_id=1, institution_id=inst.institution_id)

    token = create_access_token(subject=user.user_id)
    client.cookies.set(settings.access_cookie_name, token)

    # Endpoint has no {institution_id} in its path
    response = client.get("/test-rbac/missing-institution-path-param")
    assert response.status_code == 400
    assert (
        "does not specify an institution_id in path parameters"
        in response.json()["detail"]
    )


def test_institution_access_query_param_does_not_bypass_missing_path(rbac_env, client):
    """18. Verify that query parameter institution_id cannot bypass missing path parameter."""
    factory, _ = rbac_env
    user = factory.create_user("InstUser")
    inst = factory.create_institution("College Query Spoof")
    factory.add_institution_membership(
        inst.institution_id, user.user_id, is_active=True
    )
    factory.assign_role(user.user_id, role_id=1, institution_id=inst.institution_id)

    token = create_access_token(subject=user.user_id)
    client.cookies.set(settings.access_cookie_name, token)

    # Malicious or client-supplied query parameter must be completely ignored
    response = client.get(
        f"/test-rbac/missing-institution-path-param?institution_id={inst.institution_id}"
    )
    assert response.status_code == 400
    assert (
        "does not specify an institution_id in path parameters"
        in response.json()["detail"]
    )


def test_institution_access_malformed_path_param_returns_http_400(rbac_env, client):
    """19. Verify that a malformed UUID in institution path parameter returns HTTP 400."""
    factory, _ = rbac_env
    user = factory.create_user("InstUser")
    inst = factory.create_institution("College Malformed")
    factory.add_institution_membership(
        inst.institution_id, user.user_id, is_active=True
    )
    factory.assign_role(user.user_id, role_id=1, institution_id=inst.institution_id)

    token = create_access_token(subject=user.user_id)
    client.cookies.set(settings.access_cookie_name, token)

    response = client.get("/test-rbac/institution/not-a-valid-uuid")
    assert response.status_code == 400
    assert (
        "Invalid institution_id in endpoint path parameter" in response.json()["detail"]
    )


def test_review_team_access_missing_path_param_returns_http_400(rbac_env, client):
    """20. Verify that missing review_team_id path parameter returns HTTP 400."""
    factory, _ = rbac_env
    user = factory.create_user("AuditorUser")
    team = factory.create_review_team("Team Missing Param")
    factory.add_review_team_member(
        team.review_team_id, user.user_id, team_role=TeamRole.AUDITOR, is_active=True
    )
    factory.assign_role(user.user_id, role_id=2, review_team_id=team.review_team_id)

    token = create_access_token(subject=user.user_id)
    client.cookies.set(settings.access_cookie_name, token)

    response = client.get("/test-rbac/missing-review-team-path-param")
    assert response.status_code == 400
    assert (
        "does not specify a review_team_id in path parameters"
        in response.json()["detail"]
    )


def test_review_team_access_query_param_does_not_bypass_missing_path(rbac_env, client):
    """21. Verify that query parameter review_team_id cannot bypass missing path parameter."""
    factory, _ = rbac_env
    user = factory.create_user("AuditorUser")
    team = factory.create_review_team("Team Query Spoof")
    factory.add_review_team_member(
        team.review_team_id, user.user_id, team_role=TeamRole.AUDITOR, is_active=True
    )
    factory.assign_role(user.user_id, role_id=2, review_team_id=team.review_team_id)

    token = create_access_token(subject=user.user_id)
    client.cookies.set(settings.access_cookie_name, token)

    # Malicious or client-supplied query parameter must be completely ignored
    response = client.get(
        f"/test-rbac/missing-review-team-path-param?review_team_id={team.review_team_id}"
    )
    assert response.status_code == 400
    assert (
        "does not specify a review_team_id in path parameters"
        in response.json()["detail"]
    )


def test_review_team_access_malformed_path_param_returns_http_400(rbac_env, client):
    """22. Verify that a malformed UUID in review team path parameter returns HTTP 400."""
    factory, _ = rbac_env
    user = factory.create_user("AuditorUser")
    team = factory.create_review_team("Team Malformed")
    factory.add_review_team_member(
        team.review_team_id, user.user_id, team_role=TeamRole.AUDITOR, is_active=True
    )
    factory.assign_role(user.user_id, role_id=2, review_team_id=team.review_team_id)

    token = create_access_token(subject=user.user_id)
    client.cookies.set(settings.access_cookie_name, token)

    response = client.get("/test-rbac/review-team/not-a-valid-uuid")
    assert response.status_code == 400
    assert (
        "Invalid review_team_id in endpoint path parameter" in response.json()["detail"]
    )

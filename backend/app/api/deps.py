import secrets
from dataclasses import dataclass
from typing import Annotated
from uuid import UUID

import jwt
from fastapi import Depends, Header, HTTPException, Request, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.security import SecurityConfigError, decode_access_token
from app.db.session import get_db
from app.models.enums import TeamRole, UserStatus
from app.models.institution_membership import InstitutionMembership
from app.models.review_team_member import ReviewTeamMember
from app.models.role import Role
from app.models.user import User
from app.models.user_role_assignment import UserRoleAssignment


@dataclass(frozen=True)
class RoleAssignmentContext:
    """Validated role assignment representing an active role and its authorized scope."""

    assignment_id: UUID
    role_code: str
    institution_id: UUID | None = None
    review_team_id: UUID | None = None


def verify_csrf(
    request: Request,
    x_csrf_token: Annotated[str | None, Header(alias="X-CSRF-Token")] = None,
) -> str:
    """Validate CSRF token by comparing the request cookie and X-CSRF-Token header.

    Raises:
        HTTPException(403): If the CSRF cookie or header is missing or does not match.
    """
    cookie_token = request.cookies.get(settings.csrf_cookie_name)

    if not cookie_token or not x_csrf_token:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="CSRF validation failed: token missing.",
        )

    if not secrets.compare_digest(cookie_token, x_csrf_token):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="CSRF validation failed: token mismatch.",
        )

    return cookie_token


def get_current_user(
    request: Request,
    db: Annotated[Session, Depends(get_db)],
) -> User:
    """Extract and validate the access token from the HttpOnly cookie, loading the user from PostgreSQL.

    Raises:
        HTTPException(401): If the token is missing, invalid, expired, malformed, or user not found.
        HTTPException(403): If the user account is not active (INVITED, SUSPENDED, DISABLED).
        HTTPException(503): If the JWT secret key is misconfigured.
    """
    token = request.cookies.get(settings.access_cookie_name)
    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required: access token missing.",
        )

    try:
        payload = decode_access_token(token)
    except SecurityConfigError:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Authentication service configuration error.",
        )
    except jwt.PyJWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid, expired, or malformed authentication token.",
        )

    subject = payload.get("sub")
    if not subject:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication token: missing subject.",
        )

    try:
        user_id = UUID(str(subject))
    except (ValueError, TypeError):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication token subject format.",
        )

    user = db.get(User, user_id)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authenticated user no longer exists.",
        )

    if user.status != UserStatus.ACTIVE:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"User account is not active (status: {user.status.value}).",
        )

    return user


def get_active_role_assignments(
    current_user: User,
    db: Session,
) -> list[RoleAssignmentContext]:
    """Resolve and validate the active role assignments for the authenticated user from PostgreSQL.

    Revalidates live membership records:
    - INSTITUTION_USER requires institution_id and active InstitutionMembership.
    - AUDITOR requires review_team_id and active ReviewTeamMember with team_role=AUDITOR.
    - LEAD_AUDITOR requires review_team_id and active ReviewTeamMember with team_role=LEAD_AUDITOR.
    - ADMIN requires null institution_id and null review_team_id.

    Revoked assignments or inactive memberships are excluded.
    """
    # 1. Fetch unrevoked role assignments joined with roles
    stmt = (
        select(UserRoleAssignment, Role.role_code)
        .join(Role, UserRoleAssignment.role_id == Role.role_id)
        .where(
            UserRoleAssignment.user_id == current_user.user_id,
            UserRoleAssignment.revoked_at.is_(None),
        )
    )
    assignment_rows = db.execute(stmt).all()
    if not assignment_rows:
        return []

    # 2. Batch load active institution memberships for the user
    active_institution_ids = set(
        db.scalars(
            select(InstitutionMembership.institution_id).where(
                InstitutionMembership.user_id == current_user.user_id,
                InstitutionMembership.is_active.is_(True),
            )
        ).all()
    )

    # 3. Batch load active review team memberships with team_role for the user
    active_team_roles = {
        (m.review_team_id, m.team_role)
        for m in db.scalars(
            select(ReviewTeamMember).where(
                ReviewTeamMember.user_id == current_user.user_id,
                ReviewTeamMember.is_active.is_(True),
            )
        ).all()
    }

    # 4. Filter and build validated contexts. Operational role packages are
    # scoped to an active review-team membership with the same role code.
    review_team_role_codes = {
        item.value for item in TeamRole
    }
    global_configuration_roles = {"ADMIN", "REGULATORY_POLICY_PUBLISHER"}
    valid_contexts: list[RoleAssignmentContext] = []
    for assignment, role_code in assignment_rows:
        if role_code == "INSTITUTION_USER":
            if (
                assignment.institution_id is not None
                and assignment.review_team_id is None
                and assignment.institution_id in active_institution_ids
            ):
                valid_contexts.append(
                    RoleAssignmentContext(
                        assignment_id=assignment.user_role_assignment_id,
                        role_code=role_code,
                        institution_id=assignment.institution_id,
                        review_team_id=None,
                    )
                )

        elif role_code in review_team_role_codes:
            if (
                assignment.review_team_id is not None
                and assignment.institution_id is None
                and (assignment.review_team_id, TeamRole(role_code)) in active_team_roles
            ):
                valid_contexts.append(
                    RoleAssignmentContext(
                        assignment_id=assignment.user_role_assignment_id,
                        role_code=role_code,
                        institution_id=None,
                        review_team_id=assignment.review_team_id,
                    )
                )

        elif (
            role_code in global_configuration_roles
            and assignment.institution_id is None
            and assignment.review_team_id is None
        ):
            valid_contexts.append(
                RoleAssignmentContext(
                    assignment_id=assignment.user_role_assignment_id,
                    role_code=role_code,
                    institution_id=None,
                    review_team_id=None,
                )
            )

    return valid_contexts


def require_role(*allowed_roles: str):
    """FastAPI dependency factory enforcing that the user has at least one active assignment in allowed_roles."""

    def role_checker(
        current_user: Annotated[User, Depends(get_current_user)],
        db: Annotated[Session, Depends(get_db)],
    ) -> list[RoleAssignmentContext]:
        active_assignments = get_active_role_assignments(current_user, db)
        matching = [a for a in active_assignments if a.role_code in allowed_roles]
        if not matching:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Forbidden: insufficient permissions for this operation.",
            )
        return matching

    return role_checker


def require_institution_access(
    request: Request,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
) -> RoleAssignmentContext:
    """Validate that the authenticated user has active INSTITUTION_USER scope for the requested institution_id.

    Obtains the target resource identifier exclusively from request.path_params["institution_id"].
    Rejects with HTTP 400 if the path parameter is absent or malformed.
    Admins and users without an active, verified assignment for this exact institution are denied access (HTTP 403).
    """
    if "institution_id" not in request.path_params:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Endpoint resource scope does not specify an institution_id in path parameters.",
        )

    raw_id = request.path_params["institution_id"]
    try:
        target_institution_id = (
            raw_id if isinstance(raw_id, UUID) else UUID(str(raw_id))
        )
    except (ValueError, TypeError):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid institution_id in endpoint path parameter.",
        )

    active_assignments = get_active_role_assignments(current_user, db)
    matching = next(
        (
            a
            for a in active_assignments
            if a.role_code == "INSTITUTION_USER"
            and a.institution_id == target_institution_id
        ),
        None,
    )
    if not matching:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Forbidden: access denied for institution {target_institution_id}.",
        )
    return matching


def require_review_team_access(
    request: Request,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
) -> RoleAssignmentContext:
    """Validate that the authenticated user has active AUDITOR or LEAD_AUDITOR scope for the requested review_team_id.

    Obtains the target resource identifier exclusively from request.path_params["review_team_id"].
    Rejects with HTTP 400 if the path parameter is absent or malformed.
    Admins and users without an active, verified assignment for this exact review team are denied access (HTTP 403).
    """
    if "review_team_id" not in request.path_params:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Endpoint resource scope does not specify a review_team_id in path parameters.",
        )

    raw_id = request.path_params["review_team_id"]
    try:
        target_team_id = raw_id if isinstance(raw_id, UUID) else UUID(str(raw_id))
    except (ValueError, TypeError):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid review_team_id in endpoint path parameter.",
        )

    active_assignments = get_active_role_assignments(current_user, db)
    matching = next(
        (
            a
            for a in active_assignments
            if a.review_team_id == target_team_id
        ),
        None,
    )
    if not matching:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Forbidden: access denied for review team {target_team_id}.",
        )
    return matching


# Convenient role dependency shortcuts
require_admin = require_role("ADMIN")
require_institution_user = require_role("INSTITUTION_USER")
require_auditor = require_role("AUDITOR", "INTAKE_OFFICER", "SCRUTINY_OFFICER")
require_lead_auditor = require_role("LEAD_AUDITOR", "REGIONAL_OFFICER", "BUREAU_SUPERVISOR")
require_any_auditor = require_role(
    "AUDITOR", "LEAD_AUDITOR", "INTAKE_OFFICER", "SCRUTINY_OFFICER",
    "REGIONAL_OFFICER", "EVC_COORDINATOR", "EVC_MEMBER", "COMMITTEE_SECRETARIAT",
    "BUREAU_SUPERVISOR", "COMPETENT_AUTHORITY",
)
require_competent_authority = require_role("COMPETENT_AUTHORITY")
require_policy_publisher = require_role("REGULATORY_POLICY_PUBLISHER")

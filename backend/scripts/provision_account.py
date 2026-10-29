"""Provision one AIC-Flow user with a validated role and scope.

This is an operator-run account bootstrap utility. It does not ship default
credentials or expose a public self-registration endpoint. For a production
run, APP_ENV must be production and the operator must pass --confirm-production
and type the exact confirmation phrase.
"""

from __future__ import annotations

import argparse
import getpass
import sys
from pathlib import Path
from uuid import UUID

BACKEND_DIR = str(Path(__file__).resolve().parents[1])
if BACKEND_DIR not in sys.path:
    sys.path.insert(0, BACKEND_DIR)

from sqlalchemy import func, select

from app.core.config import settings
from app.core.security import hash_password
from app.db.session import SessionLocal
from app.models.enums import RoleCode, TeamRole, UserStatus
from app.models.institution import Institution
from app.models.institution_membership import InstitutionMembership
from app.models.review_team import ReviewTeam
from app.models.review_team_member import ReviewTeamMember
from app.models.role import Role
from app.models.user import User
from app.models.user_role_assignment import UserRoleAssignment

TEAM_ROLE_CODES = {item.value for item in TeamRole}
GLOBAL_ROLE_CODES = {RoleCode.ADMIN.value, RoleCode.REGULATORY_POLICY_PUBLISHER.value}
ROLE_CODES = {item.value for item in RoleCode}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Provision an AIC-Flow account with a scoped role.")
    parser.add_argument("--email", required=True, help="User email address")
    parser.add_argument("--name", required=True, help="User's display name")
    parser.add_argument("--role", required=True, choices=sorted(ROLE_CODES), help="Permission package to assign")
    parser.add_argument("--institution-id", help="Required for INSTITUTION_USER")
    parser.add_argument("--review-team-id", help="Required for operational review-team roles")
    parser.add_argument("--team-name", help="For a team role, create/reuse a team by this name instead of supplying --review-team-id")
    parser.add_argument("--confirm-production", action="store_true", help="Required when APP_ENV=production")
    return parser.parse_args()


def prompt_password() -> str:
    while True:
        password = getpass.getpass("Set account password (minimum 12 characters): ")
        confirmation = getpass.getpass("Confirm account password: ")
        if password != confirmation:
            print("Passwords do not match. Try again.")
            continue
        if len(password) < 12:
            print("Use at least 12 characters.")
            continue
        return password


def main() -> int:
    args = parse_args()
    email = args.email.strip().lower()
    full_name = args.name.strip()
    role_code = args.role

    if "@" not in email or len(email) > 320:
        print("ERROR: Provide a valid email address.")
        return 2
    if not full_name or len(full_name) > 200:
        print("ERROR: Name must contain 1–200 characters.")
        return 2

    if settings.app_env.lower() == "production":
        if not args.confirm_production:
            print("ERROR: Production provisioning requires --confirm-production.")
            return 2
        if input("Type PRODUCTION to confirm account creation in the production database: ").strip() != "PRODUCTION":
            print("Cancelled.")
            return 2

    institution_id: UUID | None = None
    review_team_id: UUID | None = None
    if role_code == RoleCode.INSTITUTION_USER.value:
        if not args.institution_id or args.review_team_id or args.team_name:
            print("ERROR: INSTITUTION_USER requires --institution-id and no team scope.")
            return 2
        try:
            institution_id = UUID(args.institution_id)
        except ValueError:
            print("ERROR: --institution-id must be a UUID.")
            return 2
    elif role_code in TEAM_ROLE_CODES:
        if args.institution_id or bool(args.review_team_id) == bool(args.team_name):
            print("ERROR: Team roles require exactly one of --review-team-id or --team-name, and no institution scope.")
            return 2
        if args.review_team_id:
            try:
                review_team_id = UUID(args.review_team_id)
            except ValueError:
                print("ERROR: --review-team-id must be a UUID.")
                return 2
    elif role_code in GLOBAL_ROLE_CODES:
        if args.institution_id or args.review_team_id or args.team_name:
            print("ERROR: Global configuration roles must not receive institution or team scope.")
            return 2
    else:
        print("ERROR: Unsupported role code.")
        return 2

    password = prompt_password()
    db = SessionLocal()
    try:
        existing = db.scalar(select(User).where(func.lower(User.email) == email))
        if existing is not None:
            print("ERROR: This email already exists. Use the authorised account recovery process; this utility never overwrites accounts.")
            return 3

        role = db.scalar(select(Role).where(Role.role_code == role_code))
        if role is None:
            print(f"ERROR: Role {role_code} is not present. Apply the database migrations first.")
            return 3

        if institution_id is not None:
            institution = db.get(Institution, institution_id)
            if institution is None or not institution.is_active:
                print("ERROR: Institution not found or inactive.")
                return 3

        team: ReviewTeam | None = None
        if role_code in TEAM_ROLE_CODES:
            if args.team_name:
                team_name = args.team_name.strip()
                if not team_name or len(team_name) > 160:
                    print("ERROR: Team name must contain 1–160 characters.")
                    return 2
                team = db.scalar(select(ReviewTeam).where(ReviewTeam.team_name == team_name))
                if team is None:
                    team = ReviewTeam(team_name=team_name, description="AIC-Flow operational review team", is_active=True)
                    db.add(team)
                    db.flush()
                elif not team.is_active:
                    print("ERROR: The requested review team is inactive; it will not be reactivated.")
                    return 3
                review_team_id = team.review_team_id
            else:
                team = db.get(ReviewTeam, review_team_id)
                if team is None or not team.is_active:
                    print("ERROR: Review team not found or inactive.")
                    return 3

        user = User(full_name=full_name, email=email, password_hash=hash_password(password), status=UserStatus.ACTIVE)
        db.add(user)
        db.flush()

        if institution_id is not None:
            db.add(InstitutionMembership(institution_id=institution_id, user_id=user.user_id, is_active=True))
        elif review_team_id is not None:
            db.add(ReviewTeamMember(
                review_team_id=review_team_id,
                user_id=user.user_id,
                team_role=TeamRole(role_code),
                is_active=True,
            ))

        db.flush()
        db.add(UserRoleAssignment(
            user_id=user.user_id,
            role_id=role.role_id,
            institution_id=institution_id,
            review_team_id=review_team_id,
        ))
        db.commit()

        print("Account provisioned successfully.")
        print(f"User ID: {user.user_id}")
        print(f"Email: {email}")
        print(f"Role: {role_code}")
        if institution_id:
            print(f"Institution ID: {institution_id}")
        if review_team_id:
            print(f"Review Team ID: {review_team_id}")
        print("The password is not displayed. Store it in your approved password manager.")
        return 0
    except Exception as exc:  # noqa: BLE001
        db.rollback()
        print(f"ERROR: Account provisioning failed; transaction rolled back: {exc}")
        return 1
    finally:
        db.close()


if __name__ == "__main__":
    raise SystemExit(main())

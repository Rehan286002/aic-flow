"""Create the isolated baseline records required by the backend CI test suite.

This script is intentionally restricted to APP_ENV=test and the dedicated
PostgreSQL database named ``aic_flow_test``. It is safe to run repeatedly and
must never be used to create accounts or institution records in a real service.
"""

from __future__ import annotations

import sys
import uuid
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parents[1]
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from sqlalchemy import func, select
from sqlalchemy.engine import make_url

from app.core.config import settings
from app.db.session import SessionLocal
from app.models.application import Application
from app.models.application_document_link import ApplicationDocumentLink
from app.models.application_requirements import ApplicationRequirement
from app.models.application_revision import ApplicationRevision
from app.models.application_status_history import ApplicationStatusHistory
from app.models.checklist_item import ChecklistItem
from app.models.document import Document
from app.models.document_type import DocumentType
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
from app.services.checklist_service import (
    get_published_template_for_application,
    initialize_revision_requirements,
    seed_standard_references,
)
from app.services.workflow_service import create_workflow_case

TEST_DATABASE_NAME = "aic_flow_test"
INSTITUTION_PERMANENT_ID = "SYNTH-AICTE-0001"
APPLICATION_NUMBER = "APP-2026-EOA-0006"
INSTITUTION_EMAIL = "institution@aic-verify.internal"
ADMIN_EMAIL = "admin@aic-verify.internal"
AUDITOR_EMAIL = "auditor@aic-verify.internal"
LEAD_AUDITOR_EMAIL = "lead@aic-verify.internal"
REVIEW_TEAM_NAME = "Western Region Review Team"
REVIEW_TEAM_ID = uuid.UUID("9533f553-82be-44ac-9d46-85936fdec003")
BASELINE_DOCUMENT_FILENAME = "ci_baseline_affidavit.pdf"


def assert_ci_test_database() -> None:
    """Fail closed unless the process targets the dedicated CI test database."""
    if settings.app_env.strip().lower() != "test":
        raise SystemExit("Refusing CI fixture seeding: APP_ENV must be exactly 'test'.")

    database_name = make_url(settings.database_url).database
    if database_name != TEST_DATABASE_NAME:
        raise SystemExit(
            "Refusing CI fixture seeding: DATABASE_URL must target the dedicated "
            f"'{TEST_DATABASE_NAME}' database (received {database_name!r})."
        )


def get_or_create_user(db, email: str, full_name: str) -> User:
    user = db.scalar(select(User).where(func.lower(User.email) == email.lower()))
    if user is None:
        user = User(
            email=email,
            full_name=full_name,
            password_hash=None,
            status=UserStatus.ACTIVE,
        )
        db.add(user)
        db.flush()
    elif user.status != UserStatus.ACTIVE:
        raise RuntimeError(f"CI fixture account {email} exists but is not ACTIVE.")
    return user


def get_role(db, role_code: RoleCode) -> Role:
    role = db.scalar(select(Role).where(Role.role_code == role_code.value))
    if role is None:
        raise RuntimeError(
            f"Role {role_code.value} is missing. Apply all Alembic migrations first."
        )
    return role


def ensure_role_assignment(
    db,
    user: User,
    role_code: RoleCode,
    *,
    institution_id=None,
    review_team_id=None,
) -> None:
    role = get_role(db, role_code)
    existing = db.scalar(
        select(UserRoleAssignment).where(
            UserRoleAssignment.user_id == user.user_id,
            UserRoleAssignment.role_id == role.role_id,
            UserRoleAssignment.institution_id == institution_id,
            UserRoleAssignment.review_team_id == review_team_id,
            UserRoleAssignment.revoked_at.is_(None),
        )
    )
    if existing is None:
        db.add(
            UserRoleAssignment(
                user_id=user.user_id,
                role_id=role.role_id,
                institution_id=institution_id,
                review_team_id=review_team_id,
            )
        )


def seed_identity(db):
    institution = db.scalar(
        select(Institution).where(
            Institution.aicte_permanent_institution_id == INSTITUTION_PERMANENT_ID
        )
    )
    if institution is None:
        institution = Institution(
            aicte_permanent_institution_id=INSTITUTION_PERMANENT_ID,
            institution_name="Apex Institute of Technology",
            institution_type="PRIVATE_SELF_FINANCING",
            address_line="CI-only fictional address",
            district="Mumbai Suburban",
            state="Maharashtra",
            postal_code="400001",
            is_active=True,
        )
        db.add(institution)
        db.flush()

    institution_user = get_or_create_user(
        db, INSTITUTION_EMAIL, "CI Institution Representative"
    )
    admin_user = get_or_create_user(db, ADMIN_EMAIL, "CI Platform Administrator")
    auditor_user = get_or_create_user(db, AUDITOR_EMAIL, "Synthetic Auditor")
    lead_user = get_or_create_user(db, LEAD_AUDITOR_EMAIL, "Synthetic Lead Auditor")

    institution_membership = db.scalar(
        select(InstitutionMembership).where(
            InstitutionMembership.institution_id == institution.institution_id,
            InstitutionMembership.user_id == institution_user.user_id,
        )
    )
    if institution_membership is None:
        db.add(
            InstitutionMembership(
                institution_id=institution.institution_id,
                user_id=institution_user.user_id,
                is_active=True,
            )
        )

    review_team = db.scalar(
        select(ReviewTeam).where(ReviewTeam.team_name == REVIEW_TEAM_NAME)
    )
    if review_team is None:
        review_team = ReviewTeam(
            review_team_id=REVIEW_TEAM_ID,
            team_name=REVIEW_TEAM_NAME,
            description="Isolated CI review team; not a real AICTE unit.",
            is_active=True,
        )
        db.add(review_team)
        db.flush()
    elif review_team.review_team_id != REVIEW_TEAM_ID:
        raise RuntimeError("Existing CI review team has an unexpected fixture ID.")

    for member, team_role in (
        (auditor_user, TeamRole.AUDITOR),
        (lead_user, TeamRole.LEAD_AUDITOR),
    ):
        membership = db.scalar(
            select(ReviewTeamMember).where(
                ReviewTeamMember.review_team_id == review_team.review_team_id,
                ReviewTeamMember.user_id == member.user_id,
            )
        )
        if membership is None:
            db.add(
                ReviewTeamMember(
                    review_team_id=review_team.review_team_id,
                    user_id=member.user_id,
                    team_role=team_role,
                    is_active=True,
                )
            )
        elif membership.team_role != team_role or not membership.is_active:
            raise RuntimeError(
                f"CI team membership for {member.email} conflicts with {team_role.value}."
            )

    db.flush()
    ensure_role_assignment(
        db,
        institution_user,
        RoleCode.INSTITUTION_USER,
        institution_id=institution.institution_id,
    )
    ensure_role_assignment(db, admin_user, RoleCode.ADMIN)
    ensure_role_assignment(
        db,
        auditor_user,
        RoleCode.AUDITOR,
        review_team_id=review_team.review_team_id,
    )
    ensure_role_assignment(
        db,
        lead_user,
        RoleCode.LEAD_AUDITOR,
        review_team_id=review_team.review_team_id,
    )

    return institution, institution_user, review_team


def seed_application_and_document(db, institution, institution_user, review_team) -> None:
    application = db.scalar(
        select(Application).where(Application.application_number == APPLICATION_NUMBER)
    )
    if application is None:
        application = Application(
            application_number=APPLICATION_NUMBER,
            institution_id=institution.institution_id,
            application_family=ApplicationFamily.EXISTING_INSTITUTION,
            process_type="EOA_SELF_DISCLOSURE",
            academic_year="2026-27",
            status=ApplicationStatus.DRAFT,
            created_by=institution_user.user_id,
        )
        db.add(application)
        db.flush()
    else:
        expected = (
            application.institution_id == institution.institution_id
            and application.academic_year == "2026-27"
            and application.application_family == ApplicationFamily.EXISTING_INSTITUTION
            and application.process_type == "EOA_SELF_DISCLOSURE"
            and application.status == ApplicationStatus.DRAFT
        )
        if not expected:
            raise RuntimeError(
                f"CI baseline application {APPLICATION_NUMBER} exists with unexpected attributes."
            )
        # The default baseline case is intentionally unassigned. Individual tests
        # assign it to a reviewer team when exercising team-scoped access.
        application.review_team_id = None

    revision = db.scalar(
        select(ApplicationRevision).where(
            ApplicationRevision.application_id == application.application_id,
            ApplicationRevision.revision_number == 1,
        )
    )
    if revision is None:
        revision = ApplicationRevision(
            application_id=application.application_id,
            revision_number=1,
            status=RevisionStatus.DRAFT,
            created_by=institution_user.user_id,
        )
        db.add(revision)
        db.flush()
    application.current_revision_id = revision.application_revision_id

    history = db.scalar(
        select(ApplicationStatusHistory).where(
            ApplicationStatusHistory.application_id == application.application_id,
            ApplicationStatusHistory.from_status.is_(None),
            ApplicationStatusHistory.to_status == ApplicationStatus.DRAFT,
        )
    )
    if history is None:
        db.add(
            ApplicationStatusHistory(
                application_id=application.application_id,
                from_status=None,
                to_status=ApplicationStatus.DRAFT,
                changed_by=institution_user.user_id,
                change_reason="CI-only baseline EoA application draft.",
            )
        )

    template = get_published_template_for_application(
        db, "2026-27", ApplicationFamily.EXISTING_INSTITUTION
    )
    if template is None:
        raise RuntimeError(
            "Published EoA checklist template missing. Run seed_checklist.py first."
        )

    existing_requirements = db.scalars(
        select(ApplicationRequirement).where(
            ApplicationRequirement.application_revision_id == revision.application_revision_id
        )
    ).all()
    if not existing_requirements:
        initialize_revision_requirements(
            db,
            revision.application_revision_id,
            template.checklist_template_id,
            {
                "completion_certificate_issue_date": "1990-05-15",
                "payment_applicable": True,
                "application_remarks": "CI fixture only; never treated as an official application.",
            },
        )

    create_workflow_case(
        db,
        application,
        institution_user.user_id,
        "EOA_SELF_DISCLOSURE",
    )
    db.flush()

    document = db.scalar(
        select(Document).where(
            Document.institution_id == institution.institution_id,
            Document.document_label == "CI baseline affidavit fixture",
        )
    )
    if document is None:
        document_type = db.scalar(
            select(DocumentType).where(
                DocumentType.type_code == "AFFIDAVIT_UNDERTAKING"
            )
        )
        if document_type is None:
            raise RuntimeError("AFFIDAVIT_UNDERTAKING document type is missing.")
        document = Document(
            institution_id=institution.institution_id,
            document_type_id=document_type.document_type_id,
            document_label="CI baseline affidavit fixture",
            created_by=institution_user.user_id,
        )
        db.add(document)
        db.flush()

    document_version = db.scalar(
        select(DocumentVersion).where(
            DocumentVersion.document_id == document.document_id,
            DocumentVersion.version_number == 1,
        )
    )
    if document_version is None:
        document_version = DocumentVersion(
            document_id=document.document_id,
            version_number=1,
            original_filename=BASELINE_DOCUMENT_FILENAME,
            storage_key="ci-fixtures/baseline/affidavit.pdf",
            mime_type="application/pdf",
            file_size_bytes=128,
            sha256_hex="0" * 64,
            page_count=1,
            uploaded_by=institution_user.user_id,
        )
        db.add(document_version)
        db.flush()

    affidavit_item = db.scalar(
        select(ChecklistItem).where(ChecklistItem.item_code == "EOA-SD-01")
    )
    affidavit_requirement = db.scalar(
        select(ApplicationRequirement).where(
            ApplicationRequirement.application_revision_id == revision.application_revision_id,
            ApplicationRequirement.checklist_item_id == affidavit_item.checklist_item_id,
        )
    )
    if affidavit_requirement is None:
        raise RuntimeError("EOA-SD-01 requirement is missing from the CI baseline revision.")

    link = db.scalar(
        select(ApplicationDocumentLink).where(
            ApplicationDocumentLink.application_revision_id == revision.application_revision_id,
            ApplicationDocumentLink.document_version_id == document_version.document_version_id,
        )
    )
    if link is None:
        db.add(
            ApplicationDocumentLink(
                application_revision_id=revision.application_revision_id,
                uploaded_for_requirement_id=affidavit_requirement.application_requirement_id,
                document_version_id=document_version.document_version_id,
            )
        )


def main() -> int:
    assert_ci_test_database()
    db = SessionLocal()
    try:
        seed_standard_references(db)
        institution, institution_user, review_team = seed_identity(db)
        seed_application_and_document(db, institution, institution_user, review_team)
        db.commit()
        print("CI-only baseline fixture seeded successfully (institution, roles, application, requirements, document).")
        return 0
    except Exception as exc:  # noqa: BLE001
        db.rollback()
        print(f"ERROR seeding CI-only baseline: {exc}", file=sys.stderr)
        return 1
    finally:
        db.close()


if __name__ == "__main__":
    raise SystemExit(main())
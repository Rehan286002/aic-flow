"""Initial identity and application foundation.

Revision ID: c33c142f79bd
Revises:
Create Date: 2026-10-27

"""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

# ---------------------------------------------------------------------------
# Revision identifiers
# ---------------------------------------------------------------------------

revision: str = "c33c142f79bd"
down_revision: str | Sequence[str] | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


# ---------------------------------------------------------------------------
# PostgreSQL ENUM definitions
#
# create_type=False prevents SQLAlchemy from attempting to create the same
# PostgreSQL enum repeatedly when several tables use it.
# We create and drop these types explicitly in upgrade/downgrade.
# ---------------------------------------------------------------------------

user_status_enum = postgresql.ENUM(
    "ACTIVE",
    "INVITED",
    "SUSPENDED",
    "DISABLED",
    name="user_status",
    create_type=False,
)

application_family_enum = postgresql.ENUM(
    "NEW_INSTITUTION",
    "EXISTING_INSTITUTION",
    "UNIVERSITY",
    "OTHER",
    name="application_family",
    create_type=False,
)

application_status_enum = postgresql.ENUM(
    "DRAFT",
    "SUBMITTED",
    "VALIDATING",
    "RECTIFICATION_REQUESTED",
    "RESUBMITTED",
    "UNDER_AUDITOR_REVIEW",
    "ESCALATED_TO_LEAD",
    "UNDER_LEAD_REVIEW",
    "INSPECTION_REQUIRED",
    "RECOMMENDATION_ISSUED",
    "AWAITING_AUTHORITY_DISPOSITION",
    "ON_HOLD",
    "CLOSED",
    name="application_status",
    create_type=False,
)

revision_status_enum = postgresql.ENUM(
    "DRAFT",
    "SUBMITTED",
    "SUPERSEDED",
    name="revision_status",
    create_type=False,
)

team_role_enum = postgresql.ENUM(
    "AUDITOR",
    "LEAD_AUDITOR",
    name="team_role",
    create_type=False,
)


# ---------------------------------------------------------------------------
# UPGRADE
# ---------------------------------------------------------------------------


def upgrade() -> None:
    """Create the identity and application foundation."""

    bind = op.get_bind()

    # 1. PostgreSQL extension for UUID generation.
    op.execute("CREATE EXTENSION IF NOT EXISTS pgcrypto")

    # 2. Create shared enum types once.
    for enum_type in (
        user_status_enum,
        application_family_enum,
        application_status_enum,
        revision_status_enum,
        team_role_enum,
    ):
        enum_type.create(bind, checkfirst=True)

    # -----------------------------------------------------------------------
    # 3. INSTITUTIONS
    # -----------------------------------------------------------------------

    op.create_table(
        "institutions",
        sa.Column(
            "institution_id",
            sa.UUID(),
            server_default=sa.text("gen_random_uuid()"),
            nullable=False,
        ),
        sa.Column(
            "aicte_permanent_institution_id",
            sa.String(length=80),
            nullable=False,
        ),
        sa.Column(
            "institution_name",
            sa.String(length=300),
            nullable=False,
        ),
        sa.Column(
            "institution_type",
            sa.String(length=100),
            nullable=True,
        ),
        sa.Column("address_line", sa.Text(), nullable=True),
        sa.Column("district", sa.String(length=120), nullable=True),
        sa.Column("state", sa.String(length=120), nullable=True),
        sa.Column("postal_code", sa.String(length=20), nullable=True),
        sa.Column(
            "is_active",
            sa.Boolean(),
            server_default=sa.text("true"),
            nullable=False,
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("institution_id"),
        sa.UniqueConstraint("aicte_permanent_institution_id"),
    )

    # -----------------------------------------------------------------------
    # 4. REVIEW TEAMS
    # -----------------------------------------------------------------------

    op.create_table(
        "review_teams",
        sa.Column(
            "review_team_id",
            sa.UUID(),
            server_default=sa.text("gen_random_uuid()"),
            nullable=False,
        ),
        sa.Column("team_name", sa.String(length=160), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column(
            "is_active",
            sa.Boolean(),
            server_default=sa.text("true"),
            nullable=False,
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("review_team_id"),
        sa.UniqueConstraint("team_name"),
    )

    # -----------------------------------------------------------------------
    # 5. ROLES
    # -----------------------------------------------------------------------

    op.create_table(
        "roles",
        sa.Column(
            "role_id",
            sa.SmallInteger(),
            autoincrement=True,
            nullable=False,
        ),
        sa.Column("role_code", sa.String(length=40), nullable=False),
        sa.Column("role_name", sa.String(length=100), nullable=False),
        sa.CheckConstraint(
            "role_code IN ('INSTITUTION_USER', 'AUDITOR', 'LEAD_AUDITOR', 'ADMIN')",
            name="chk_role_code",
        ),
        sa.PrimaryKeyConstraint("role_id"),
        sa.UniqueConstraint("role_code"),
    )

    # Seed the four predefined platform roles.
    op.execute(
        sa.text(
            """
            INSERT INTO roles (role_code, role_name)
            VALUES
                (
                    'INSTITUTION_USER',
                    'Institution User (Applicant)'
                ),
                (
                    'AUDITOR',
                    'Auditor (Scrutiny Officer)'
                ),
                (
                    'LEAD_AUDITOR',
                    'Lead Auditor (Senior Officer)'
                ),
                (
                    'ADMIN',
                    'Admin (IT / System Admin)'
                )
            """
        )
    )

    # -----------------------------------------------------------------------
    # 6. USERS
    # -----------------------------------------------------------------------

    op.create_table(
        "users",
        sa.Column(
            "user_id",
            sa.UUID(),
            server_default=sa.text("gen_random_uuid()"),
            nullable=False,
        ),
        sa.Column("full_name", sa.String(length=200), nullable=False),
        sa.Column("email", sa.String(length=320), nullable=False),
        sa.Column("password_hash", sa.Text(), nullable=True),
        sa.Column("external_subject", sa.String(length=255), nullable=True),
        sa.Column(
            "status",
            user_status_enum,
            server_default=sa.text("'INVITED'"),
            nullable=False,
        ),
        sa.Column(
            "last_login_at",
            sa.DateTime(timezone=True),
            nullable=True,
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("user_id"),
    )

    op.create_index(
        "uq_users_email_lower",
        "users",
        [sa.literal_column("lower(email)")],
        unique=True,
    )

    op.create_index(
        "uq_users_external_subject",
        "users",
        ["external_subject"],
        unique=True,
        postgresql_where=sa.text("external_subject IS NOT NULL"),
    )

    # -----------------------------------------------------------------------
    # 7. APPLICATIONS
    #
    # NOTE:
    # current_revision_id is created as a column here.
    # Its foreign key is added after application_revisions exists.
    # -----------------------------------------------------------------------

    op.create_table(
        "applications",
        sa.Column(
            "application_id",
            sa.UUID(),
            server_default=sa.text("gen_random_uuid()"),
            nullable=False,
        ),
        sa.Column(
            "application_number",
            sa.String(length=80),
            nullable=False,
        ),
        sa.Column("institution_id", sa.UUID(), nullable=False),
        sa.Column(
            "application_family",
            application_family_enum,
            nullable=False,
        ),
        sa.Column("academic_year", sa.String(length=9), nullable=False),
        sa.Column(
            "status",
            application_status_enum,
            server_default=sa.text("'DRAFT'"),
            nullable=False,
        ),
        sa.Column("review_team_id", sa.UUID(), nullable=True),
        sa.Column("current_revision_id", sa.UUID(), nullable=True),
        sa.Column("created_by", sa.UUID(), nullable=False),
        sa.Column(
            "submitted_at",
            sa.DateTime(timezone=True),
            nullable=True,
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["created_by"],
            ["users.user_id"],
        ),
        sa.ForeignKeyConstraint(
            ["institution_id"],
            ["institutions.institution_id"],
        ),
        sa.ForeignKeyConstraint(
            ["review_team_id"],
            ["review_teams.review_team_id"],
        ),
        sa.PrimaryKeyConstraint("application_id"),
        sa.UniqueConstraint("application_number"),
    )

    op.create_index(
        "idx_applications_institution",
        "applications",
        [
            "institution_id",
            sa.literal_column("created_at DESC"),
        ],
        unique=False,
    )

    op.create_index(
        "idx_applications_team_status",
        "applications",
        ["review_team_id", "status"],
        unique=False,
    )

    # -----------------------------------------------------------------------
    # 8. INSTITUTION MEMBERSHIPS
    # -----------------------------------------------------------------------

    op.create_table(
        "institution_memberships",
        sa.Column(
            "institution_membership_id",
            sa.UUID(),
            server_default=sa.text("gen_random_uuid()"),
            nullable=False,
        ),
        sa.Column("institution_id", sa.UUID(), nullable=False),
        sa.Column("user_id", sa.UUID(), nullable=False),
        sa.Column(
            "is_active",
            sa.Boolean(),
            server_default=sa.text("true"),
            nullable=False,
        ),
        sa.Column("created_by", sa.UUID(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["created_by"],
            ["users.user_id"],
        ),
        sa.ForeignKeyConstraint(
            ["institution_id"],
            ["institutions.institution_id"],
        ),
        sa.ForeignKeyConstraint(
            ["user_id"],
            ["users.user_id"],
        ),
        sa.PrimaryKeyConstraint("institution_membership_id"),
        sa.UniqueConstraint(
            "institution_id",
            "user_id",
            name="uq_institution_membership",
        ),
    )

    # -----------------------------------------------------------------------
    # 9. REVIEW TEAM MEMBERS
    # -----------------------------------------------------------------------

    op.create_table(
        "review_team_members",
        sa.Column(
            "review_team_member_id",
            sa.UUID(),
            server_default=sa.text("gen_random_uuid()"),
            nullable=False,
        ),
        sa.Column("review_team_id", sa.UUID(), nullable=False),
        sa.Column("user_id", sa.UUID(), nullable=False),
        sa.Column("team_role", team_role_enum, nullable=False),
        sa.Column(
            "is_active",
            sa.Boolean(),
            server_default=sa.text("true"),
            nullable=False,
        ),
        sa.Column(
            "joined_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["review_team_id"],
            ["review_teams.review_team_id"],
        ),
        sa.ForeignKeyConstraint(
            ["user_id"],
            ["users.user_id"],
        ),
        sa.PrimaryKeyConstraint("review_team_member_id"),
        sa.UniqueConstraint(
            "review_team_id",
            "user_id",
            name="uq_review_team_member",
        ),
    )

    # -----------------------------------------------------------------------
    # 10. USER ROLE ASSIGNMENTS
    # -----------------------------------------------------------------------

    op.create_table(
        "user_role_assignments",
        sa.Column(
            "user_role_assignment_id",
            sa.UUID(),
            server_default=sa.text("gen_random_uuid()"),
            nullable=False,
        ),
        sa.Column("user_id", sa.UUID(), nullable=False),
        sa.Column("role_id", sa.SmallInteger(), nullable=False),
        sa.Column("institution_id", sa.UUID(), nullable=True),
        sa.Column("review_team_id", sa.UUID(), nullable=True),
        sa.Column("granted_by", sa.UUID(), nullable=True),
        sa.Column(
            "granted_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "revoked_at",
            sa.DateTime(timezone=True),
            nullable=True,
        ),
        sa.CheckConstraint(
            """
            (
                institution_id IS NOT NULL
                AND review_team_id IS NULL
            )
            OR (
                institution_id IS NULL
                AND review_team_id IS NOT NULL
            )
            OR (
                institution_id IS NULL
                AND review_team_id IS NULL
            )
            """,
            name="chk_role_scope_shape",
        ),
        sa.ForeignKeyConstraint(
            ["granted_by"],
            ["users.user_id"],
        ),
        sa.ForeignKeyConstraint(
            ["institution_id"],
            ["institutions.institution_id"],
        ),
        sa.ForeignKeyConstraint(
            ["review_team_id"],
            ["review_teams.review_team_id"],
        ),
        sa.ForeignKeyConstraint(
            ["role_id"],
            ["roles.role_id"],
        ),
        sa.ForeignKeyConstraint(
            ["user_id"],
            ["users.user_id"],
        ),
        sa.PrimaryKeyConstraint("user_role_assignment_id"),
    )

    op.create_index(
        "idx_user_role_assignments_user",
        "user_role_assignments",
        ["user_id", "revoked_at"],
        unique=False,
    )

    # -----------------------------------------------------------------------
    # 11. APPLICATION REVISIONS
    # -----------------------------------------------------------------------

    op.create_table(
        "application_revisions",
        sa.Column(
            "application_revision_id",
            sa.UUID(),
            server_default=sa.text("gen_random_uuid()"),
            nullable=False,
        ),
        sa.Column("application_id", sa.UUID(), nullable=False),
        sa.Column("revision_number", sa.Integer(), nullable=False),
        sa.Column(
            "status",
            revision_status_enum,
            server_default=sa.text("'DRAFT'"),
            nullable=False,
        ),
        sa.Column("supersedes_revision_id", sa.UUID(), nullable=True),
        sa.Column("created_by", sa.UUID(), nullable=False),
        sa.Column("submitted_by", sa.UUID(), nullable=True),
        sa.Column(
            "submitted_at",
            sa.DateTime(timezone=True),
            nullable=True,
        ),
        sa.Column("rectification_request_id", sa.UUID(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.CheckConstraint(
            "revision_number > 0",
            name="chk_revision_number_positive",
        ),
        sa.ForeignKeyConstraint(
            ["application_id"],
            ["applications.application_id"],
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["created_by"],
            ["users.user_id"],
        ),
        sa.ForeignKeyConstraint(
            ["submitted_by"],
            ["users.user_id"],
        ),
        sa.ForeignKeyConstraint(
            ["supersedes_revision_id"],
            ["application_revisions.application_revision_id"],
        ),
        sa.PrimaryKeyConstraint("application_revision_id"),
        sa.UniqueConstraint(
            "application_id",
            "revision_number",
            name="uq_application_revision_number",
        ),
        sa.UniqueConstraint(
            "application_revision_id",
            "application_id",
            name="uq_application_revision_id_application_id",
        ),
    )

    # Add the circular foreign key only after both tables exist.
    op.create_foreign_key(
        "fk_application_current_revision",
        "applications",
        "application_revisions",
        ["current_revision_id"],
        ["application_revision_id"],
    )

    # -----------------------------------------------------------------------
    # 12. APPLICATION STATUS HISTORY
    # -----------------------------------------------------------------------

    op.create_table(
        "application_status_history",
        sa.Column(
            "application_status_history_id",
            sa.UUID(),
            server_default=sa.text("gen_random_uuid()"),
            nullable=False,
        ),
        sa.Column("application_id", sa.UUID(), nullable=False),
        sa.Column("from_status", application_status_enum, nullable=True),
        sa.Column("to_status", application_status_enum, nullable=False),
        sa.Column("changed_by", sa.UUID(), nullable=True),
        sa.Column("change_reason", sa.Text(), nullable=True),
        sa.Column(
            "changed_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["application_id"],
            ["applications.application_id"],
        ),
        sa.ForeignKeyConstraint(
            ["changed_by"],
            ["users.user_id"],
        ),
        sa.PrimaryKeyConstraint("application_status_history_id"),
    )

    op.create_index(
        "idx_application_status_history",
        "application_status_history",
        [
            "application_id",
            sa.literal_column("changed_at DESC"),
        ],
        unique=False,
    )

    # -----------------------------------------------------------------------
    # 13. ROLE-SCOPE ENFORCEMENT FUNCTION
    #
    # Institution Users require an active institution membership.
    # Auditors and Lead Auditors require the matching active team membership.
    # Admin assignments must remain global.
    # -----------------------------------------------------------------------

    op.execute(
        """
        CREATE OR REPLACE FUNCTION enforce_user_role_scope()
        RETURNS TRIGGER
        LANGUAGE plpgsql
        AS $$
        DECLARE
            v_role_code VARCHAR(40);
        BEGIN
            SELECT role_code
            INTO v_role_code
            FROM roles
            WHERE role_id = NEW.role_id;

            IF v_role_code = 'INSTITUTION_USER' THEN

                IF NEW.institution_id IS NULL
                   OR NEW.review_team_id IS NOT NULL
                   OR NOT EXISTS (
                       SELECT 1
                       FROM institution_memberships im
                       WHERE im.institution_id = NEW.institution_id
                         AND im.user_id = NEW.user_id
                         AND im.is_active = TRUE
                   )
                THEN
                    RAISE EXCEPTION
                        'Institution User role requires an active membership in that institution';
                END IF;

            ELSIF v_role_code = 'AUDITOR' THEN

                IF NEW.review_team_id IS NULL
                   OR NEW.institution_id IS NOT NULL
                   OR NOT EXISTS (
                       SELECT 1
                       FROM review_team_members tm
                       WHERE tm.review_team_id = NEW.review_team_id
                         AND tm.user_id = NEW.user_id
                         AND tm.team_role = 'AUDITOR'
                         AND tm.is_active = TRUE
                   )
                THEN
                    RAISE EXCEPTION
                        'Auditor role requires active Auditor membership in a review team';
                END IF;

            ELSIF v_role_code = 'LEAD_AUDITOR' THEN

                IF NEW.review_team_id IS NULL
                   OR NEW.institution_id IS NOT NULL
                   OR NOT EXISTS (
                       SELECT 1
                       FROM review_team_members tm
                       WHERE tm.review_team_id = NEW.review_team_id
                         AND tm.user_id = NEW.user_id
                         AND tm.team_role = 'LEAD_AUDITOR'
                         AND tm.is_active = TRUE
                   )
                THEN
                    RAISE EXCEPTION
                        'Lead Auditor role requires active Lead Auditor membership in a review team';
                END IF;

            ELSIF v_role_code = 'ADMIN' THEN

                IF NEW.institution_id IS NOT NULL
                   OR NEW.review_team_id IS NOT NULL
                THEN
                    RAISE EXCEPTION
                        'Admin role is global and cannot be institution/team scoped';
                END IF;

            END IF;

            RETURN NEW;
        END;
        $$
        """
    )

    # Attach the enforcement function to role assignments.
    op.execute(
        """
        CREATE TRIGGER trg_enforce_user_role_scope
        BEFORE INSERT OR UPDATE
        ON user_role_assignments
        FOR EACH ROW
        EXECUTE FUNCTION enforce_user_role_scope()
        """
    )


# ---------------------------------------------------------------------------
# DOWNGRADE
# ---------------------------------------------------------------------------


def downgrade() -> None:
    """Remove the identity and application foundation."""

    bind = op.get_bind()

    # 1. Remove the role enforcement trigger and function.
    op.execute(
        """
        DROP TRIGGER IF EXISTS trg_enforce_user_role_scope
        ON user_role_assignments
        """
    )

    op.execute(
        """
        DROP FUNCTION IF EXISTS enforce_user_role_scope()
        """
    )

    # 2. Drop application status history.
    op.drop_index(
        "idx_application_status_history",
        table_name="application_status_history",
    )

    op.drop_table("application_status_history")

    # 3. Remove the circular foreign key before dropping revisions.
    op.drop_constraint(
        "fk_application_current_revision",
        "applications",
        type_="foreignkey",
    )

    op.drop_table("application_revisions")

    # 4. Remove user role assignments.
    op.drop_index(
        "idx_user_role_assignments_user",
        table_name="user_role_assignments",
    )

    op.drop_table("user_role_assignments")

    # 5. Remove review-team and institution memberships.
    op.drop_table("review_team_members")
    op.drop_table("institution_memberships")

    # 6. Remove application indexes and table.
    op.drop_index(
        "idx_applications_team_status",
        table_name="applications",
    )

    op.drop_index(
        "idx_applications_institution",
        table_name="applications",
    )

    op.drop_table("applications")

    # 7. Remove user indexes and table.
    op.drop_index(
        "uq_users_external_subject",
        table_name="users",
        postgresql_where=sa.text("external_subject IS NOT NULL"),
    )

    op.drop_index(
        "uq_users_email_lower",
        table_name="users",
    )

    op.drop_table("users")

    # 8. Remove role, team and institution tables.
    op.drop_table("roles")
    op.drop_table("review_teams")
    op.drop_table("institutions")

    # 9. Drop PostgreSQL enum types after their dependent tables.
    for enum_type in (
        revision_status_enum,
        team_role_enum,
        application_status_enum,
        application_family_enum,
        user_status_enum,
    ):
        enum_type.drop(bind, checkfirst=True)

    # The pgcrypto extension is intentionally retained.
    # It may be used by other database objects.

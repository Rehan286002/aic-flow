"""Add application field definitions, values and application number sequence.

Revision ID: e1a2b3c4d5e6
Revises: d7d40900ce25
Create Date: 2026-10-28

Phase 3, Task 1 Option A Database Extension:
Implements dynamic applicant self-disclosure field definitions and values
directly based on Schema v4 (lines 241-262), along with a concurrency-safe
sequence for application number allocation.
"""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

# Revision identifiers, used by Alembic.
revision: str = "e1a2b3c4d5e6"
down_revision: str | Sequence[str] | None = "d7d40900ce25"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


# Reference existing PostgreSQL application_family enum without re-creating it
application_family_enum = postgresql.ENUM(
    "NEW_INSTITUTION",
    "EXISTING_INSTITUTION",
    "UNIVERSITY",
    "OTHER",
    name="application_family",
    create_type=False,
)


def upgrade() -> None:
    """Create application_field_definitions, application_field_values, and application_number_seq."""

    # 1. Create application_field_definitions
    op.create_table(
        "application_field_definitions",
        sa.Column(
            "field_definition_id",
            sa.UUID(),
            server_default=sa.text("gen_random_uuid()"),
            nullable=False,
        ),
        sa.Column(
            "field_code",
            sa.String(length=100),
            nullable=False,
        ),
        sa.Column(
            "field_label",
            sa.String(length=200),
            nullable=False,
        ),
        sa.Column(
            "data_type",
            sa.String(length=30),
            nullable=False,
        ),
        sa.Column(
            "applies_to",
            postgresql.ARRAY(application_family_enum),
            nullable=True,
        ),
        sa.Column(
            "applicant_editable",
            sa.Boolean(),
            server_default=sa.text("true"),
            nullable=False,
        ),
        sa.Column(
            "is_active",
            sa.Boolean(),
            server_default=sa.text("true"),
            nullable=False,
        ),
        sa.CheckConstraint(
            "data_type IN ('TEXT', 'NUMBER', 'DATE', 'BOOLEAN', 'JSON', 'IDENTIFIER')",
            name="chk_field_data_type",
        ),
        sa.PrimaryKeyConstraint("field_definition_id"),
        sa.UniqueConstraint("field_code"),
    )

    # 2. Create application_field_values
    op.create_table(
        "application_field_values",
        sa.Column(
            "application_field_value_id",
            sa.UUID(),
            server_default=sa.text("gen_random_uuid()"),
            nullable=False,
        ),
        sa.Column(
            "application_revision_id",
            sa.UUID(),
            nullable=False,
        ),
        sa.Column(
            "field_definition_id",
            sa.UUID(),
            nullable=False,
        ),
        sa.Column(
            "value_json",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
        ),
        sa.Column(
            "entered_by",
            sa.UUID(),
            nullable=False,
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["application_revision_id"],
            ["application_revisions.application_revision_id"],
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["field_definition_id"],
            ["application_field_definitions.field_definition_id"],
        ),
        sa.ForeignKeyConstraint(
            ["entered_by"],
            ["users.user_id"],
        ),
        sa.PrimaryKeyConstraint("application_field_value_id"),
        sa.UniqueConstraint(
            "application_revision_id",
            "field_definition_id",
            name="uq_application_field_value_revision_field",
        ),
    )

    op.create_index(
        "idx_application_field_values_rev",
        "application_field_values",
        ["application_revision_id"],
    )

    # 3. Create concurrency-safe application numbering sequence
    op.execute(
        "CREATE SEQUENCE IF NOT EXISTS application_number_seq START WITH 1 INCREMENT BY 1"
    )


def downgrade() -> None:
    """Drop application numbering sequence, values, and definitions.

    WARNING: Downgrading after data entry permanently removes all revision-level
    self-disclosure values stored in application_field_values.
    """
    op.execute("DROP SEQUENCE IF EXISTS application_number_seq")
    op.drop_index(
        "idx_application_field_values_rev",
        table_name="application_field_values",
    )
    op.drop_table("application_field_values")
    op.drop_table("application_field_definitions")

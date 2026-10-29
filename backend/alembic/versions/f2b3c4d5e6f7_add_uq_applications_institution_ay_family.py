"""Add unique constraint on applications (institution_id, academic_year, application_family).

Revision ID: f2b3c4d5e6f7
Revises: e1a2b3c4d5e6
Create Date: 2026-10-28

Phase 3, Task 1 Concurrency Hardening:
Ensures that under concurrent requests, PostgreSQL enforces that only one application
per (institution_id, academic_year, application_family) can exist.
"""

from collections.abc import Sequence

from alembic import op

# Revision identifiers, used by Alembic.
revision: str = "f2b3c4d5e6f7"
down_revision: str | Sequence[str] | None = "e1a2b3c4d5e6"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Add uq_applications_institution_ay_family unique constraint."""
    op.create_unique_constraint(
        "uq_applications_institution_ay_family",
        "applications",
        ["institution_id", "academic_year", "application_family"],
    )


def downgrade() -> None:
    """Drop uq_applications_institution_ay_family unique constraint."""
    op.drop_constraint(
        "uq_applications_institution_ay_family",
        "applications",
        type_="unique",
    )

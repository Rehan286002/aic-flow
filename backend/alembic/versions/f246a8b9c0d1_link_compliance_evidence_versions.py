"""Link post-approval compliance evidence to an exact scanned document version.

Revision ID: f246a8b9c0d1
Revises: e135f7a8b9c0
"""
from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = "f246a8b9c0d1"
down_revision: str | Sequence[str] | None = "e135f7a8b9c0"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "compliance_obligations",
        sa.Column("evidence_document_version_id", postgresql.UUID(as_uuid=True), nullable=True),
    )
    op.add_column(
        "compliance_obligations",
        sa.Column("evidence_requirement_id", postgresql.UUID(as_uuid=True), nullable=True),
    )
    op.create_foreign_key(
        "fk_obligations_evidence_document_version",
        "compliance_obligations",
        "document_versions",
        ["evidence_document_version_id"],
        ["document_version_id"],
    )
    op.create_foreign_key(
        "fk_obligations_evidence_requirement",
        "compliance_obligations",
        "application_requirements",
        ["evidence_requirement_id"],
        ["application_requirement_id"],
    )
    op.create_index(
        "idx_obligations_evidence_version",
        "compliance_obligations",
        ["evidence_document_version_id"],
    )


def downgrade() -> None:
    op.drop_index("idx_obligations_evidence_version", table_name="compliance_obligations")
    op.drop_constraint("fk_obligations_evidence_requirement", "compliance_obligations", type_="foreignkey")
    op.drop_constraint("fk_obligations_evidence_document_version", "compliance_obligations", type_="foreignkey")
    op.drop_column("compliance_obligations", "evidence_requirement_id")
    op.drop_column("compliance_obligations", "evidence_document_version_id")

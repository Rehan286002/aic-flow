"""Add version-linked institutional document validity records.

Revision ID: b1c2d3e4f5a6
Revises: e9f8b7c6d5a4
Create Date: 2026-10-30
"""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = "b1c2d3e4f5a6"
down_revision: str | Sequence[str] | None = "e9f8b7c6d5a4"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "document_validity_records",
        sa.Column("document_validity_id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("workflow_case_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("workflow_cases.workflow_case_id", ondelete="CASCADE"), nullable=False),
        sa.Column("application_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("applications.application_id", ondelete="CASCADE"), nullable=False),
        sa.Column("institution_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("institutions.institution_id", ondelete="CASCADE"), nullable=False),
        sa.Column("document_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("documents.document_id", ondelete="RESTRICT"), nullable=False),
        sa.Column("document_version_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("document_versions.document_version_id", ondelete="RESTRICT"), nullable=False),
        sa.Column("document_type", sa.String(60), nullable=False),
        sa.Column("issuer", sa.String(300), nullable=False),
        sa.Column("valid_from", sa.Date(), nullable=True),
        sa.Column("valid_until", sa.Date(), nullable=False),
        sa.Column("document_reference", sa.String(500), nullable=False),
        sa.Column("verification_status", sa.String(32), nullable=False, server_default="PENDING_VERIFICATION"),
        sa.Column("verification_note", sa.Text(), nullable=True),
        sa.Column("replacement_of_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("document_validity_records.document_validity_id"), nullable=True),
        sa.Column("created_by", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.user_id"), nullable=False),
        sa.Column("verified_by", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.user_id"), nullable=True),
        sa.Column("verified_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.CheckConstraint("verification_status IN ('PENDING_VERIFICATION', 'VERIFIED', 'RETURNED', 'DISPUTED', 'SUPERSEDED')", name="chk_document_validity_status"),
        sa.CheckConstraint("valid_from IS NULL OR valid_until >= valid_from", name="chk_document_validity_date_order"),
        sa.UniqueConstraint("document_version_id", name="uq_document_validity_version"),
    )
    op.create_index("idx_document_validity_due_status", "document_validity_records", ["valid_until", "verification_status"])
    op.create_index("idx_document_validity_institution", "document_validity_records", ["institution_id", "valid_until"])
    op.create_index("idx_document_validity_case", "document_validity_records", ["workflow_case_id", "verification_status"])


def downgrade() -> None:
    op.drop_index("idx_document_validity_case", table_name="document_validity_records")
    op.drop_index("idx_document_validity_institution", table_name="document_validity_records")
    op.drop_index("idx_document_validity_due_status", table_name="document_validity_records")
    op.drop_table("document_validity_records")

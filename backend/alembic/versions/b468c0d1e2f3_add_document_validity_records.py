"""Add reviewed document validity and lease date records.

Revision ID: b468c0d1e2f3
Revises: a357b9c0d1e2
"""
from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = "b468c0d1e2f3"
down_revision: str | Sequence[str] | None = "a357b9c0d1e2"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "document_validity_records",
        sa.Column("document_validity_record_id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("workflow_case_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("workflow_cases.workflow_case_id", ondelete="CASCADE"), nullable=False),
        sa.Column("application_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("applications.application_id", ondelete="CASCADE"), nullable=False),
        sa.Column("application_requirement_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("application_requirements.application_requirement_id", ondelete="RESTRICT"), nullable=False),
        sa.Column("document_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("documents.document_id", ondelete="RESTRICT"), nullable=False),
        sa.Column("document_version_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("document_versions.document_version_id", ondelete="RESTRICT"), nullable=False),
        sa.Column("supersedes_validity_record_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("document_validity_records.document_validity_record_id"), nullable=True),
        sa.Column("validity_type", sa.String(48), nullable=False),
        sa.Column("status", sa.String(24), nullable=False, server_default="PENDING_REVIEW"),
        sa.Column("issue_date", sa.Date(), nullable=True),
        sa.Column("valid_from", sa.Date(), nullable=True),
        sa.Column("valid_until", sa.Date(), nullable=True),
        sa.Column("review_due_at", sa.Date(), nullable=True),
        sa.Column("lease_start_date", sa.Date(), nullable=True),
        sa.Column("lease_end_date", sa.Date(), nullable=True),
        sa.Column("maximum_course_duration_years", sa.Integer(), nullable=True),
        sa.Column("lease_minimum_term_met", sa.Boolean(), nullable=True),
        sa.Column("lease_live_term_met_at_submission", sa.Boolean(), nullable=True),
        sa.Column("lease_eoa_cutoff_year_triggered", sa.Boolean(), nullable=True),
        sa.Column("lease_assessed_on", sa.Date(), nullable=True),
        sa.Column("validity_basis_reference", sa.Text(), nullable=False),
        sa.Column("submitted_by", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.user_id"), nullable=False),
        sa.Column("submitted_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("reviewed_by", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.user_id"), nullable=True),
        sa.Column("reviewed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("review_note", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.CheckConstraint("validity_type IN ('LEASE_DEED', 'STRUCTURAL_STABILITY_CERTIFICATE', 'FIRE_SAFETY_CERTIFICATE', 'BUILDING_COMPLETION_CERTIFICATE', 'ISSUER_DATED_DOCUMENT')", name="chk_document_validity_type"),
        sa.CheckConstraint("status IN ('PENDING_REVIEW', 'VERIFIED', 'RETURNED', 'SUPERSEDED')", name="chk_document_validity_status"),
        sa.CheckConstraint("valid_until IS NULL OR valid_from IS NULL OR valid_until >= valid_from", name="chk_document_validity_date_order"),
        sa.CheckConstraint("validity_type <> 'LEASE_DEED' OR (lease_start_date IS NOT NULL AND lease_end_date IS NOT NULL AND maximum_course_duration_years IS NOT NULL AND maximum_course_duration_years > 0)", name="chk_document_validity_lease_details"),
        sa.CheckConstraint("validity_type <> 'STRUCTURAL_STABILITY_CERTIFICATE' OR (issue_date IS NOT NULL AND valid_until IS NOT NULL)", name="chk_document_validity_structural_dates"),
        sa.CheckConstraint("validity_type <> 'FIRE_SAFETY_CERTIFICATE' OR (issue_date IS NOT NULL AND valid_until IS NOT NULL AND length(trim(validity_basis_reference)) > 0)", name="chk_document_validity_fire_dates"),
        sa.CheckConstraint("status <> 'VERIFIED' OR (reviewed_by IS NOT NULL AND reviewed_at IS NOT NULL)", name="chk_document_validity_reviewed"),
        sa.UniqueConstraint("document_version_id", name="uq_document_validity_document_version"),
    )
    op.create_index("idx_document_validity_due", "document_validity_records", ["status", "valid_until"])
    op.create_index("idx_document_validity_case_type", "document_validity_records", ["workflow_case_id", "validity_type", "status"])


def downgrade() -> None:
    op.drop_index("idx_document_validity_case_type", table_name="document_validity_records")
    op.drop_index("idx_document_validity_due", table_name="document_validity_records")
    op.drop_table("document_validity_records")

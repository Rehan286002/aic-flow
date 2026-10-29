"""Add Executive Committee decision and Speaking Order record.

Revision ID: d924e5f6a7b8
Revises: c813d9e2f4a5
"""
from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = "d924e5f6a7b8"
down_revision: str | Sequence[str] | None = "c813d9e2f4a5"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "executive_committee_decisions",
        sa.Column("executive_committee_decision_id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("workflow_case_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("workflow_cases.workflow_case_id", ondelete="CASCADE"), nullable=False),
        sa.Column("application_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("applications.application_id", ondelete="CASCADE"), nullable=False),
        sa.Column("outcome_code", sa.String(32), nullable=False),
        sa.Column("decision_reference", sa.String(180), nullable=False),
        sa.Column("decision_reasons", sa.Text(), nullable=False),
        sa.Column("speaking_order_reference", sa.String(180), nullable=False),
        sa.Column("speaking_order_uploaded_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("appeal_deadline_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("recorded_by", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.user_id"), nullable=False),
        sa.Column("recorded_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.UniqueConstraint("workflow_case_id", name="uq_ec_decisions_workflow_case"),
        sa.CheckConstraint("outcome_code IN ('APPROVED', 'APPROVED_WITH_CONDITIONS', 'REJECTED')", name="chk_ec_decision_outcome"),
        sa.CheckConstraint("length(trim(decision_reference)) >= 2 AND length(trim(decision_reasons)) >= 15 AND length(trim(speaking_order_reference)) >= 2", name="chk_ec_decision_required_text"),
        sa.CheckConstraint("appeal_deadline_at = speaking_order_uploaded_at + INTERVAL '7 days'", name="chk_ec_decision_appeal_deadline"),
    )


def downgrade() -> None:
    op.drop_table("executive_committee_decisions")

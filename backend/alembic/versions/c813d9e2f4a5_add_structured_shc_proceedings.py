"""Add structured Standing Hearing Committee proceedings.

Revision ID: c813d9e2f4a5
Revises: b712c8a1d3e4
"""
from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = "c813d9e2f4a5"
down_revision: str | Sequence[str] | None = "b712c8a1d3e4"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "shc_proceedings",
        sa.Column("shc_proceeding_id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("workflow_case_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("workflow_cases.workflow_case_id", ondelete="CASCADE"), nullable=False),
        sa.Column("application_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("applications.application_id", ondelete="CASCADE"), nullable=False),
        sa.Column("status", sa.String(32), nullable=False, server_default="PREPARATION"),
        sa.Column("notice_reference", sa.String(180), nullable=True),
        sa.Column("hearing_mode", sa.String(20), nullable=True),
        sa.Column("hearing_scheduled_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("hearing_details", sa.Text(), nullable=True),
        sa.Column("official_schedule_reference", sa.String(180), nullable=True),
        sa.Column("schedule_revision", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("institution_submission_reference", sa.String(500), nullable=True),
        sa.Column("representative_one_name", sa.String(160), nullable=True),
        sa.Column("representative_one_designation", sa.String(160), nullable=True),
        sa.Column("representative_two_name", sa.String(160), nullable=True),
        sa.Column("representative_two_designation", sa.String(160), nullable=True),
        sa.Column("hearing_summary", sa.Text(), nullable=True),
        sa.Column("hearing_recorded_by", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.user_id"), nullable=True),
        sa.Column("hearing_recorded_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("recommendation_code", sa.String(40), nullable=True),
        sa.Column("recommendation_text", sa.Text(), nullable=True),
        sa.Column("recommendation_reference", sa.String(180), nullable=True),
        sa.Column("recommendation_recorded_by", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.user_id"), nullable=True),
        sa.Column("recommendation_recorded_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_by", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.user_id"), nullable=False),
        sa.Column("updated_by", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.user_id"), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.UniqueConstraint("workflow_case_id", name="uq_shc_proceedings_workflow_case"),
        sa.CheckConstraint("status IN ('PREPARATION', 'SCHEDULED', 'HEARING_RECORDED', 'RECOMMENDATION_RECORDED')", name="chk_shc_proceedings_status"),
        sa.CheckConstraint("hearing_mode IS NULL OR hearing_mode IN ('ONLINE', 'IN_PERSON')", name="chk_shc_proceedings_hearing_mode"),
        sa.CheckConstraint("status <> 'SCHEDULED' OR (hearing_scheduled_at IS NOT NULL AND hearing_mode IS NOT NULL AND hearing_details IS NOT NULL AND schedule_revision > 0)", name="chk_shc_proceedings_schedule"),
        sa.CheckConstraint("status NOT IN ('HEARING_RECORDED', 'RECOMMENDATION_RECORDED') OR (hearing_recorded_at IS NOT NULL AND representative_one_name IS NOT NULL AND representative_two_name IS NOT NULL AND hearing_summary IS NOT NULL)", name="chk_shc_proceedings_hearing_record"),
        sa.CheckConstraint("status <> 'RECOMMENDATION_RECORDED' OR (recommendation_code IS NOT NULL AND recommendation_text IS NOT NULL AND recommendation_recorded_at IS NOT NULL AND recommendation_recorded_by IS NOT NULL)", name="chk_shc_proceedings_recommendation"),
        sa.CheckConstraint("recommendation_code IS NULL OR recommendation_code IN ('COMPLIANCE_REVIEWED', 'FURTHER_COMPLIANCE_REQUIRED', 'DEFICIENCIES_REMAIN', 'INCONCLUSIVE')", name="chk_shc_proceedings_recommendation_code"),
    )
    op.create_index("idx_shc_proceedings_status_hearing", "shc_proceedings", ["status", "hearing_scheduled_at"])


def downgrade() -> None:
    op.drop_index("idx_shc_proceedings_status_hearing", table_name="shc_proceedings")
    op.drop_table("shc_proceedings")

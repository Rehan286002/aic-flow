"""Add structured EVC visit coordination and report records.

Revision ID: b712c8a1d3e4
Revises: e9f8b7c6d5a4
"""
from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = "b712c8a1d3e4"
down_revision: str | Sequence[str] | None = "e9f8b7c6d5a4"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "evc_visits",
        sa.Column("evc_visit_id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("workflow_case_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("workflow_cases.workflow_case_id", ondelete="CASCADE"), nullable=False),
        sa.Column("application_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("applications.application_id", ondelete="CASCADE"), nullable=False),
        sa.Column("status", sa.String(30), nullable=False, server_default="DETAILS_REQUIRED"),
        sa.Column("visit_mode", sa.String(20), nullable=True),
        sa.Column("scheduled_start_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("scheduled_end_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("venue_or_meeting_details", sa.Text(), nullable=True),
        sa.Column("official_schedule_reference", sa.String(180), nullable=True),
        sa.Column("institution_contact_name", sa.String(160), nullable=True),
        sa.Column("institution_contact_email", sa.String(254), nullable=True),
        sa.Column("coordination_note", sa.Text(), nullable=True),
        sa.Column("schedule_revision", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("report_reference", sa.String(180), nullable=True),
        sa.Column("report_summary", sa.Text(), nullable=True),
        sa.Column("report_outcome", sa.String(40), nullable=True),
        sa.Column("report_recorded_by", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.user_id"), nullable=True),
        sa.Column("report_recorded_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("cancellation_reason", sa.Text(), nullable=True),
        sa.Column("created_by", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.user_id"), nullable=False),
        sa.Column("updated_by", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.user_id"), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.UniqueConstraint("workflow_case_id", name="uq_evc_visits_workflow_case"),
        sa.CheckConstraint("status IN ('DETAILS_REQUIRED', 'SCHEDULED', 'COMPLETED', 'CANCELLED')", name="chk_evc_visits_status"),
        sa.CheckConstraint("visit_mode IS NULL OR visit_mode IN ('ONLINE', 'OFFLINE')", name="chk_evc_visits_mode"),
        sa.CheckConstraint("scheduled_end_at IS NULL OR scheduled_start_at IS NULL OR scheduled_end_at > scheduled_start_at", name="chk_evc_visits_time_order"),
        sa.CheckConstraint("status <> 'SCHEDULED' OR (visit_mode IS NOT NULL AND scheduled_start_at IS NOT NULL AND venue_or_meeting_details IS NOT NULL AND schedule_revision > 0)", name="chk_evc_visits_scheduled_details"),
        sa.CheckConstraint("report_outcome IS NULL OR report_outcome IN ('NO_DEFICIENCY_RECORDED', 'DEFICIENCIES_OBSERVED', 'FOLLOW_UP_REQUIRED', 'INCONCLUSIVE')", name="chk_evc_visits_report_outcome"),
        sa.CheckConstraint("status <> 'COMPLETED' OR (report_reference IS NOT NULL AND report_summary IS NOT NULL AND report_outcome IS NOT NULL AND report_recorded_at IS NOT NULL AND report_recorded_by IS NOT NULL)", name="chk_evc_visits_completed_report"),
        sa.CheckConstraint("status <> 'CANCELLED' OR cancellation_reason IS NOT NULL", name="chk_evc_visits_cancellation_reason"),
    )
    op.create_index("idx_evc_visits_status_start", "evc_visits", ["status", "scheduled_start_at"])

    # Preserve legacy schedule events without inventing a visit date or mode.
    op.execute(sa.text("""
        INSERT INTO evc_visits (
            workflow_case_id, application_id, status, schedule_revision,
            created_by, created_at, updated_at
        )
        SELECT DISTINCT ON (event.workflow_case_id)
            event.workflow_case_id,
            event.application_id,
            'DETAILS_REQUIRED',
            0,
            event.actor_user_id,
            event.occurred_at,
            event.occurred_at
        FROM workflow_events AS event
        JOIN workflow_cases AS workflow_case
          ON workflow_case.workflow_case_id = event.workflow_case_id
        WHERE event.event_type = 'EVC_VISIT_SCHEDULED'
          AND workflow_case.current_stage IN ('EVC_COORDINATION', 'EVC_SCHEDULED')
        ORDER BY event.workflow_case_id, event.occurred_at DESC
        ON CONFLICT (workflow_case_id) DO NOTHING
    """))


def downgrade() -> None:
    op.drop_index("idx_evc_visits_status_start", table_name="evc_visits")
    op.drop_table("evc_visits")

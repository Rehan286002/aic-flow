"""Add configurable, idempotent deadline reminders and escalation dispatches.

Revision ID: a357b9c0d1e2
Revises: f246a8b9c0d1
"""
from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = "a357b9c0d1e2"
down_revision: str | Sequence[str] | None = "f246a8b9c0d1"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


DEFAULT_POLICIES = [
    ("CASE_DUE_3D_ASSIGNEE", "WORKFLOW_CASE", -3, "ASSIGNEE", "INFO", "Application deadline approaching", "{application_number} is due on {due_date}. Review the case action assigned to you."),
    ("CASE_DUE_1D_ASSIGNEE", "WORKFLOW_CASE", -1, "ASSIGNEE", "WARNING", "Application deadline tomorrow", "{application_number} is due on {due_date}. Complete the pending case action."),
    ("CASE_OVERDUE_1D_SUPERVISORS", "WORKFLOW_CASE", 1, "SUPERVISORS", "WARNING", "Application deadline passed", "{application_number} passed its due date on {due_date}. Supervisory follow-up is required."),
    ("CASE_OVERDUE_3D_SUPERVISORS", "WORKFLOW_CASE", 3, "SUPERVISORS", "CRITICAL", "Application remains overdue", "{application_number} remains overdue since {due_date}. Review pendency and officer assignment."),
    ("OBLIGATION_DUE_7D_INSTITUTION", "OBLIGATION", -7, "INSTITUTION", "INFO", "Approval condition due in seven days", "{condition_title} for {application_number} is due on {due_date}. Submit the required compliance evidence."),
    ("OBLIGATION_DUE_1D_INSTITUTION", "OBLIGATION", -1, "INSTITUTION", "WARNING", "Approval condition due tomorrow", "{condition_title} for {application_number} is due on {due_date}. Submit the required compliance evidence."),
    ("OBLIGATION_DUE_TODAY_INSTITUTION", "OBLIGATION", 0, "INSTITUTION", "WARNING", "Approval condition due today", "{condition_title} for {application_number} is due today. Submit the required compliance evidence."),
    ("OBLIGATION_OVERDUE_3D_SUPERVISORS", "OBLIGATION", 3, "SUPERVISORS", "WARNING", "Approval condition overdue", "{condition_title} for {application_number} has been overdue since {due_date}. Review the institution's compliance status."),
    ("OBLIGATION_OVERDUE_7D_SUPERVISORS", "OBLIGATION", 7, "SUPERVISORS", "CRITICAL", "Approval condition requires escalation", "{condition_title} for {application_number} remains overdue since {due_date}. Supervisory escalation is required."),
]


def upgrade() -> None:
    op.create_table(
        "workflow_reminder_policies",
        sa.Column("reminder_policy_id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("policy_code", sa.String(80), nullable=False, unique=True),
        sa.Column("target_type", sa.String(24), nullable=False),
        sa.Column("days_from_due", sa.Integer(), nullable=False),
        sa.Column("recipient_group", sa.String(24), nullable=False),
        sa.Column("severity", sa.String(20), nullable=False, server_default="INFO"),
        sa.Column("title_template", sa.String(180), nullable=False),
        sa.Column("body_template", sa.Text(), nullable=False),
        sa.Column("is_enabled", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.CheckConstraint("target_type IN ('WORKFLOW_CASE', 'OBLIGATION')", name="chk_reminder_policy_target"),
        sa.CheckConstraint("recipient_group IN ('INSTITUTION', 'ASSIGNEE', 'SUPERVISORS')", name="chk_reminder_policy_recipient"),
        sa.CheckConstraint("severity IN ('INFO', 'WARNING', 'CRITICAL')", name="chk_reminder_policy_severity"),
        sa.CheckConstraint("days_from_due BETWEEN -365 AND 365", name="chk_reminder_policy_days"),
        sa.UniqueConstraint("target_type", "days_from_due", "recipient_group", name="uq_reminder_policy_schedule"),
    )
    op.create_index("idx_reminder_policy_enabled", "workflow_reminder_policies", ["is_enabled", "target_type"])

    op.create_table(
        "workflow_reminder_dispatches",
        sa.Column("reminder_dispatch_id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("reminder_policy_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("workflow_reminder_policies.reminder_policy_id", ondelete="RESTRICT"), nullable=False),
        sa.Column("target_type", sa.String(24), nullable=False),
        sa.Column("workflow_case_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("workflow_cases.workflow_case_id", ondelete="CASCADE"), nullable=True),
        sa.Column("obligation_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("compliance_obligations.obligation_id", ondelete="CASCADE"), nullable=True),
        sa.Column("dispatch_key", sa.String(180), nullable=False),
        sa.Column("scheduled_for", sa.DateTime(timezone=True), nullable=False),
        sa.Column("dispatched_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("recipient_count", sa.Integer(), nullable=False, server_default="0"),
        sa.CheckConstraint("target_type IN ('WORKFLOW_CASE', 'OBLIGATION')", name="chk_reminder_dispatch_target"),
        sa.CheckConstraint("(target_type = 'WORKFLOW_CASE' AND workflow_case_id IS NOT NULL AND obligation_id IS NULL) OR (target_type = 'OBLIGATION' AND obligation_id IS NOT NULL AND workflow_case_id IS NULL)", name="chk_reminder_dispatch_target_link"),
        sa.CheckConstraint("recipient_count >= 0", name="chk_reminder_dispatch_recipient_count"),
        sa.UniqueConstraint("dispatch_key", name="uq_reminder_dispatch_key"),
        sa.UniqueConstraint("reminder_policy_id", "workflow_case_id", name="uq_reminder_dispatch_policy_case"),
        sa.UniqueConstraint("reminder_policy_id", "obligation_id", name="uq_reminder_dispatch_policy_obligation"),
    )
    op.create_index("idx_reminder_dispatch_dispatched", "workflow_reminder_dispatches", ["dispatched_at"])

    policies = sa.table(
        "workflow_reminder_policies",
        sa.column("policy_code", sa.String),
        sa.column("target_type", sa.String),
        sa.column("days_from_due", sa.Integer),
        sa.column("recipient_group", sa.String),
        sa.column("severity", sa.String),
        sa.column("title_template", sa.String),
        sa.column("body_template", sa.Text),
        sa.column("is_enabled", sa.Boolean),
    )
    op.bulk_insert(
        policies,
        [
            {
                "policy_code": code,
                "target_type": target,
                "days_from_due": days,
                "recipient_group": group,
                "severity": severity,
                "title_template": title,
                "body_template": body,
                "is_enabled": True,
            }
            for code, target, days, group, severity, title, body in DEFAULT_POLICIES
        ],
    )


def downgrade() -> None:
    op.drop_index("idx_reminder_dispatch_dispatched", table_name="workflow_reminder_dispatches")
    op.drop_table("workflow_reminder_dispatches")
    op.drop_index("idx_reminder_policy_enabled", table_name="workflow_reminder_policies")
    op.drop_table("workflow_reminder_policies")

"""Extend reminder dispatches to verified document validity records.

Revision ID: c579d1e2f3a4
Revises: b468c0d1e2f3
"""
from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = "c579d1e2f3a4"
down_revision: str | Sequence[str] | None = "b468c0d1e2f3"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


DEFAULT_POLICIES = [
    ("DOC_VALIDITY_90D_INSTITUTION", -90, "INSTITUTION", "INFO", "Document validity expires in 90 days", "{condition_title} for {application_number} is due for renewal on {due_date}. Start the replacement or renewal process."),
    ("DOC_VALIDITY_30D_INSTITUTION", -30, "INSTITUTION", "WARNING", "Document validity expires in 30 days", "{condition_title} for {application_number} is due for renewal on {due_date}. Upload the renewed document and validity dates."),
    ("DOC_VALIDITY_7D_INSTITUTION", -7, "INSTITUTION", "WARNING", "Document validity expires in seven days", "{condition_title} for {application_number} expires on {due_date}. Complete the renewal process."),
    ("DOC_VALIDITY_OVERDUE_1D_SUPERVISORS", 1, "SUPERVISORS", "WARNING", "Regulatory document validity has expired", "{condition_title} for {application_number} expired on {due_date}. Review the institution's current compliance position."),
    ("DOC_VALIDITY_OVERDUE_30D_SUPERVISORS", 30, "SUPERVISORS", "CRITICAL", "Document validity requires escalation", "{condition_title} for {application_number} remains expired since {due_date}. Supervisory follow-up is required."),
]


def upgrade() -> None:
    op.add_column(
        "workflow_reminder_dispatches",
        sa.Column("document_validity_record_id", postgresql.UUID(as_uuid=True), nullable=True),
    )
    op.create_foreign_key(
        "fk_reminder_dispatch_document_validity",
        "workflow_reminder_dispatches",
        "document_validity_records",
        ["document_validity_record_id"],
        ["document_validity_record_id"],
        ondelete="CASCADE",
    )

    op.drop_constraint("chk_reminder_policy_target", "workflow_reminder_policies", type_="check")
    op.create_check_constraint(
        "chk_reminder_policy_target",
        "workflow_reminder_policies",
        "target_type IN ('WORKFLOW_CASE', 'OBLIGATION', 'DOCUMENT_VALIDITY')",
    )
    op.drop_constraint("chk_reminder_dispatch_target", "workflow_reminder_dispatches", type_="check")
    op.create_check_constraint(
        "chk_reminder_dispatch_target",
        "workflow_reminder_dispatches",
        "target_type IN ('WORKFLOW_CASE', 'OBLIGATION', 'DOCUMENT_VALIDITY')",
    )
    op.drop_constraint("chk_reminder_dispatch_target_link", "workflow_reminder_dispatches", type_="check")
    op.create_check_constraint(
        "chk_reminder_dispatch_target_link",
        "workflow_reminder_dispatches",
        "(target_type = 'WORKFLOW_CASE' AND workflow_case_id IS NOT NULL AND obligation_id IS NULL AND document_validity_record_id IS NULL) OR "
        "(target_type = 'OBLIGATION' AND obligation_id IS NOT NULL AND workflow_case_id IS NULL AND document_validity_record_id IS NULL) OR "
        "(target_type = 'DOCUMENT_VALIDITY' AND document_validity_record_id IS NOT NULL AND workflow_case_id IS NULL AND obligation_id IS NULL)",
    )
    op.create_unique_constraint(
        "uq_reminder_dispatch_policy_validity",
        "workflow_reminder_dispatches",
        ["reminder_policy_id", "document_validity_record_id"],
    )

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
                "target_type": "DOCUMENT_VALIDITY",
                "days_from_due": days,
                "recipient_group": group,
                "severity": severity,
                "title_template": title,
                "body_template": body,
                "is_enabled": True,
            }
            for code, days, group, severity, title, body in DEFAULT_POLICIES
        ],
    )


def downgrade() -> None:
    op.execute("DELETE FROM workflow_reminder_policies WHERE target_type = 'DOCUMENT_VALIDITY'")
    op.drop_constraint("uq_reminder_dispatch_policy_validity", "workflow_reminder_dispatches", type_="unique")
    op.drop_constraint("chk_reminder_dispatch_target_link", "workflow_reminder_dispatches", type_="check")
    op.create_check_constraint(
        "chk_reminder_dispatch_target_link",
        "workflow_reminder_dispatches",
        "(target_type = 'WORKFLOW_CASE' AND workflow_case_id IS NOT NULL AND obligation_id IS NULL) OR "
        "(target_type = 'OBLIGATION' AND obligation_id IS NOT NULL AND workflow_case_id IS NULL)",
    )
    op.drop_constraint("chk_reminder_dispatch_target", "workflow_reminder_dispatches", type_="check")
    op.create_check_constraint(
        "chk_reminder_dispatch_target",
        "workflow_reminder_dispatches",
        "target_type IN ('WORKFLOW_CASE', 'OBLIGATION')",
    )
    op.drop_constraint("chk_reminder_policy_target", "workflow_reminder_policies", type_="check")
    op.create_check_constraint(
        "chk_reminder_policy_target",
        "workflow_reminder_policies",
        "target_type IN ('WORKFLOW_CASE', 'OBLIGATION')",
    )
    op.drop_constraint("fk_reminder_dispatch_document_validity", "workflow_reminder_dispatches", type_="foreignkey")
    op.drop_column("workflow_reminder_dispatches", "document_validity_record_id")

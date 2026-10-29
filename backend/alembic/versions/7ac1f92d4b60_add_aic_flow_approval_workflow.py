"""Add AIC-Flow case lifecycle, obligations and notifications.

Revision ID: 7ac1f92d4b60
Revises: f2b3c4d5e6f7
"""
from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = "7ac1f92d4b60"
down_revision: str | Sequence[str] | None = "f2b3c4d5e6f7"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

ROLE_ROWS = [
    ("INTAKE_OFFICER", "Intake / Registry Officer"),
    ("SCRUTINY_OFFICER", "Scrutiny / Processing Officer"),
    ("REGIONAL_OFFICER", "Regional Officer / Coordinator"),
    ("EVC_COORDINATOR", "EVC Coordinator"),
    ("EVC_MEMBER", "EVC Assigned Participant"),
    ("COMMITTEE_SECRETARIAT", "Committee Secretariat / Panel Participant"),
    ("BUREAU_SUPERVISOR", "Bureau Supervisor / Senior Officer"),
    ("COMPETENT_AUTHORITY", "Competent Authority"),
    ("REGULATORY_POLICY_PUBLISHER", "Regulatory Policy Publisher / Approver"),
]


def upgrade() -> None:
    bind = op.get_bind()

    for value in ["APPROVED", "APPROVED_WITH_CONDITIONS", "REJECTED"]:
        op.execute(sa.text(f"ALTER TYPE application_status ADD VALUE IF NOT EXISTS '{value}'"))

    # Extend the existing enum in place; existing AUDITOR/LEAD_AUDITOR assignments remain valid.
    for value in [
        "INTAKE_OFFICER", "SCRUTINY_OFFICER", "REGIONAL_OFFICER",
        "EVC_COORDINATOR", "EVC_MEMBER", "COMMITTEE_SECRETARIAT",
        "BUREAU_SUPERVISOR", "COMPETENT_AUTHORITY",
    ]:
        op.execute(sa.text(f"ALTER TYPE team_role ADD VALUE IF NOT EXISTS '{value}'"))

    op.add_column(
        "applications",
        sa.Column("process_type", sa.String(length=60), nullable=False, server_default="EOA_SELF_DISCLOSURE"),
    )
    op.drop_constraint("uq_applications_institution_ay_family", "applications", type_="unique")
    op.create_unique_constraint(
        "uq_applications_institution_ay_family_process",
        "applications",
        ["institution_id", "academic_year", "application_family", "process_type"],
    )

    op.drop_constraint("chk_role_code", "roles", type_="check")
    allowed = ["INSTITUTION_USER", "AUDITOR", "LEAD_AUDITOR", "ADMIN", *[r[0] for r in ROLE_ROWS]]
    op.create_check_constraint(
        "chk_role_code", "roles", "role_code IN (" + ", ".join(repr(v) for v in allowed) + ")"
    )
    for code, name in ROLE_ROWS:
        bind.execute(
            sa.text("INSERT INTO roles (role_code, role_name) VALUES (:code, :name) ON CONFLICT (role_code) DO NOTHING"),
            {"code": code, "name": name},
        )

    op.create_table(
        "workflow_cases",
        sa.Column("workflow_case_id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("application_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("applications.application_id", ondelete="CASCADE"), nullable=False),
        sa.Column("process_type", sa.String(60), nullable=False, server_default="EOA_SELF_DISCLOSURE"),
        sa.Column("route_code", sa.String(100), nullable=False, server_default="ROUTE_PENDING_CONFIRMATION"),
        sa.Column("regulatory_version", sa.String(80), nullable=False, server_default="APH_2024_2027_BASELINE"),
        sa.Column("route_snapshot", postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column("current_stage", sa.String(50), nullable=False, server_default="DRAFT"),
        sa.Column("assigned_role_code", sa.String(40), nullable=True),
        sa.Column("assigned_user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.user_id"), nullable=True),
        sa.Column("due_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("stage_entered_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("created_by", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.user_id"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.UniqueConstraint("application_id", name="uq_workflow_cases_application"),
    )
    op.create_index("idx_workflow_cases_stage_due", "workflow_cases", ["current_stage", "due_at"])
    op.create_index("idx_workflow_cases_assigned", "workflow_cases", ["assigned_role_code", "assigned_user_id"])

    op.create_table(
        "workflow_events",
        sa.Column("workflow_event_id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("workflow_case_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("workflow_cases.workflow_case_id", ondelete="CASCADE"), nullable=False),
        sa.Column("application_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("applications.application_id", ondelete="CASCADE"), nullable=False),
        sa.Column("event_type", sa.String(60), nullable=False),
        sa.Column("from_stage", sa.String(50), nullable=True),
        sa.Column("to_stage", sa.String(50), nullable=True),
        sa.Column("summary", sa.Text(), nullable=False),
        sa.Column("event_payload", postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column("actor_user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.user_id"), nullable=False),
        sa.Column("occurred_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )
    op.create_index("idx_workflow_events_case_time", "workflow_events", ["workflow_case_id", "occurred_at"])
    op.create_index("idx_workflow_events_actor_time", "workflow_events", ["actor_user_id", "occurred_at"])

    op.create_table(
        "compliance_obligations",
        sa.Column("obligation_id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("workflow_case_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("workflow_cases.workflow_case_id", ondelete="CASCADE"), nullable=False),
        sa.Column("application_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("applications.application_id", ondelete="CASCADE"), nullable=False),
        sa.Column("condition_code", sa.String(60), nullable=True),
        sa.Column("title", sa.String(220), nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("source_condition", sa.Text(), nullable=False),
        sa.Column("due_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("status", sa.String(30), nullable=False, server_default="OPEN"),
        sa.Column("evidence_document_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("documents.document_id"), nullable=True),
        sa.Column("evidence_reference", sa.String(500), nullable=True),
        sa.Column("verification_note", sa.Text(), nullable=True),
        sa.Column("created_by", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.user_id"), nullable=False),
        sa.Column("verified_by", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.user_id"), nullable=True),
        sa.Column("submitted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("verified_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.CheckConstraint("status IN ('OPEN', 'EVIDENCE_SUBMITTED', 'UNDER_VERIFICATION', 'VERIFIED', 'RETURNED', 'CLOSED')", name="chk_compliance_obligation_status"),
    )
    op.create_index("idx_obligations_due_status", "compliance_obligations", ["due_at", "status"])
    op.create_index("idx_obligations_case", "compliance_obligations", ["workflow_case_id", "status"])

    op.create_table(
        "in_app_notifications",
        sa.Column("notification_id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("recipient_user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.user_id", ondelete="CASCADE"), nullable=False),
        sa.Column("application_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("applications.application_id", ondelete="CASCADE"), nullable=True),
        sa.Column("workflow_event_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("workflow_events.workflow_event_id", ondelete="CASCADE"), nullable=True),
        sa.Column("event_key", sa.String(180), nullable=False),
        sa.Column("title", sa.String(180), nullable=False),
        sa.Column("body", sa.Text(), nullable=False),
        sa.Column("severity", sa.String(20), nullable=False, server_default="INFO"),
        sa.Column("read_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("acknowledged_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.UniqueConstraint("recipient_user_id", "event_key", name="uq_notification_recipient_event"),
    )
    op.create_index("idx_notifications_recipient_read_time", "in_app_notifications", ["recipient_user_id", "read_at", "created_at"])


def downgrade() -> None:
    op.drop_index("idx_notifications_recipient_read_time", table_name="in_app_notifications")
    op.drop_table("in_app_notifications")
    op.drop_index("idx_obligations_case", table_name="compliance_obligations")
    op.drop_index("idx_obligations_due_status", table_name="compliance_obligations")
    op.drop_table("compliance_obligations")
    op.drop_index("idx_workflow_events_actor_time", table_name="workflow_events")
    op.drop_index("idx_workflow_events_case_time", table_name="workflow_events")
    op.drop_table("workflow_events")
    op.drop_index("idx_workflow_cases_assigned", table_name="workflow_cases")
    op.drop_index("idx_workflow_cases_stage_due", table_name="workflow_cases")
    op.drop_table("workflow_cases")
    op.drop_constraint("chk_role_code", "roles", type_="check")
    op.create_check_constraint("chk_role_code", "roles", "role_code IN ('INSTITUTION_USER', 'AUDITOR', 'LEAD_AUDITOR', 'ADMIN')")
    for code, _name in ROLE_ROWS:
        op.execute(sa.text("DELETE FROM roles WHERE role_code = :code").bindparams(code=code))
    op.drop_constraint("uq_applications_institution_ay_family_process", "applications", type_="unique")
    op.create_unique_constraint("uq_applications_institution_ay_family", "applications", ["institution_id", "academic_year", "application_family"])
    op.drop_column("applications", "process_type")
    # PostgreSQL enum values cannot safely be removed in a transactional downgrade.

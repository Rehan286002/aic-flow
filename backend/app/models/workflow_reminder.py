import uuid
from datetime import datetime

from sqlalchemy import Boolean, CheckConstraint, DateTime, Index, Integer, String, Text, UniqueConstraint, func, text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.session import Base


class WorkflowReminderPolicy(Base):
    """Editable schedule rule for application and compliance deadline notifications."""

    __tablename__ = "workflow_reminder_policies"
    __table_args__ = (
        CheckConstraint("target_type IN ('WORKFLOW_CASE', 'OBLIGATION')", name="chk_reminder_policy_target"),
        CheckConstraint("recipient_group IN ('INSTITUTION', 'ASSIGNEE', 'SUPERVISORS')", name="chk_reminder_policy_recipient"),
        CheckConstraint("severity IN ('INFO', 'WARNING', 'CRITICAL')", name="chk_reminder_policy_severity"),
        CheckConstraint("days_from_due BETWEEN -365 AND 365", name="chk_reminder_policy_days"),
        UniqueConstraint("target_type", "days_from_due", "recipient_group", name="uq_reminder_policy_schedule"),
        Index("idx_reminder_policy_enabled", "is_enabled", "target_type"),
    )

    reminder_policy_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()")
    )
    policy_code: Mapped[str] = mapped_column(String(80), nullable=False, unique=True)
    target_type: Mapped[str] = mapped_column(String(24), nullable=False)
    days_from_due: Mapped[int] = mapped_column(Integer, nullable=False)
    recipient_group: Mapped[str] = mapped_column(String(24), nullable=False)
    severity: Mapped[str] = mapped_column(String(20), nullable=False, server_default=text("'INFO'"))
    title_template: Mapped[str] = mapped_column(String(180), nullable=False)
    body_template: Mapped[str] = mapped_column(Text, nullable=False)
    is_enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default=text("true"))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now())


class WorkflowReminderDispatch(Base):
    """Durable idempotency record for one policy firing against one deadline target."""

    __tablename__ = "workflow_reminder_dispatches"
    __table_args__ = (
        CheckConstraint("target_type IN ('WORKFLOW_CASE', 'OBLIGATION')", name="chk_reminder_dispatch_target"),
        CheckConstraint(
            "(target_type = 'WORKFLOW_CASE' AND workflow_case_id IS NOT NULL AND obligation_id IS NULL) OR "
            "(target_type = 'OBLIGATION' AND obligation_id IS NOT NULL AND workflow_case_id IS NULL)",
            name="chk_reminder_dispatch_target_link",
        ),
        CheckConstraint("recipient_count >= 0", name="chk_reminder_dispatch_recipient_count"),
        UniqueConstraint("dispatch_key", name="uq_reminder_dispatch_key"),
        UniqueConstraint("reminder_policy_id", "workflow_case_id", name="uq_reminder_dispatch_policy_case"),
        UniqueConstraint("reminder_policy_id", "obligation_id", name="uq_reminder_dispatch_policy_obligation"),
        Index("idx_reminder_dispatch_dispatched", "dispatched_at"),
    )

    reminder_dispatch_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()")
    )
    reminder_policy_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("workflow_reminder_policies.reminder_policy_id", ondelete="RESTRICT"),
        nullable=False,
    )
    target_type: Mapped[str] = mapped_column(String(24), nullable=False)
    workflow_case_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("workflow_cases.workflow_case_id", ondelete="CASCADE"), nullable=True
    )
    obligation_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("compliance_obligations.obligation_id", ondelete="CASCADE"), nullable=True
    )
    dispatch_key: Mapped[str] = mapped_column(String(180), nullable=False)
    scheduled_for: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    dispatched_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())
    recipient_count: Mapped[int] = mapped_column(Integer, nullable=False, server_default=text("0"))

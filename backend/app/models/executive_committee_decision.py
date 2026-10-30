import uuid
from datetime import datetime

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, String, Text, UniqueConstraint, func, text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.session import Base


class ExecutiveCommitteeDecision(Base):
    """Human-recorded Executive Committee outcome and uploaded Speaking Order reference."""

    __tablename__ = "executive_committee_decisions"
    __table_args__ = (
        UniqueConstraint("workflow_case_id", name="uq_ec_decisions_workflow_case"),
        CheckConstraint(
            "outcome_code IN ('APPROVED', 'APPROVED_WITH_CONDITIONS', 'REJECTED')",
            name="chk_ec_decision_outcome",
        ),
        CheckConstraint(
            "length(trim(decision_reference)) >= 2 AND length(trim(decision_reasons)) >= 15 AND length(trim(speaking_order_reference)) >= 2",
            name="chk_ec_decision_required_text",
        ),
        CheckConstraint(
            "appeal_deadline_at = speaking_order_uploaded_at + INTERVAL '7 days'",
            name="chk_ec_decision_appeal_deadline",
        ),
    )

    executive_committee_decision_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()")
    )
    workflow_case_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("workflow_cases.workflow_case_id", ondelete="CASCADE"),
        nullable=False,
    )
    application_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("applications.application_id", ondelete="CASCADE"), nullable=False
    )
    outcome_code: Mapped[str] = mapped_column(String(32), nullable=False)
    decision_reference: Mapped[str] = mapped_column(String(180), nullable=False)
    decision_reasons: Mapped[str] = mapped_column(Text, nullable=False)
    speaking_order_reference: Mapped[str] = mapped_column(String(180), nullable=False)
    speaking_order_uploaded_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    appeal_deadline_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    recorded_by: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.user_id"), nullable=False)
    recorded_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())

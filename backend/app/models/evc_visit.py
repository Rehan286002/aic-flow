import uuid
from datetime import datetime

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, Index, Integer, String, Text, UniqueConstraint, func, text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.session import Base


class EVCVisit(Base):
    """Structured operational record for coordinating an EVC visit and recording its report.

    Formal EVC constitution/member selection remains outside this platform.
    """

    __tablename__ = "evc_visits"
    __table_args__ = (
        UniqueConstraint("workflow_case_id", name="uq_evc_visits_workflow_case"),
        CheckConstraint(
            "status IN ('DETAILS_REQUIRED', 'SCHEDULED', 'COMPLETED', 'CANCELLED')",
            name="chk_evc_visits_status",
        ),
        CheckConstraint(
            "visit_mode IS NULL OR visit_mode IN ('ONLINE', 'OFFLINE')",
            name="chk_evc_visits_mode",
        ),
        CheckConstraint(
            "scheduled_end_at IS NULL OR scheduled_start_at IS NULL OR scheduled_end_at > scheduled_start_at",
            name="chk_evc_visits_time_order",
        ),
        CheckConstraint(
            "status <> 'SCHEDULED' OR (visit_mode IS NOT NULL AND scheduled_start_at IS NOT NULL AND venue_or_meeting_details IS NOT NULL AND schedule_revision > 0)",
            name="chk_evc_visits_scheduled_details",
        ),
        CheckConstraint(
            "status <> 'COMPLETED' OR (report_reference IS NOT NULL AND report_summary IS NOT NULL AND report_outcome IS NOT NULL AND report_recorded_at IS NOT NULL AND report_recorded_by IS NOT NULL)",
            name="chk_evc_visits_completed_report",
        ),
        CheckConstraint(
            "status <> 'CANCELLED' OR cancellation_reason IS NOT NULL",
            name="chk_evc_visits_cancellation_reason",
        ),
        Index("idx_evc_visits_status_start", "status", "scheduled_start_at"),
    )

    evc_visit_id: Mapped[uuid.UUID] = mapped_column(
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
    status: Mapped[str] = mapped_column(String(30), nullable=False, server_default=text("'DETAILS_REQUIRED'"))
    visit_mode: Mapped[str | None] = mapped_column(String(20), nullable=True)
    scheduled_start_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    scheduled_end_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    venue_or_meeting_details: Mapped[str | None] = mapped_column(Text, nullable=True)
    official_schedule_reference: Mapped[str | None] = mapped_column(String(180), nullable=True)
    institution_contact_name: Mapped[str | None] = mapped_column(String(160), nullable=True)
    institution_contact_email: Mapped[str | None] = mapped_column(String(254), nullable=True)
    coordination_note: Mapped[str | None] = mapped_column(Text, nullable=True)
    schedule_revision: Mapped[int] = mapped_column(Integer, nullable=False, server_default=text("0"))
    report_reference: Mapped[str | None] = mapped_column(String(180), nullable=True)
    report_summary: Mapped[str | None] = mapped_column(Text, nullable=True)
    report_outcome: Mapped[str | None] = mapped_column(String(40), nullable=True)
    report_recorded_by: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("users.user_id"), nullable=True)
    report_recorded_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    cancellation_reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_by: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.user_id"), nullable=False)
    updated_by: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("users.user_id"), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now())

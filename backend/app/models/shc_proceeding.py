import uuid
from datetime import datetime

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, Index, String, Text, UniqueConstraint, func, text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.session import Base


class SHCProceeding(Base):
    """Structured Standing Hearing Committee hearing and recommendation record.

    SHC recommendations are routed to the Executive Committee; this record
    does not itself constitute a statutory approval, rejection or appeal.
    """

    __tablename__ = "shc_proceedings"
    __table_args__ = (
        UniqueConstraint("workflow_case_id", name="uq_shc_proceedings_workflow_case"),
        CheckConstraint(
            "status IN ('PREPARATION', 'SCHEDULED', 'HEARING_RECORDED', 'RECOMMENDATION_RECORDED')",
            name="chk_shc_proceedings_status",
        ),
        CheckConstraint(
            "hearing_mode IS NULL OR hearing_mode IN ('ONLINE', 'IN_PERSON')",
            name="chk_shc_proceedings_hearing_mode",
        ),
        CheckConstraint(
            "status <> 'SCHEDULED' OR (hearing_scheduled_at IS NOT NULL AND hearing_mode IS NOT NULL AND hearing_details IS NOT NULL AND schedule_revision > 0)",
            name="chk_shc_proceedings_schedule",
        ),
        CheckConstraint(
            "status NOT IN ('HEARING_RECORDED', 'RECOMMENDATION_RECORDED') OR (hearing_recorded_at IS NOT NULL AND representative_one_name IS NOT NULL AND representative_two_name IS NOT NULL AND hearing_summary IS NOT NULL)",
            name="chk_shc_proceedings_hearing_record",
        ),
        CheckConstraint(
            "status <> 'RECOMMENDATION_RECORDED' OR (recommendation_code IS NOT NULL AND recommendation_text IS NOT NULL AND recommendation_recorded_at IS NOT NULL AND recommendation_recorded_by IS NOT NULL)",
            name="chk_shc_proceedings_recommendation",
        ),
        CheckConstraint(
            "recommendation_code IS NULL OR recommendation_code IN ('COMPLIANCE_REVIEWED', 'FURTHER_COMPLIANCE_REQUIRED', 'DEFICIENCIES_REMAIN', 'INCONCLUSIVE')",
            name="chk_shc_proceedings_recommendation_code",
        ),
        Index("idx_shc_proceedings_status_hearing", "status", "hearing_scheduled_at"),
    )

    shc_proceeding_id: Mapped[uuid.UUID] = mapped_column(
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
    status: Mapped[str] = mapped_column(String(32), nullable=False, server_default=text("'PREPARATION'"))
    notice_reference: Mapped[str | None] = mapped_column(String(180), nullable=True)
    hearing_mode: Mapped[str | None] = mapped_column(String(20), nullable=True)
    hearing_scheduled_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    hearing_details: Mapped[str | None] = mapped_column(Text, nullable=True)
    official_schedule_reference: Mapped[str | None] = mapped_column(String(180), nullable=True)
    schedule_revision: Mapped[int] = mapped_column(nullable=False, server_default=text("0"))
    institution_submission_reference: Mapped[str | None] = mapped_column(String(500), nullable=True)
    representative_one_name: Mapped[str | None] = mapped_column(String(160), nullable=True)
    representative_one_designation: Mapped[str | None] = mapped_column(String(160), nullable=True)
    representative_two_name: Mapped[str | None] = mapped_column(String(160), nullable=True)
    representative_two_designation: Mapped[str | None] = mapped_column(String(160), nullable=True)
    hearing_summary: Mapped[str | None] = mapped_column(Text, nullable=True)
    hearing_recorded_by: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("users.user_id"), nullable=True)
    hearing_recorded_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    recommendation_code: Mapped[str | None] = mapped_column(String(40), nullable=True)
    recommendation_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    recommendation_reference: Mapped[str | None] = mapped_column(String(180), nullable=True)
    recommendation_recorded_by: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("users.user_id"), nullable=True)
    recommendation_recorded_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_by: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.user_id"), nullable=False)
    updated_by: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("users.user_id"), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now())

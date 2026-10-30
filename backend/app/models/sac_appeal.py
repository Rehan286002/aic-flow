import uuid
from datetime import datetime

from sqlalchemy import Boolean, CheckConstraint, DateTime, ForeignKey, Index, Integer, String, Text, UniqueConstraint, func, text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.session import Base


class SACAppeal(Base):
    """Institution appeal against one Executive Committee decision, heard by SAC and decided by Council."""

    __tablename__ = "sac_appeals"
    __table_args__ = (
        UniqueConstraint("executive_committee_decision_id", name="uq_sac_appeals_ec_decision"),
        CheckConstraint(
            "status IN ('FILED', 'SCHEDULED', 'HEARING_RECORDED', 'RECOMMENDATION_RECORDED', 'COUNCIL_DECISION_RECORDED')",
            name="chk_sac_appeals_status",
        ),
        CheckConstraint(
            "hearing_mode IS NULL OR hearing_mode IN ('ONLINE', 'IN_PERSON')",
            name="chk_sac_appeals_hearing_mode",
        ),
        CheckConstraint(
            "schedule_revision >= 0",
            name="chk_sac_appeals_schedule_revision",
        ),
        CheckConstraint(
            "status <> 'SCHEDULED' OR (hearing_scheduled_at IS NOT NULL AND hearing_mode IS NOT NULL AND hearing_details IS NOT NULL AND schedule_revision > 0)",
            name="chk_sac_appeals_schedule",
        ),
        CheckConstraint(
            "status NOT IN ('HEARING_RECORDED', 'RECOMMENDATION_RECORDED', 'COUNCIL_DECISION_RECORDED') OR (representative_one_name IS NOT NULL AND representative_one_designation IS NOT NULL AND representative_one_id_reference IS NOT NULL AND representative_one_id_self_attested IS TRUE AND representative_two_name IS NOT NULL AND representative_two_designation IS NOT NULL AND representative_two_id_reference IS NOT NULL AND representative_two_id_self_attested IS TRUE AND hearing_summary IS NOT NULL AND hearing_recorded_at IS NOT NULL AND hearing_recorded_by IS NOT NULL)",
            name="chk_sac_appeals_hearing_record",
        ),
        CheckConstraint(
            "status NOT IN ('RECOMMENDATION_RECORDED', 'COUNCIL_DECISION_RECORDED') OR (recommendation_code IS NOT NULL AND recommendation_text IS NOT NULL AND recommendation_recorded_at IS NOT NULL AND recommendation_recorded_by IS NOT NULL)",
            name="chk_sac_appeals_recommendation",
        ),
        CheckConstraint(
            "status <> 'COUNCIL_DECISION_RECORDED' OR (council_outcome_code IS NOT NULL AND council_decision_reference IS NOT NULL AND council_decision_text IS NOT NULL AND council_decision_uploaded_at IS NOT NULL AND council_decision_recorded_at IS NOT NULL AND council_decision_recorded_by IS NOT NULL)",
            name="chk_sac_appeals_council_decision",
        ),
        CheckConstraint(
            "recommendation_code IS NULL OR recommendation_code IN ('RECOMMEND_TO_COUNCIL', 'NOT_RECOMMEND_TO_COUNCIL', 'FURTHER_REVIEW_REQUIRED')",
            name="chk_sac_appeals_recommendation_code",
        ),
        CheckConstraint(
            "council_outcome_code IS NULL OR council_outcome_code IN ('UPHOLD_EXECUTIVE_COMMITTEE', 'SET_ASIDE_EXECUTIVE_COMMITTEE', 'MODIFY_EXECUTIVE_COMMITTEE', 'REMAND_FOR_RECONSIDERATION')",
            name="chk_sac_appeals_council_outcome",
        ),
        CheckConstraint(
            "filed_at <= appeal_deadline_at",
            name="chk_sac_appeals_filed_within_deadline",
        ),
        Index("idx_sac_appeals_status_hearing", "status", "hearing_scheduled_at"),
        Index("idx_sac_appeals_institution_filed", "application_id", "filed_at"),
    )

    sac_appeal_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()")
    )
    executive_committee_decision_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("executive_committee_decisions.executive_committee_decision_id", ondelete="RESTRICT"),
        nullable=False,
    )
    workflow_case_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("workflow_cases.workflow_case_id", ondelete="CASCADE"), nullable=False
    )
    application_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("applications.application_id", ondelete="CASCADE"), nullable=False
    )
    shc_proceeding_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("shc_proceedings.shc_proceeding_id", ondelete="SET NULL"), nullable=True
    )

    status: Mapped[str] = mapped_column(String(36), nullable=False, server_default=text("'FILED'"))
    appeal_reference: Mapped[str | None] = mapped_column(String(180), nullable=True)
    appeal_grounds: Mapped[str] = mapped_column(Text, nullable=False)
    supporting_material_reference: Mapped[str] = mapped_column(Text, nullable=False)
    filed_by: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.user_id"), nullable=False)
    filed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())
    appeal_deadline_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

    hearing_mode: Mapped[str | None] = mapped_column(String(20), nullable=True)
    hearing_scheduled_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    hearing_details: Mapped[str | None] = mapped_column(Text, nullable=True)
    official_schedule_reference: Mapped[str | None] = mapped_column(String(180), nullable=True)
    schedule_revision: Mapped[int] = mapped_column(Integer, nullable=False, server_default=text("0"))

    regulation_bureau_observation_reference: Mapped[str | None] = mapped_column(String(180), nullable=True)
    regulation_bureau_observations: Mapped[str | None] = mapped_column(Text, nullable=True)
    bureau_observations_recorded_by: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("users.user_id"), nullable=True)
    bureau_observations_recorded_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    representative_one_name: Mapped[str | None] = mapped_column(String(160), nullable=True)
    representative_one_designation: Mapped[str | None] = mapped_column(String(160), nullable=True)
    representative_one_id_reference: Mapped[str | None] = mapped_column(String(500), nullable=True)
    representative_one_id_self_attested: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    representative_two_name: Mapped[str | None] = mapped_column(String(160), nullable=True)
    representative_two_designation: Mapped[str | None] = mapped_column(String(160), nullable=True)
    representative_two_id_reference: Mapped[str | None] = mapped_column(String(500), nullable=True)
    representative_two_id_self_attested: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    hearing_summary: Mapped[str | None] = mapped_column(Text, nullable=True)
    hearing_recorded_by: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("users.user_id"), nullable=True)
    hearing_recorded_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    recommendation_code: Mapped[str | None] = mapped_column(String(40), nullable=True)
    recommendation_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    recommendation_reference: Mapped[str | None] = mapped_column(String(180), nullable=True)
    recommendation_recorded_by: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("users.user_id"), nullable=True)
    recommendation_recorded_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    council_outcome_code: Mapped[str | None] = mapped_column(String(48), nullable=True)
    council_decision_reference: Mapped[str | None] = mapped_column(String(180), nullable=True)
    council_decision_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    council_decision_uploaded_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    council_decision_recorded_by: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("users.user_id"), nullable=True)
    council_decision_recorded_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now())

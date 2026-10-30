import uuid
from datetime import date, datetime

from sqlalchemy import Boolean, CheckConstraint, Date, DateTime, ForeignKey, Index, Integer, String, Text, UniqueConstraint, func, text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.session import Base


class DocumentValidityRecord(Base):
    """Officer-reviewed validity dates and rule basis for an exact document version."""

    __tablename__ = "document_validity_records"
    __table_args__ = (
        CheckConstraint(
            "validity_type IN ('LEASE_DEED', 'STRUCTURAL_STABILITY_CERTIFICATE', 'FIRE_SAFETY_CERTIFICATE', 'BUILDING_COMPLETION_CERTIFICATE', 'ISSUER_DATED_DOCUMENT')",
            name="chk_document_validity_type",
        ),
        CheckConstraint(
            "status IN ('PENDING_REVIEW', 'VERIFIED', 'RETURNED', 'SUPERSEDED')",
            name="chk_document_validity_status",
        ),
        CheckConstraint(
            "valid_until IS NULL OR valid_from IS NULL OR valid_until >= valid_from",
            name="chk_document_validity_date_order",
        ),
        CheckConstraint(
            "validity_type <> 'LEASE_DEED' OR (lease_start_date IS NOT NULL AND lease_end_date IS NOT NULL AND maximum_course_duration_years IS NOT NULL AND maximum_course_duration_years > 0)",
            name="chk_document_validity_lease_details",
        ),
        CheckConstraint(
            "validity_type <> 'STRUCTURAL_STABILITY_CERTIFICATE' OR (issue_date IS NOT NULL AND valid_until IS NOT NULL)",
            name="chk_document_validity_structural_dates",
        ),
        CheckConstraint(
            "validity_type <> 'FIRE_SAFETY_CERTIFICATE' OR (issue_date IS NOT NULL AND valid_until IS NOT NULL AND length(trim(validity_basis_reference)) > 0)",
            name="chk_document_validity_fire_dates",
        ),
        CheckConstraint(
            "status <> 'VERIFIED' OR (reviewed_by IS NOT NULL AND reviewed_at IS NOT NULL)",
            name="chk_document_validity_reviewed",
        ),
        UniqueConstraint("document_version_id", name="uq_document_validity_document_version"),
        Index("idx_document_validity_due", "status", "valid_until"),
        Index("idx_document_validity_case_type", "workflow_case_id", "validity_type", "status"),
    )

    document_validity_record_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()")
    )
    workflow_case_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("workflow_cases.workflow_case_id", ondelete="CASCADE"), nullable=False
    )
    application_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("applications.application_id", ondelete="CASCADE"), nullable=False
    )
    application_requirement_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("application_requirements.application_requirement_id", ondelete="RESTRICT"), nullable=False
    )
    document_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("documents.document_id", ondelete="RESTRICT"), nullable=False
    )
    document_version_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("document_versions.document_version_id", ondelete="RESTRICT"), nullable=False
    )
    supersedes_validity_record_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("document_validity_records.document_validity_record_id"), nullable=True
    )

    validity_type: Mapped[str] = mapped_column(String(48), nullable=False)
    status: Mapped[str] = mapped_column(String(24), nullable=False, server_default=text("'PENDING_REVIEW'"))
    issue_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    valid_from: Mapped[date | None] = mapped_column(Date, nullable=True)
    valid_until: Mapped[date | None] = mapped_column(Date, nullable=True)
    review_due_at: Mapped[date | None] = mapped_column(Date, nullable=True)

    lease_start_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    lease_end_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    maximum_course_duration_years: Mapped[int | None] = mapped_column(Integer, nullable=True)
    lease_minimum_term_met: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    lease_live_term_met_at_submission: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    lease_eoa_cutoff_year_triggered: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    lease_assessed_on: Mapped[date | None] = mapped_column(Date, nullable=True)

    validity_basis_reference: Mapped[str] = mapped_column(Text, nullable=False)
    submitted_by: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.user_id"), nullable=False)
    submitted_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())
    reviewed_by: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("users.user_id"), nullable=True)
    reviewed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    review_note: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now())

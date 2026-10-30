import uuid
from datetime import date, datetime

from sqlalchemy import (
    CheckConstraint,
    Date,
    DateTime,
    ForeignKey,
    Index,
    String,
    Text,
    UniqueConstraint,
    func,
    text,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.session import Base


class DocumentValidityRecord(Base):
    """Version-specific validity statement with explicit human verification."""

    __tablename__ = "document_validity_records"
    __table_args__ = (
        CheckConstraint(
            "verification_status IN ('PENDING_VERIFICATION', 'VERIFIED', 'RETURNED', 'DISPUTED', 'SUPERSEDED')",
            name="chk_document_validity_status",
        ),
        CheckConstraint(
            "valid_from IS NULL OR valid_until >= valid_from",
            name="chk_document_validity_date_order",
        ),
        UniqueConstraint("document_version_id", name="uq_document_validity_version"),
        Index("idx_document_validity_due_status", "valid_until", "verification_status"),
        Index("idx_document_validity_institution", "institution_id", "valid_until"),
        Index("idx_document_validity_case", "workflow_case_id", "verification_status"),
    )

    document_validity_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()")
    )
    workflow_case_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("workflow_cases.workflow_case_id", ondelete="CASCADE"), nullable=False
    )
    application_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("applications.application_id", ondelete="CASCADE"), nullable=False
    )
    institution_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("institutions.institution_id", ondelete="CASCADE"), nullable=False
    )
    document_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("documents.document_id", ondelete="RESTRICT"), nullable=False
    )
    document_version_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("document_versions.document_version_id", ondelete="RESTRICT"), nullable=False
    )
    document_type: Mapped[str] = mapped_column(String(60), nullable=False)
    issuer: Mapped[str] = mapped_column(String(300), nullable=False)
    valid_from: Mapped[date | None] = mapped_column(Date, nullable=True)
    valid_until: Mapped[date] = mapped_column(Date, nullable=False)
    document_reference: Mapped[str] = mapped_column(String(500), nullable=False)
    verification_status: Mapped[str] = mapped_column(
        String(32), nullable=False, server_default=text("'PENDING_VERIFICATION'")
    )
    verification_note: Mapped[str | None] = mapped_column(Text, nullable=True)
    replacement_of_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("document_validity_records.document_validity_id"), nullable=True
    )
    created_by: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.user_id"), nullable=False)
    verified_by: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("users.user_id"), nullable=True)
    verified_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now())

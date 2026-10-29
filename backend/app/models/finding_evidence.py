from datetime import datetime
from uuid import UUID as PythonUUID

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    ForeignKey,
    Integer,
    String,
    Text,
    func,
    text,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.session import Base


class FindingEvidence(Base):
    __tablename__ = "finding_evidence"

    __table_args__ = (
        CheckConstraint(
            "page_number IS NULL OR page_number > 0",
            name="chk_finding_evidence_page",
        ),
        CheckConstraint(
            "num_nonnulls("
            "document_version_id, "
            "extracted_field_id, "
            "verification_attempt_id, "
            "validation_result_id"
            ") >= 1",
            name="chk_finding_evidence_target",
        ),
    )

    finding_evidence_id: Mapped[PythonUUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        server_default=text("gen_random_uuid()"),
    )

    finding_id: Mapped[PythonUUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("findings.finding_id", ondelete="CASCADE"),
        nullable=False,
    )

    document_version_id: Mapped[PythonUUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("document_versions.document_version_id"),
        nullable=True,
    )

    extracted_field_id: Mapped[PythonUUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("extracted_fields.extracted_field_id"),
        nullable=True,
    )

    verification_attempt_id: Mapped[PythonUUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("verification_attempts.verification_attempt_id"),
        nullable=True,
    )

    validation_result_id: Mapped[PythonUUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("validation_results.validation_result_id"),
        nullable=True,
    )

    page_number: Mapped[int | None] = mapped_column(
        Integer,
        nullable=True,
    )

    evidence_type: Mapped[str] = mapped_column(
        String(80),
        nullable=False,
    )

    evidence_reference: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    evidence_summary: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )

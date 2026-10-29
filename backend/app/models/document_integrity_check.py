from datetime import datetime
from uuid import UUID as PythonUUID

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    ForeignKey,
    String,
    func,
    text,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.session import Base


class DocumentIntegrityCheck(Base):
    __tablename__ = "document_integrity_checks"

    __table_args__ = (
        CheckConstraint(
            "check_type IN ("
            "'HASH_DUPLICATE', "
            "'PDF_METADATA', "
            "'VISUAL_TAMPERING_INDICATOR', "
            "'SIGNATURE_STRUCTURE', "
            "'FILE_STRUCTURE'"
            ")",
            name="chk_document_integrity_check_type",
        ),
        CheckConstraint(
            "outcome IN ('PASS', 'WARNING', 'ANOMALY', 'ERROR', 'INCONCLUSIVE')",
            name="chk_document_integrity_outcome",
        ),
    )

    document_integrity_check_id: Mapped[PythonUUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        server_default=text("gen_random_uuid()"),
    )

    document_version_id: Mapped[PythonUUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("document_versions.document_version_id"),
        nullable=False,
    )

    check_type: Mapped[str] = mapped_column(
        String(80),
        nullable=False,
    )

    outcome: Mapped[str] = mapped_column(
        String(40),
        nullable=False,
    )

    details: Mapped[dict] = mapped_column(
        JSONB,
        nullable=False,
        server_default=text("'{}'::jsonb"),
    )

    tool_name: Mapped[str | None] = mapped_column(
        String(120),
        nullable=True,
    )

    tool_version: Mapped[str | None] = mapped_column(
        String(80),
        nullable=True,
    )

    checked_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )

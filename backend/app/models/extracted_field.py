from datetime import datetime
from uuid import UUID as PythonUUID

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    Numeric,
    String,
    Text,
    func,
    text,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.session import Base


class ExtractedField(Base):
    __tablename__ = "extracted_fields"

    __table_args__ = (
        CheckConstraint(
            "confidence IS NULL OR confidence BETWEEN 0 AND 1",
            name="chk_extracted_field_confidence",
        ),
        CheckConstraint(
            "page_number IS NULL OR page_number > 0",
            name="chk_extracted_field_page",
        ),
        Index("idx_extracted_fields_code", "field_code"),
    )

    extracted_field_id: Mapped[PythonUUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        server_default=text("gen_random_uuid()"),
    )

    document_extraction_id: Mapped[PythonUUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey(
            "document_extractions.document_extraction_id",
            ondelete="CASCADE",
        ),
        nullable=False,
    )

    field_code: Mapped[str] = mapped_column(
        String(120),
        nullable=False,
    )

    field_label: Mapped[str | None] = mapped_column(
        String(200),
        nullable=True,
    )

    raw_value: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    normalized_value: Mapped[dict | list | None] = mapped_column(
        JSONB,
        nullable=True,
    )

    confidence: Mapped[float | None] = mapped_column(
        Numeric(5, 4),
        nullable=True,
    )

    page_number: Mapped[int | None] = mapped_column(
        nullable=True,
    )

    bounding_box: Mapped[dict | None] = mapped_column(
        JSONB,
        nullable=True,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )

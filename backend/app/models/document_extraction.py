from datetime import datetime
from uuid import UUID as PythonUUID

from sqlalchemy import (
    DateTime,
    Enum,
    ForeignKey,
    String,
    Text,
    func,
    text,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.session import Base
from app.models.enums import DocumentProcessingStatus


class DocumentExtraction(Base):
    __tablename__ = "document_extractions"

    document_extraction_id: Mapped[PythonUUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        server_default=text("gen_random_uuid()"),
    )

    document_version_id: Mapped[PythonUUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("document_versions.document_version_id"),
        nullable=False,
    )

    processing_job_id: Mapped[PythonUUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("document_processing_jobs.document_processing_job_id"),
        nullable=True,
    )

    extraction_status: Mapped[DocumentProcessingStatus] = mapped_column(
        Enum(
            DocumentProcessingStatus,
            name="document_processing_status",
            values_callable=lambda enum_cls: [member.value for member in enum_cls],
        ),
        nullable=False,
    )

    extraction_engine: Mapped[str] = mapped_column(
        String(120),
        nullable=False,
    )

    engine_version: Mapped[str | None] = mapped_column(
        String(80),
        nullable=True,
    )

    language_code: Mapped[str | None] = mapped_column(
        String(20),
        nullable=True,
    )

    full_text_storage_key: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )

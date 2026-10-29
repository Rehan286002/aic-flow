from datetime import datetime
from uuid import UUID as PythonUUID

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    ForeignKey,
    String,
    Text,
    func,
    text,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.session import Base


class DocumentMetadataObservation(Base):
    __tablename__ = "document_metadata_observations"

    __table_args__ = (
        CheckConstraint(
            "metadata_source IN "
            "('PDF_INFO', 'XMP', 'EXIF', 'FILE_SYSTEM', 'SERVER_INGEST')",
            name="chk_document_metadata_source",
        ),
        CheckConstraint(
            "trust_level IN "
            "('UNTRUSTED', 'SERVER_OBSERVED', 'CRYPTOGRAPHICALLY_BOUND')",
            name="chk_document_metadata_trust_level",
        ),
    )

    document_metadata_observation_id: Mapped[PythonUUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        server_default=text("gen_random_uuid()"),
    )

    document_version_id: Mapped[PythonUUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("document_versions.document_version_id"),
        nullable=False,
    )

    metadata_source: Mapped[str] = mapped_column(
        String(40),
        nullable=False,
    )

    metadata_key: Mapped[str] = mapped_column(
        String(160),
        nullable=False,
    )

    metadata_value: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    trust_level: Mapped[str] = mapped_column(
        String(24),
        nullable=False,
        server_default=text("'UNTRUSTED'"),
    )

    observed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )

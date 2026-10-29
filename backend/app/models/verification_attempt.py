from datetime import datetime
from uuid import UUID as PythonUUID

from sqlalchemy import (
    DateTime,
    Enum,
    ForeignKey,
    Index,
    String,
    Text,
    func,
    text,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.session import Base
from app.models.enums import VerificationMethod, VerificationStatus


class VerificationAttempt(Base):
    __tablename__ = "verification_attempts"

    __table_args__ = (
        Index(
            "idx_verification_doc_status",
            "document_version_id",
            "status",
        ),
    )

    verification_attempt_id: Mapped[PythonUUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        server_default=text("gen_random_uuid()"),
    )

    document_version_id: Mapped[PythonUUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("document_versions.document_version_id"),
        nullable=False,
    )

    verification_source_id: Mapped[PythonUUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("verification_sources.verification_source_id"),
        nullable=True,
    )

    method: Mapped[VerificationMethod] = mapped_column(
        Enum(
            VerificationMethod,
            name="verification_method",
            values_callable=lambda enum_cls: [member.value for member in enum_cls],
        ),
        nullable=False,
    )

    status: Mapped[VerificationStatus] = mapped_column(
        Enum(
            VerificationStatus,
            name="verification_status",
            values_callable=lambda enum_cls: [member.value for member in enum_cls],
        ),
        nullable=False,
        server_default=text("'PENDING'"),
    )

    requested_by: Mapped[PythonUUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.user_id"),
        nullable=True,
    )

    source_reference_number: Mapped[str | None] = mapped_column(
        String(200),
        nullable=True,
    )

    request_correlation_id: Mapped[str | None] = mapped_column(
        String(160),
        nullable=True,
    )

    response_summary: Mapped[dict] = mapped_column(
        JSONB,
        nullable=False,
        server_default=text("'{}'::jsonb"),
    )

    compared_fields: Mapped[dict] = mapped_column(
        JSONB,
        nullable=False,
        server_default=text("'{}'::jsonb"),
    )

    source_response_reference: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    requested_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )

    completed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

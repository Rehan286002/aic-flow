from datetime import datetime
from uuid import UUID as PythonUUID

from sqlalchemy import (
    CHAR,
    Boolean,
    CheckConstraint,
    DateTime,
    ForeignKey,
    Integer,
    String,
    Text,
    func,
    text,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.session import Base


class DigitalSignatureCheck(Base):
    __tablename__ = "digital_signature_checks"

    __table_args__ = (
        CheckConstraint(
            "revocation_status IS NULL OR revocation_status IN "
            "('GOOD', 'REVOKED', 'UNKNOWN', 'UNAVAILABLE', 'NOT_CHECKED')",
            name="chk_signature_revocation_status",
        ),
        CheckConstraint(
            "timestamp_status IS NULL OR timestamp_status IN "
            "('VALID', 'INVALID', 'UNAVAILABLE', 'NOT_PRESENT', 'NOT_CHECKED')",
            name="chk_signature_timestamp_status",
        ),
    )

    digital_signature_check_id: Mapped[PythonUUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        server_default=text("gen_random_uuid()"),
    )

    document_version_id: Mapped[PythonUUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("document_versions.document_version_id"),
        nullable=False,
    )

    signature_index: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        server_default=text("0"),
    )

    signature_format: Mapped[str | None] = mapped_column(
        String(40),
        nullable=True,
    )

    digest_algorithm: Mapped[str | None] = mapped_column(
        String(40),
        nullable=True,
    )

    signer_subject: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    signer_certificate_fingerprint: Mapped[str | None] = mapped_column(
        CHAR(64),
        nullable=True,
    )

    signature_integrity_valid: Mapped[bool | None] = mapped_column(
        Boolean,
        nullable=True,
    )

    certificate_chain_valid: Mapped[bool | None] = mapped_column(
        Boolean,
        nullable=True,
    )

    revocation_status: Mapped[str | None] = mapped_column(
        String(32),
        nullable=True,
    )

    timestamp_status: Mapped[str | None] = mapped_column(
        String(32),
        nullable=True,
    )

    trust_policy_id: Mapped[str | None] = mapped_column(
        String(120),
        nullable=True,
    )

    validation_details: Mapped[dict] = mapped_column(
        JSONB,
        nullable=False,
        server_default=text("'{}'::jsonb"),
    )

    checked_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )

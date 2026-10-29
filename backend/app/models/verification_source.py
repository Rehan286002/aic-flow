from datetime import datetime
from uuid import UUID as PythonUUID

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    DateTime,
    Enum,
    SmallInteger,
    String,
    Text,
    func,
    text,
)
from sqlalchemy.dialects.postgresql import ARRAY, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.session import Base
from app.models.enums import SourceType


class VerificationSource(Base):
    __tablename__ = "verification_sources"

    __table_args__ = (
        CheckConstraint(
            "integration_mode IN "
            "('API', 'PORTAL', 'QR_RESOLUTION', "
            "'DIGITAL_SIGNATURE', 'MANUAL', 'MOCK')",
            name="chk_verification_source_integration_mode",
        ),
    )

    verification_source_id: Mapped[PythonUUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        server_default=text("gen_random_uuid()"),
    )

    source_code: Mapped[str] = mapped_column(
        String(100),
        unique=True,
        nullable=False,
    )

    source_name: Mapped[str] = mapped_column(
        String(250),
        nullable=False,
    )

    source_type: Mapped[SourceType] = mapped_column(
        Enum(
            SourceType,
            name="source_type",
            values_callable=lambda enum_cls: [member.value for member in enum_cls],
        ),
        nullable=False,
    )

    supported_document_types: Mapped[list[int] | None] = mapped_column(
        ARRAY(SmallInteger),
        nullable=True,
    )

    official_domain: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
    )

    integration_mode: Mapped[str] = mapped_column(
        String(40),
        nullable=False,
    )

    is_authorized: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        server_default=text("false"),
    )

    is_enabled: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        server_default=text("false"),
    )

    credential_secret_reference: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )

    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )

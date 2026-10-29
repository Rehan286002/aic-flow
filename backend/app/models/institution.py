import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, String, Text, func, text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.session import Base


class Institution(Base):
    __tablename__ = "institutions"

    institution_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        server_default=text("gen_random_uuid()"),
    )

    aicte_permanent_institution_id: Mapped[str] = mapped_column(
        String(80),
        unique=True,
        nullable=False,
    )

    institution_name: Mapped[str] = mapped_column(
        String(300),
        nullable=False,
    )

    institution_type: Mapped[str | None] = mapped_column(
        String(100),
        nullable=True,
    )

    address_line: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    district: Mapped[str | None] = mapped_column(
        String(120),
        nullable=True,
    )

    state: Mapped[str | None] = mapped_column(
        String(120),
        nullable=True,
    )

    postal_code: Mapped[str | None] = mapped_column(
        String(20),
        nullable=True,
    )

    is_active: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=True,
        server_default=text("true"),
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

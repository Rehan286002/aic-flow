from datetime import datetime
from uuid import UUID as PythonUUID

from sqlalchemy import (
    CHAR,
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
    func,
    text,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.session import Base


class InstitutionRecordVersion(Base):
    __tablename__ = "institution_record_versions"

    __table_args__ = (
        CheckConstraint(
            "record_version > 0",
            name="chk_institution_record_version",
        ),
        UniqueConstraint(
            "institution_id",
            "record_version",
            name="uq_institution_record_version",
        ),
        Index(
            "idx_institution_record_versions_source_sync",
            "source_sync_run_id",
        ),
    )

    institution_record_version_id: Mapped[PythonUUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        server_default=text("gen_random_uuid()"),
    )

    institution_id: Mapped[PythonUUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("institutions.institution_id"),
        nullable=False,
    )

    record_version: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
    )

    record_data: Mapped[dict] = mapped_column(
        JSONB,
        nullable=False,
    )

    source_system: Mapped[str] = mapped_column(
        String(120),
        nullable=False,
    )

    source_reference: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    effective_from: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
    )

    effective_to: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    recorded_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )

    recorded_by: Mapped[PythonUUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.user_id"),
        nullable=True,
    )

    source_sync_run_id: Mapped[PythonUUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("source_sync_runs.source_sync_run_id"),
        nullable=True,
    )

    source_updated_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    source_payload_sha256: Mapped[str | None] = mapped_column(
        CHAR(64),
        nullable=True,
    )

from datetime import datetime
from uuid import UUID as PythonUUID

from sqlalchemy import (
    DateTime,
    ForeignKey,
    Index,
    String,
    func,
    text,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.session import Base


class ValidationRunSourceVersion(Base):
    __tablename__ = "validation_run_source_versions"

    __table_args__ = (
        Index(
            "idx_validation_run_source_versions_source",
            "source_code",
            text("captured_at DESC"),
        ),
    )

    validation_run_id: Mapped[PythonUUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey(
            "validation_runs.validation_run_id",
            ondelete="CASCADE",
        ),
        primary_key=True,
    )

    institution_record_version_id: Mapped[PythonUUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("institution_record_versions.institution_record_version_id"),
        primary_key=True,
    )

    source_sync_run_id: Mapped[PythonUUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("source_sync_runs.source_sync_run_id"),
        nullable=True,
    )

    source_code: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
    )

    captured_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )

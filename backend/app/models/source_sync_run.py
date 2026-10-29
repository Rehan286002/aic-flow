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
    func,
    text,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.session import Base


class SourceSyncRun(Base):
    __tablename__ = "source_sync_runs"

    __table_args__ = (
        CheckConstraint(
            "environment IN ('SIMULATED', 'SANDBOX', 'PRODUCTION', 'PUBLIC_DATA')",
            name="chk_source_sync_environment",
        ),
        CheckConstraint(
            "sync_kind IN ('FULL', 'INCREMENTAL', 'ON_DEMAND', 'HEALTH_CHECK')",
            name="chk_source_sync_kind",
        ),
        CheckConstraint(
            "status IN "
            "('QUEUED', 'RUNNING', 'SUCCEEDED', 'PARTIAL', 'FAILED', 'CANCELLED')",
            name="chk_source_sync_status",
        ),
        CheckConstraint(
            "records_received >= 0",
            name="chk_source_sync_records_received",
        ),
        CheckConstraint(
            "completed_at IS NULL OR completed_at >= started_at",
            name="chk_source_sync_completed_at",
        ),
        Index(
            "idx_source_sync_runs_source_time",
            "verification_source_id",
            text("started_at DESC"),
        ),
        Index(
            "idx_source_sync_runs_status_time",
            "status",
            text("started_at DESC"),
        ),
    )

    source_sync_run_id: Mapped[PythonUUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        server_default=text("gen_random_uuid()"),
    )

    verification_source_id: Mapped[PythonUUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("verification_sources.verification_source_id"),
        nullable=False,
    )

    environment: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
    )

    sync_kind: Mapped[str] = mapped_column(
        String(40),
        nullable=False,
    )

    adapter_version: Mapped[str] = mapped_column(
        String(80),
        nullable=False,
    )

    status: Mapped[str] = mapped_column(
        String(24),
        nullable=False,
    )

    request_correlation_id: Mapped[str | None] = mapped_column(
        String(160),
        nullable=True,
    )

    source_published_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    source_updated_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    started_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )

    completed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    records_received: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        server_default=text("0"),
    )

    response_sha256: Mapped[str | None] = mapped_column(
        CHAR(64),
        nullable=True,
    )

    sanitized_summary: Mapped[dict] = mapped_column(
        JSONB,
        nullable=False,
        server_default=text("'{}'::jsonb"),
    )

    error_code: Mapped[str | None] = mapped_column(
        String(100),
        nullable=True,
    )

    error_summary: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )

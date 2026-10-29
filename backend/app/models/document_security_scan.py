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


class DocumentSecurityScan(Base):
    __tablename__ = "document_security_scans"

    __table_args__ = (
        CheckConstraint(
            "scan_status IN ('CLEAN', 'DETECTED', 'ERROR', 'NOT_SCANNED')",
            name="chk_document_security_scan_status",
        ),
    )

    document_security_scan_id: Mapped[PythonUUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        server_default=text("gen_random_uuid()"),
    )

    document_version_id: Mapped[PythonUUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("document_versions.document_version_id"),
        nullable=False,
    )

    scanner_name: Mapped[str] = mapped_column(
        String(120),
        nullable=False,
    )

    scanner_version: Mapped[str | None] = mapped_column(
        String(80),
        nullable=True,
    )

    signature_database_version: Mapped[str | None] = mapped_column(
        String(100),
        nullable=True,
    )

    scan_status: Mapped[str] = mapped_column(
        String(24),
        nullable=False,
    )

    threat_name: Mapped[str | None] = mapped_column(
        String(240),
        nullable=True,
    )

    scanned_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )

    scan_log_reference: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

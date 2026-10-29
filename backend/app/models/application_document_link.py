from datetime import datetime
from uuid import UUID as PythonUUID

from sqlalchemy import (
    DateTime,
    ForeignKey,
    Index,
    UniqueConstraint,
    func,
    text,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.session import Base


class ApplicationDocumentLink(Base):
    __tablename__ = "application_document_links"

    __table_args__ = (
        UniqueConstraint(
            "application_revision_id",
            "document_version_id",
            name="uq_application_document_revision",
        ),
        Index(
            "idx_application_document_revision",
            "application_revision_id",
        ),
    )

    application_document_link_id: Mapped[PythonUUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        server_default=text("gen_random_uuid()"),
    )

    application_revision_id: Mapped[PythonUUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey(
            "application_revisions.application_revision_id",
            ondelete="RESTRICT",
        ),
        nullable=False,
    )

    uploaded_for_requirement_id: Mapped[PythonUUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("application_requirements.application_requirement_id"),
        nullable=True,
    )

    document_version_id: Mapped[PythonUUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("document_versions.document_version_id"),
        nullable=False,
    )

    linked_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )

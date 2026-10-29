import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    ForeignKey,
    UniqueConstraint,
    func,
    text,
)
from sqlalchemy import (
    Enum as SQLAlchemyEnum,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.session import Base
from app.models.enums import RevisionStatus

if TYPE_CHECKING:
    from app.models.application_field_value import ApplicationFieldValue


class ApplicationRevision(Base):
    __tablename__ = "application_revisions"

    __table_args__ = (
        CheckConstraint(
            "revision_number > 0",
            name="chk_revision_number_positive",
        ),
        UniqueConstraint(
            "application_id",
            "revision_number",
            name="uq_application_revision_number",
        ),
        UniqueConstraint(
            "application_revision_id",
            "application_id",
            name="uq_application_revision_id_application_id",
        ),
    )

    application_revision_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        server_default=text("gen_random_uuid()"),
    )

    application_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey(
            "applications.application_id",
            ondelete="RESTRICT",
        ),
        nullable=False,
    )

    revision_number: Mapped[int] = mapped_column(
        nullable=False,
    )

    status: Mapped[RevisionStatus] = mapped_column(
        SQLAlchemyEnum(
            RevisionStatus,
            name="revision_status",
            values_callable=lambda enum_cls: [item.value for item in enum_cls],
        ),
        nullable=False,
        server_default=text("'DRAFT'"),
    )

    supersedes_revision_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("application_revisions.application_revision_id"),
        nullable=True,
    )

    created_by: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.user_id"),
        nullable=False,
    )

    submitted_by: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.user_id"),
        nullable=True,
    )

    submitted_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    # Linked to rectification_requests in a later implementation stage.
    rectification_request_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        nullable=True,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )

    # Relationships
    field_values: Mapped[list["ApplicationFieldValue"]] = relationship(
        "ApplicationFieldValue",
        back_populates="revision",
        cascade="save-update, merge",
        passive_deletes="all",
    )

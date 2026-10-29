from datetime import datetime
from uuid import UUID as PythonUUID

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    Enum,
    ForeignKey,
    String,
    Text,
    UniqueConstraint,
    text,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.session import Base
from app.models.enums import RequirementStatus


class ApplicationRequirement(Base):
    __tablename__ = "application_requirements"

    __table_args__ = (
        CheckConstraint(
            "applicability_status IN "
            "('APPLICABLE', 'NOT_APPLICABLE', 'PENDING_DETERMINATION')",
            name="chk_application_requirement_applicability",
        ),
        UniqueConstraint(
            "application_revision_id",
            "checklist_item_id",
            name="uq_application_revision_checklist_item",
        ),
    )

    application_requirement_id: Mapped[PythonUUID] = mapped_column(
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

    checklist_item_id: Mapped[PythonUUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("checklist_items.checklist_item_id"),
        nullable=False,
    )

    applicability_status: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
    )

    status: Mapped[RequirementStatus] = mapped_column(
        Enum(
            RequirementStatus,
            name="requirement_status",
            values_callable=lambda enum_cls: [member.value for member in enum_cls],
        ),
        nullable=False,
        server_default=text("'PENDING'"),
    )

    determination_reason: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    last_evaluated_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

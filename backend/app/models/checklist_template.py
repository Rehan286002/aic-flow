from datetime import datetime
from uuid import UUID as PythonUUID

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    DateTime,
    Enum,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
    func,
    text,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.session import Base
from app.models.enums import ApplicationFamily


class ChecklistTemplate(Base):
    __tablename__ = "checklist_templates"

    __table_args__ = (
        CheckConstraint(
            "version_number > 0",
            name="chk_checklist_template_version",
        ),
        UniqueConstraint(
            "template_code",
            "version_number",
            name="uq_checklist_template_version",
        ),
    )

    checklist_template_id: Mapped[PythonUUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        server_default=text("gen_random_uuid()"),
    )

    template_code: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
    )

    template_name: Mapped[str] = mapped_column(
        String(200),
        nullable=False,
    )

    application_family: Mapped[ApplicationFamily] = mapped_column(
        Enum(
            ApplicationFamily,
            name="application_family",
            values_callable=lambda enum_cls: [member.value for member in enum_cls],
        ),
        nullable=False,
    )

    academic_year_from: Mapped[str] = mapped_column(
        String(9),
        nullable=False,
    )

    academic_year_to: Mapped[str | None] = mapped_column(
        String(9),
        nullable=True,
    )

    version_number: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
    )

    regulatory_reference: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    is_published: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        server_default=text("false"),
    )

    created_by: Mapped[PythonUUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.user_id"),
        nullable=True,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )

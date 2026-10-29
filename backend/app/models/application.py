import uuid
from datetime import datetime

from sqlalchemy import (
    DateTime,
    ForeignKey,
    Index,
    String,
    UniqueConstraint,
    func,
    text,
)
from sqlalchemy import (
    Enum as SQLAlchemyEnum,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.session import Base
from app.models.enums import ApplicationFamily, ApplicationStatus


class Application(Base):
    __tablename__ = "applications"

    __table_args__ = (
        UniqueConstraint(
            "institution_id",
            "academic_year",
            "application_family",
            "process_type",
            name="uq_applications_institution_ay_family_process",
        ),
    )

    application_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        server_default=text("gen_random_uuid()"),
    )

    application_number: Mapped[str] = mapped_column(
        String(80),
        unique=True,
        nullable=False,
    )

    institution_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("institutions.institution_id"),
        nullable=False,
    )

    application_family: Mapped[ApplicationFamily] = mapped_column(
        SQLAlchemyEnum(
            ApplicationFamily,
            name="application_family",
            values_callable=lambda enum_cls: [item.value for item in enum_cls],
        ),
        nullable=False,
    )

    process_type: Mapped[str] = mapped_column(
        String(60), nullable=False, server_default=text("'EOA_SELF_DISCLOSURE'")
    )

    academic_year: Mapped[str] = mapped_column(
        String(9),
        nullable=False,
    )

    status: Mapped[ApplicationStatus] = mapped_column(
        SQLAlchemyEnum(
            ApplicationStatus,
            name="application_status",
            values_callable=lambda enum_cls: [item.value for item in enum_cls],
        ),
        nullable=False,
        server_default=text("'DRAFT'"),
    )

    review_team_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("review_teams.review_team_id"),
        nullable=True,
    )

    current_revision_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey(
            "application_revisions.application_revision_id",
            use_alter=True,
            name="fk_application_current_revision",
        ),
        nullable=True,
    )

    created_by: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.user_id"),
        nullable=False,
    )

    submitted_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
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


# Indexes from the AICTE reference schema
Index(
    "idx_applications_institution",
    Application.institution_id,
    Application.created_at.desc(),
)

Index(
    "idx_applications_team_status",
    Application.review_team_id,
    Application.status,
)

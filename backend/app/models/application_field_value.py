import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import (
    DateTime,
    ForeignKey,
    Index,
    UniqueConstraint,
    func,
    text,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.session import Base

if TYPE_CHECKING:
    from app.models.application_field_definition import ApplicationFieldDefinition
    from app.models.application_revision import ApplicationRevision


class ApplicationFieldValue(Base):
    """Dynamic application self-disclosure value based on Schema v4.

    Persists the revisioned self-disclosure values (e.g. completion certificate issue date,
    payment fee exemption, remarks) entered by the applicant for an application revision.
    """

    __tablename__ = "application_field_values"

    __table_args__ = (
        UniqueConstraint(
            "application_revision_id",
            "field_definition_id",
            name="uq_application_field_value_revision_field",
        ),
        Index(
            "idx_application_field_values_rev",
            "application_revision_id",
        ),
    )

    application_field_value_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        server_default=text("gen_random_uuid()"),
    )

    application_revision_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey(
            "application_revisions.application_revision_id",
            ondelete="RESTRICT",
        ),
        nullable=False,
    )

    field_definition_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("application_field_definitions.field_definition_id"),
        nullable=False,
    )

    value_json: Mapped[dict] = mapped_column(
        JSONB,
        nullable=False,
    )

    entered_by: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.user_id"),
        nullable=False,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )

    # Relationships
    field_definition: Mapped["ApplicationFieldDefinition"] = relationship(
        "ApplicationFieldDefinition",
        back_populates="field_values",
    )
    revision: Mapped["ApplicationRevision"] = relationship(
        "ApplicationRevision",
        back_populates="field_values",
    )

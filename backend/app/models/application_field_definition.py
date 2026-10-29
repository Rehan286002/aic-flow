import uuid
from typing import TYPE_CHECKING

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    String,
    text,
)
from sqlalchemy.dialects.postgresql import ARRAY, UUID
from sqlalchemy.dialects.postgresql import ENUM as PG_ENUM
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.session import Base
from app.models.enums import ApplicationFamily

if TYPE_CHECKING:
    from app.models.application_field_value import ApplicationFieldValue


class ApplicationFieldDefinition(Base):
    """Dynamic application self-disclosure field definition based on Schema v4.

    Defines metadata and regulatory constraints for dynamic declarations revisioned
    with each application submission.
    """

    __tablename__ = "application_field_definitions"

    __table_args__ = (
        CheckConstraint(
            "data_type IN ('TEXT', 'NUMBER', 'DATE', 'BOOLEAN', 'JSON', 'IDENTIFIER')",
            name="chk_field_data_type",
        ),
    )

    field_definition_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        server_default=text("gen_random_uuid()"),
    )

    field_code: Mapped[str] = mapped_column(
        String(100),
        unique=True,
        nullable=False,
    )

    field_label: Mapped[str] = mapped_column(
        String(200),
        nullable=False,
    )

    data_type: Mapped[str] = mapped_column(
        String(30),
        nullable=False,
    )

    applies_to: Mapped[list[ApplicationFamily] | None] = mapped_column(
        ARRAY(
            PG_ENUM(
                ApplicationFamily,
                name="application_family",
                create_type=False,
            )
        ),
        nullable=True,
    )

    applicant_editable: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        server_default=text("true"),
    )

    is_active: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        server_default=text("true"),
    )

    # Relationships
    field_values: Mapped[list["ApplicationFieldValue"]] = relationship(
        "ApplicationFieldValue",
        back_populates="field_definition",
        cascade="save-update, merge",
        passive_deletes="all",
    )

from datetime import datetime
from typing import Any
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
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.session import Base


class ValidationResult(Base):
    __tablename__ = "validation_results"

    __table_args__ = (
        CheckConstraint(
            "result_status IN "
            "('SATISFIED', 'DEFICIENT', 'NOT_APPLICABLE', "
            "'UNABLE_TO_DETERMINE', 'WARNING')",
            name="chk_validation_result_status",
        ),
    )

    validation_result_id: Mapped[PythonUUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        server_default=text("gen_random_uuid()"),
    )

    validation_run_id: Mapped[PythonUUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey(
            "validation_runs.validation_run_id",
            ondelete="CASCADE",
        ),
        nullable=False,
    )

    application_requirement_id: Mapped[PythonUUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("application_requirements.application_requirement_id"),
        nullable=True,
    )

    validation_rule_version_id: Mapped[PythonUUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("validation_rule_versions.validation_rule_version_id"),
        nullable=True,
    )

    result_status: Mapped[str] = mapped_column(
        String(30),
        nullable=False,
    )

    expected_value: Mapped[Any | None] = mapped_column(
        JSONB,
        nullable=True,
    )

    observed_value: Mapped[Any | None] = mapped_column(
        JSONB,
        nullable=True,
    )

    explanation: Mapped[str] = mapped_column(
        Text,
        nullable=False,
    )

    evaluated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )

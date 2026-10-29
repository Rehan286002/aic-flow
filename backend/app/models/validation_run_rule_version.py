from uuid import UUID as PythonUUID

from sqlalchemy import ForeignKey
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.session import Base


class ValidationRunRuleVersion(Base):
    __tablename__ = "validation_run_rule_versions"

    validation_run_id: Mapped[PythonUUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey(
            "validation_runs.validation_run_id",
            ondelete="CASCADE",
        ),
        primary_key=True,
    )

    validation_rule_version_id: Mapped[PythonUUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("validation_rule_versions.validation_rule_version_id"),
        primary_key=True,
    )

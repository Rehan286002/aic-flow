from uuid import UUID as PythonUUID

from sqlalchemy import ForeignKey
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.session import Base


class ChecklistItemRule(Base):
    __tablename__ = "checklist_item_rules"

    checklist_item_id: Mapped[PythonUUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey(
            "checklist_items.checklist_item_id",
            ondelete="CASCADE",
        ),
        primary_key=True,
    )

    validation_rule_id: Mapped[PythonUUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("validation_rules.validation_rule_id"),
        primary_key=True,
    )

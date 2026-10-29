from sqlalchemy import Boolean, SmallInteger, String, Text, text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.session import Base


class DocumentType(Base):
    __tablename__ = "document_types"

    document_type_id: Mapped[int] = mapped_column(
        SmallInteger,
        primary_key=True,
        autoincrement=True,
    )

    type_code: Mapped[str] = mapped_column(
        String(80),
        unique=True,
        nullable=False,
    )

    type_name: Mapped[str] = mapped_column(
        String(200),
        nullable=False,
    )

    description: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    is_active: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        server_default=text("true"),
    )

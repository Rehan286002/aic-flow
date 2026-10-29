import uuid
from datetime import datetime

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    SmallInteger,
    func,
    text,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.session import Base


class UserRoleAssignment(Base):
    __tablename__ = "user_role_assignments"

    __table_args__ = (
        CheckConstraint(
            """
            (institution_id IS NOT NULL AND review_team_id IS NULL)
            OR (institution_id IS NULL AND review_team_id IS NOT NULL)
            OR (institution_id IS NULL AND review_team_id IS NULL)
            """,
            name="chk_role_scope_shape",
        ),
        Index(
            "idx_user_role_assignments_user",
            "user_id",
            "revoked_at",
        ),
    )

    user_role_assignment_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        server_default=text("gen_random_uuid()"),
    )

    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.user_id"),
        nullable=False,
    )

    role_id: Mapped[int] = mapped_column(
        SmallInteger,
        ForeignKey("roles.role_id"),
        nullable=False,
    )

    institution_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("institutions.institution_id"),
        nullable=True,
    )

    review_team_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("review_teams.review_team_id"),
        nullable=True,
    )

    granted_by: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.user_id"),
        nullable=True,
    )

    granted_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )

    revoked_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import DateTime, ForeignKey, Index, String, UniqueConstraint, func, text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.session import Base


class WorkflowCase(Base):
    """Effective-dated workflow snapshot attached one-to-one to an application."""

    __tablename__ = "workflow_cases"
    __table_args__ = (
        UniqueConstraint("application_id", name="uq_workflow_cases_application"),
        Index("idx_workflow_cases_stage_due", "current_stage", "due_at"),
        Index("idx_workflow_cases_assigned", "assigned_role_code", "assigned_user_id"),
    )

    workflow_case_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()")
    )
    application_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("applications.application_id", ondelete="CASCADE"), nullable=False
    )
    process_type: Mapped[str] = mapped_column(String(60), nullable=False, server_default=text("'EOA_SELF_DISCLOSURE'"))
    route_code: Mapped[str] = mapped_column(String(100), nullable=False, server_default=text("'ROUTE_PENDING_CONFIRMATION'"))
    regulatory_version: Mapped[str] = mapped_column(String(80), nullable=False, server_default=text("'APH_2024_2027_BASELINE'"))
    route_snapshot: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False, server_default=text("'{}'::jsonb"))
    current_stage: Mapped[str] = mapped_column(String(50), nullable=False, server_default=text("'DRAFT'"))
    assigned_role_code: Mapped[str | None] = mapped_column(String(40), nullable=True)
    assigned_user_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("users.user_id"), nullable=True)
    due_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    stage_entered_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())
    created_by: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.user_id"), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now())

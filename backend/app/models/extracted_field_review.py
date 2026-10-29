from datetime import datetime
from uuid import UUID as PythonUUID

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    String,
    Text,
    func,
    text,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.session import Base


class ExtractedFieldReview(Base):
    """Regulatory audit record capturing human Auditor / Lead Auditor verification,

    acceptance, or correction of automated candidate extractions.
    Strictly append-only; database triggers prevent UPDATE, DELETE, and TRUNCATE.
    """

    __tablename__ = "extracted_field_reviews"

    __table_args__ = (
        Index("idx_extracted_field_reviews_field", "extracted_field_id"),
        CheckConstraint(
            """(
                accepted_as_extracted = true
                AND corrected_value IS NULL
                AND (review_note IS NULL OR length(review_note) <= 2000)
            ) OR (
                accepted_as_extracted = false
                AND corrected_value IS NOT NULL
                AND corrected_value != 'null'::jsonb
                AND review_note IS NOT NULL
                AND length(regexp_replace(review_note, '[[:space:]]', '', 'g')) >= 5
                AND length(review_note) <= 2000
            )""",
            name="chk_extracted_field_reviews_decision",
        ),
        CheckConstraint(
            "corrected_value IS NULL OR octet_length(corrected_value::text) <= 65536",
            name="chk_extracted_field_reviews_payload_size",
        ),
        CheckConstraint(
            "reviewer_role IN ('AUDITOR', 'LEAD_AUDITOR')",
            name="chk_extracted_field_reviews_role",
        ),
    )

    extracted_field_review_id: Mapped[PythonUUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        server_default=text("gen_random_uuid()"),
    )

    extracted_field_id: Mapped[PythonUUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey(
            "extracted_fields.extracted_field_id",
            ondelete="RESTRICT",
        ),
        nullable=False,
    )

    reviewed_by: Mapped[PythonUUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey(
            "users.user_id",
            ondelete="RESTRICT",
        ),
        nullable=False,
    )

    reviewer_role: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
    )

    corrected_value: Mapped[dict | list | str | int | float | bool | None] = (
        mapped_column(
            JSONB(none_as_null=True),
            nullable=True,
        )
    )

    review_note: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    accepted_as_extracted: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        server_default=text("false"),
    )

    reviewed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )

"""Add extracted_field_reviews table with append-only database triggers.

Revision ID: a3b4c5d6e7f8
Revises: f2b3c4d5e6f7
Create Date: 2026-10-28 20:55:18.218491

Phase 4, Batch 5 (Part B):
Adds the extracted_field_reviews regulatory audit table from Schema v4 (lines 531-539).
Records human Auditor / Lead Auditor verification decisions, field acceptances, and corrections
without modifying original immutable extraction records.

Audit-History Safeguards:
1. Foreign keys enforce ON DELETE RESTRICT to guarantee referential immutability.
2. PostgreSQL row-level trigger prevents UPDATE and DELETE on review records.
3. PostgreSQL statement-level trigger prevents TRUNCATE on review records.
4. Database-level CHECK constraints enforce decision mutual-exclusivity:
   - When accepted_as_extracted is TRUE: corrected_value must be SQL NULL.
   - When accepted_as_extracted is FALSE: corrected_value must be non-null and not JSONB 'null',
     and review_note must contain at least 5 non-whitespace characters.
5. Reviewer role at submission time is persisted in 'reviewer_role' column.
6. Safe downgrade behavior: refuses to drop table if existing review records exist.
"""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

# Revision identifiers, used by Alembic.
revision: str = "a3b4c5d6e7f8"
down_revision: str | Sequence[str] | None = "f2b3c4d5e6f7"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Create extracted_field_reviews table, constraints, indexes, and immutability triggers."""
    op.create_table(
        "extracted_field_reviews",
        sa.Column(
            "extracted_field_review_id",
            sa.UUID(),
            server_default=sa.text("gen_random_uuid()"),
            nullable=False,
        ),
        sa.Column(
            "extracted_field_id",
            sa.UUID(),
            nullable=False,
        ),
        sa.Column(
            "reviewed_by",
            sa.UUID(),
            nullable=False,
        ),
        sa.Column(
            "reviewer_role",
            sa.String(length=50),
            nullable=False,
        ),
        sa.Column(
            "corrected_value",
            postgresql.JSONB(astext_type=sa.Text(), none_as_null=True),
            nullable=True,
        ),
        sa.Column(
            "review_note",
            sa.Text(),
            nullable=True,
        ),
        sa.Column(
            "accepted_as_extracted",
            sa.Boolean(),
            server_default=sa.text("false"),
            nullable=False,
        ),
        sa.Column(
            "reviewed_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["extracted_field_id"],
            ["extracted_fields.extracted_field_id"],
            name="fk_extracted_field_reviews_field_id",
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["reviewed_by"],
            ["users.user_id"],
            name="fk_extracted_field_reviews_reviewed_by",
            ondelete="RESTRICT",
        ),
        sa.CheckConstraint(
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
        sa.CheckConstraint(
            "corrected_value IS NULL OR octet_length(corrected_value::text) <= 65536",
            name="chk_extracted_field_reviews_payload_size",
        ),
        sa.CheckConstraint(
            "reviewer_role IN ('AUDITOR', 'LEAD_AUDITOR')",
            name="chk_extracted_field_reviews_role",
        ),
        sa.PrimaryKeyConstraint("extracted_field_review_id"),
    )

    op.create_index(
        "idx_extracted_field_reviews_field",
        "extracted_field_reviews",
        ["extracted_field_id"],
        unique=False,
    )

    # Database-level immutability triggers (UPDATE, DELETE, and TRUNCATE)
    op.execute(
        """
        CREATE OR REPLACE FUNCTION prevent_extracted_field_reviews_modification()
        RETURNS TRIGGER AS $$
        BEGIN
            RAISE EXCEPTION 'extracted_field_reviews is an immutable regulatory audit trail: % operations are prohibited', TG_OP;
        END;
        $$ LANGUAGE plpgsql;
        """
    )

    op.execute(
        """
        CREATE TRIGGER trg_extracted_field_reviews_prevent_update_delete
        BEFORE UPDATE OR DELETE ON extracted_field_reviews
        FOR EACH ROW
        EXECUTE FUNCTION prevent_extracted_field_reviews_modification();
        """
    )

    op.execute(
        """
        CREATE TRIGGER trg_extracted_field_reviews_prevent_truncate
        BEFORE TRUNCATE ON extracted_field_reviews
        FOR EACH STATEMENT
        EXECUTE FUNCTION prevent_extracted_field_reviews_modification();
        """
    )


def downgrade() -> None:
    """Safe downgrade of extracted_field_reviews.

    Refuses to drop the table if regulatory review history exists to prevent silent data destruction.
    Only proceeds if the table is completely empty.
    """
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    if "extracted_field_reviews" in inspector.get_table_names():
        # Concurrency safety: acquire ACCESS EXCLUSIVE lock to prevent race with concurrent insertions
        bind.execute(
            sa.text("LOCK TABLE extracted_field_reviews IN ACCESS EXCLUSIVE MODE;")
        )
        count = bind.execute(
            sa.text("SELECT count(*) FROM extracted_field_reviews")
        ).scalar()
        if count and count > 0:
            raise RuntimeError(
                f"CANNOT DOWNGRADE MIGRATION a3b4c5d6e7f8: 'extracted_field_reviews' table "
                f"contains {count} permanent regulatory audit records. "
                "Silently dropping regulatory review history is prohibited. "
                "An explicit database backup/export and separately authorized archival "
                "procedure are required before dropping this regulatory table."
            )

    op.execute(
        "DROP TRIGGER IF EXISTS trg_extracted_field_reviews_prevent_truncate ON extracted_field_reviews"
    )
    op.execute(
        "DROP TRIGGER IF EXISTS trg_extracted_field_reviews_prevent_update_delete ON extracted_field_reviews"
    )
    op.execute("DROP FUNCTION IF EXISTS prevent_extracted_field_reviews_modification()")
    op.drop_index(
        "idx_extracted_field_reviews_field",
        table_name="extracted_field_reviews",
    )
    op.drop_table("extracted_field_reviews")

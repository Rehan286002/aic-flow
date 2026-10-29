"""Add document OCR and checklist foundation

Revision ID: 905643f5b8c5
Revises: c33c142f79bd
Create Date: 2026-10-28 00:10:41.642844

"""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

application_family_enum = postgresql.ENUM(
    "NEW_INSTITUTION",
    "EXISTING_INSTITUTION",
    "UNIVERSITY",
    "OTHER",
    name="application_family",
    create_type=False,
)

document_processing_status_enum = postgresql.ENUM(
    "QUEUED",
    "PROCESSING",
    "COMPLETED",
    "PARTIAL",
    "FAILED",
    "NEEDS_MANUAL_REVIEW",
    name="document_processing_status",
    create_type=False,
)

requirement_status_enum = postgresql.ENUM(
    "PENDING",
    "UPLOADED",
    "SATISFIED",
    "DEFICIENT",
    "NOT_APPLICABLE",
    "UNABLE_TO_DETERMINE",
    "UNDER_REVIEW",
    name="requirement_status",
    create_type=False,
)

# revision identifiers, used by Alembic.
revision: str = "905643f5b8c5"
down_revision: str | Sequence[str] | None = "c33c142f79bd"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Upgrade schema."""
    # Create the two new PostgreSQL enum types.
    # application_family already exists from the initial migration.
    op.execute("""
        CREATE TYPE document_processing_status AS ENUM (
            'QUEUED',
            'PROCESSING',
            'COMPLETED',
            'PARTIAL',
            'FAILED',
            'NEEDS_MANUAL_REVIEW'
        )
    """)

    op.execute("""
        CREATE TYPE requirement_status AS ENUM (
            'PENDING',
            'UPLOADED',
            'SATISFIED',
            'DEFICIENT',
            'NOT_APPLICABLE',
            'UNABLE_TO_DETERMINE',
            'UNDER_REVIEW'
        )
    """)
    op.create_table(
        "document_types",
        sa.Column(
            "document_type_id", sa.SmallInteger(), autoincrement=True, nullable=False
        ),
        sa.Column("type_code", sa.String(length=80), nullable=False),
        sa.Column("type_name", sa.String(length=200), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column(
            "is_active", sa.Boolean(), server_default=sa.text("true"), nullable=False
        ),
        sa.PrimaryKeyConstraint("document_type_id"),
        sa.UniqueConstraint("type_code"),
    )
    op.create_table(
        "validation_rules",
        sa.Column(
            "validation_rule_id",
            sa.UUID(),
            server_default=sa.text("gen_random_uuid()"),
            nullable=False,
        ),
        sa.Column("rule_code", sa.String(length=100), nullable=False),
        sa.Column("rule_name", sa.String(length=250), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("rule_category", sa.String(length=80), nullable=False),
        sa.Column(
            "is_active", sa.Boolean(), server_default=sa.text("true"), nullable=False
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("validation_rule_id"),
        sa.UniqueConstraint("rule_code"),
    )
    op.create_table(
        "checklist_templates",
        sa.Column(
            "checklist_template_id",
            sa.UUID(),
            server_default=sa.text("gen_random_uuid()"),
            nullable=False,
        ),
        sa.Column("template_code", sa.String(length=100), nullable=False),
        sa.Column("template_name", sa.String(length=200), nullable=False),
        sa.Column("application_family", application_family_enum, nullable=False),
        sa.Column("academic_year_from", sa.String(length=9), nullable=False),
        sa.Column("academic_year_to", sa.String(length=9), nullable=True),
        sa.Column("version_number", sa.Integer(), nullable=False),
        sa.Column("regulatory_reference", sa.Text(), nullable=True),
        sa.Column(
            "is_published",
            sa.Boolean(),
            server_default=sa.text("false"),
            nullable=False,
        ),
        sa.Column("created_by", sa.UUID(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.CheckConstraint("version_number > 0", name="chk_checklist_template_version"),
        sa.ForeignKeyConstraint(
            ["created_by"],
            ["users.user_id"],
        ),
        sa.PrimaryKeyConstraint("checklist_template_id"),
        sa.UniqueConstraint(
            "template_code", "version_number", name="uq_checklist_template_version"
        ),
    )
    op.create_table(
        "documents",
        sa.Column(
            "document_id",
            sa.UUID(),
            server_default=sa.text("gen_random_uuid()"),
            nullable=False,
        ),
        sa.Column("institution_id", sa.UUID(), nullable=False),
        sa.Column("document_type_id", sa.SmallInteger(), nullable=True),
        sa.Column("document_label", sa.String(length=250), nullable=True),
        sa.Column("created_by", sa.UUID(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["created_by"],
            ["users.user_id"],
        ),
        sa.ForeignKeyConstraint(
            ["document_type_id"],
            ["document_types.document_type_id"],
        ),
        sa.ForeignKeyConstraint(
            ["institution_id"],
            ["institutions.institution_id"],
        ),
        sa.PrimaryKeyConstraint("document_id"),
    )
    op.create_table(
        "validation_rule_versions",
        sa.Column(
            "validation_rule_version_id",
            sa.UUID(),
            server_default=sa.text("gen_random_uuid()"),
            nullable=False,
        ),
        sa.Column("validation_rule_id", sa.UUID(), nullable=False),
        sa.Column("version_number", sa.Integer(), nullable=False),
        sa.Column("application_family", application_family_enum, nullable=True),
        sa.Column("academic_year_from", sa.String(length=9), nullable=True),
        sa.Column("academic_year_to", sa.String(length=9), nullable=True),
        sa.Column("effective_from", sa.Date(), nullable=True),
        sa.Column("effective_to", sa.Date(), nullable=True),
        sa.Column(
            "condition_json",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default=sa.text("'{}'::jsonb"),
            nullable=False,
        ),
        sa.Column(
            "evaluation_config",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default=sa.text("'{}'::jsonb"),
            nullable=False,
        ),
        sa.Column("regulatory_reference", sa.Text(), nullable=True),
        sa.Column(
            "is_enabled", sa.Boolean(), server_default=sa.text("true"), nullable=False
        ),
        sa.Column("approved_by", sa.UUID(), nullable=True),
        sa.Column("approved_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.CheckConstraint(
            "version_number > 0", name="chk_validation_rule_version_number"
        ),
        sa.ForeignKeyConstraint(
            ["approved_by"],
            ["users.user_id"],
        ),
        sa.ForeignKeyConstraint(
            ["validation_rule_id"],
            ["validation_rules.validation_rule_id"],
        ),
        sa.PrimaryKeyConstraint("validation_rule_version_id"),
        sa.UniqueConstraint(
            "validation_rule_id", "version_number", name="uq_validation_rule_version"
        ),
    )
    op.create_table(
        "checklist_items",
        sa.Column(
            "checklist_item_id",
            sa.UUID(),
            server_default=sa.text("gen_random_uuid()"),
            nullable=False,
        ),
        sa.Column("checklist_template_id", sa.UUID(), nullable=False),
        sa.Column("item_code", sa.String(length=100), nullable=False),
        sa.Column("title", sa.String(length=250), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("expected_document_type_code", sa.String(length=80), nullable=True),
        sa.Column(
            "is_mandatory_by_default",
            sa.Boolean(),
            server_default=sa.text("true"),
            nullable=False,
        ),
        sa.Column(
            "applicability_condition",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default=sa.text("'{}'::jsonb"),
            nullable=False,
        ),
        sa.Column(
            "validation_config",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default=sa.text("'{}'::jsonb"),
            nullable=False,
        ),
        sa.Column("regulatory_clause_reference", sa.Text(), nullable=True),
        sa.Column(
            "display_order", sa.Integer(), server_default=sa.text("0"), nullable=False
        ),
        sa.ForeignKeyConstraint(
            ["checklist_template_id"],
            ["checklist_templates.checklist_template_id"],
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("checklist_item_id"),
        sa.UniqueConstraint(
            "checklist_template_id", "item_code", name="uq_checklist_item_code"
        ),
    )
    op.create_table(
        "document_versions",
        sa.Column(
            "document_version_id",
            sa.UUID(),
            server_default=sa.text("gen_random_uuid()"),
            nullable=False,
        ),
        sa.Column("document_id", sa.UUID(), nullable=False),
        sa.Column("version_number", sa.Integer(), nullable=False),
        sa.Column("original_filename", sa.String(length=500), nullable=False),
        sa.Column("storage_key", sa.Text(), nullable=False),
        sa.Column("mime_type", sa.String(length=150), nullable=False),
        sa.Column("file_size_bytes", sa.BigInteger(), nullable=False),
        sa.Column("sha256_hex", sa.CHAR(length=64), nullable=False),
        sa.Column("page_count", sa.Integer(), nullable=True),
        sa.Column("uploaded_by", sa.UUID(), nullable=False),
        sa.Column("replaces_document_version_id", sa.UUID(), nullable=True),
        sa.Column(
            "uploaded_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.CheckConstraint("file_size_bytes > 0", name="chk_document_file_size"),
        sa.CheckConstraint(
            "page_count IS NULL OR page_count >= 0", name="chk_document_page_count"
        ),
        sa.CheckConstraint("version_number > 0", name="chk_document_version_number"),
        sa.ForeignKeyConstraint(
            ["document_id"], ["documents.document_id"], ondelete="RESTRICT"
        ),
        sa.ForeignKeyConstraint(
            ["replaces_document_version_id"],
            ["document_versions.document_version_id"],
        ),
        sa.ForeignKeyConstraint(
            ["uploaded_by"],
            ["users.user_id"],
        ),
        sa.PrimaryKeyConstraint("document_version_id"),
        sa.UniqueConstraint(
            "document_id", "version_number", name="uq_document_version_number"
        ),
    )
    op.create_index(
        "idx_document_versions_hash", "document_versions", ["sha256_hex"], unique=False
    )
    op.create_table(
        "application_requirements",
        sa.Column(
            "application_requirement_id",
            sa.UUID(),
            server_default=sa.text("gen_random_uuid()"),
            nullable=False,
        ),
        sa.Column("application_revision_id", sa.UUID(), nullable=False),
        sa.Column("checklist_item_id", sa.UUID(), nullable=False),
        sa.Column("applicability_status", sa.String(length=20), nullable=False),
        sa.Column(
            "status",
            requirement_status_enum,
            server_default=sa.text("'PENDING'"),
            nullable=False,
        ),
        sa.Column("determination_reason", sa.Text(), nullable=True),
        sa.Column("last_evaluated_at", sa.DateTime(timezone=True), nullable=True),
        sa.CheckConstraint(
            "applicability_status IN ('APPLICABLE', 'NOT_APPLICABLE', 'PENDING_DETERMINATION')",
            name="chk_application_requirement_applicability",
        ),
        sa.ForeignKeyConstraint(
            ["application_revision_id"],
            ["application_revisions.application_revision_id"],
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["checklist_item_id"],
            ["checklist_items.checklist_item_id"],
        ),
        sa.PrimaryKeyConstraint("application_requirement_id"),
        sa.UniqueConstraint(
            "application_revision_id",
            "checklist_item_id",
            name="uq_application_revision_checklist_item",
        ),
    )
    op.create_table(
        "checklist_item_rules",
        sa.Column("checklist_item_id", sa.UUID(), nullable=False),
        sa.Column("validation_rule_id", sa.UUID(), nullable=False),
        sa.ForeignKeyConstraint(
            ["checklist_item_id"],
            ["checklist_items.checklist_item_id"],
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["validation_rule_id"],
            ["validation_rules.validation_rule_id"],
        ),
        sa.PrimaryKeyConstraint("checklist_item_id", "validation_rule_id"),
    )
    op.create_table(
        "document_processing_jobs",
        sa.Column(
            "document_processing_job_id",
            sa.UUID(),
            server_default=sa.text("gen_random_uuid()"),
            nullable=False,
        ),
        sa.Column("document_version_id", sa.UUID(), nullable=False),
        sa.Column(
            "processing_status",
            document_processing_status_enum,
            server_default=sa.text("'QUEUED'"),
            nullable=False,
        ),
        sa.Column("pipeline_name", sa.String(length=100), nullable=False),
        sa.Column("pipeline_version", sa.String(length=80), nullable=True),
        sa.Column(
            "queued_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("error_code", sa.String(length=100), nullable=True),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.ForeignKeyConstraint(
            ["document_version_id"],
            ["document_versions.document_version_id"],
        ),
        sa.PrimaryKeyConstraint("document_processing_job_id"),
    )
    op.create_table(
        "application_document_links",
        sa.Column(
            "application_document_link_id",
            sa.UUID(),
            server_default=sa.text("gen_random_uuid()"),
            nullable=False,
        ),
        sa.Column("application_revision_id", sa.UUID(), nullable=False),
        sa.Column("uploaded_for_requirement_id", sa.UUID(), nullable=True),
        sa.Column("document_version_id", sa.UUID(), nullable=False),
        sa.Column(
            "linked_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["application_revision_id"],
            ["application_revisions.application_revision_id"],
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["document_version_id"],
            ["document_versions.document_version_id"],
        ),
        sa.ForeignKeyConstraint(
            ["uploaded_for_requirement_id"],
            ["application_requirements.application_requirement_id"],
        ),
        sa.PrimaryKeyConstraint("application_document_link_id"),
        sa.UniqueConstraint(
            "application_revision_id",
            "document_version_id",
            name="uq_application_document_revision",
        ),
    )
    op.create_index(
        "idx_application_document_revision",
        "application_document_links",
        ["application_revision_id"],
        unique=False,
    )
    op.create_table(
        "document_extractions",
        sa.Column(
            "document_extraction_id",
            sa.UUID(),
            server_default=sa.text("gen_random_uuid()"),
            nullable=False,
        ),
        sa.Column("document_version_id", sa.UUID(), nullable=False),
        sa.Column("processing_job_id", sa.UUID(), nullable=True),
        sa.Column("extraction_status", document_processing_status_enum, nullable=False),
        sa.Column("extraction_engine", sa.String(length=120), nullable=False),
        sa.Column("engine_version", sa.String(length=80), nullable=True),
        sa.Column("language_code", sa.String(length=20), nullable=True),
        sa.Column("full_text_storage_key", sa.Text(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["document_version_id"],
            ["document_versions.document_version_id"],
        ),
        sa.ForeignKeyConstraint(
            ["processing_job_id"],
            ["document_processing_jobs.document_processing_job_id"],
        ),
        sa.PrimaryKeyConstraint("document_extraction_id"),
    )
    op.create_table(
        "extracted_fields",
        sa.Column(
            "extracted_field_id",
            sa.UUID(),
            server_default=sa.text("gen_random_uuid()"),
            nullable=False,
        ),
        sa.Column("document_extraction_id", sa.UUID(), nullable=False),
        sa.Column("field_code", sa.String(length=120), nullable=False),
        sa.Column("field_label", sa.String(length=200), nullable=True),
        sa.Column("raw_value", sa.Text(), nullable=True),
        sa.Column(
            "normalized_value", postgresql.JSONB(astext_type=sa.Text()), nullable=True
        ),
        sa.Column("confidence", sa.Numeric(precision=5, scale=4), nullable=True),
        sa.Column("page_number", sa.Integer(), nullable=True),
        sa.Column(
            "bounding_box", postgresql.JSONB(astext_type=sa.Text()), nullable=True
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.CheckConstraint(
            "confidence IS NULL OR confidence BETWEEN 0 AND 1",
            name="chk_extracted_field_confidence",
        ),
        sa.CheckConstraint(
            "page_number IS NULL OR page_number > 0", name="chk_extracted_field_page"
        ),
        sa.ForeignKeyConstraint(
            ["document_extraction_id"],
            ["document_extractions.document_extraction_id"],
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("extracted_field_id"),
    )
    op.create_index(
        "idx_extracted_fields_code", "extracted_fields", ["field_code"], unique=False
    )
    # ### end Alembic commands ###


def downgrade() -> None:
    """Downgrade schema."""
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_index("idx_extracted_fields_code", table_name="extracted_fields")
    op.drop_table("extracted_fields")
    op.drop_table("document_extractions")
    op.drop_index(
        "idx_application_document_revision", table_name="application_document_links"
    )
    op.drop_table("application_document_links")
    op.drop_table("document_processing_jobs")
    op.drop_table("checklist_item_rules")
    op.drop_table("application_requirements")
    op.drop_index("idx_document_versions_hash", table_name="document_versions")
    op.drop_table("document_versions")
    op.drop_table("checklist_items")
    op.drop_table("validation_rule_versions")
    op.drop_table("documents")
    op.drop_table("checklist_templates")
    op.drop_table("validation_rules")
    op.drop_table("document_types")

    # Drop only enum types introduced by this migration.
    op.execute("DROP TYPE requirement_status")
    op.execute("DROP TYPE document_processing_status")

    # application_family belongs to the initial migration.
    # Do not drop it here.
    # ### end Alembic commands ###

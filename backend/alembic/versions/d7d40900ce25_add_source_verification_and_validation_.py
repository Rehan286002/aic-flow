"""add source verification and validation engine

Revision ID: d7d40900ce25
Revises: 905643f5b8c5
Create Date: 2026-10-28 00:43:30.101954

"""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

# Revision identifiers, used by Alembic.
revision: str = "d7d40900ce25"
down_revision: str | Sequence[str] | None = "905643f5b8c5"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


# ---------------------------------------------------------------------------
# PostgreSQL ENUM definitions
#
# These types are created explicitly in upgrade() and dropped explicitly
# in downgrade(). create_type=False prevents SQLAlchemy from attempting
# automatic duplicate creation when the tables are created.
#
# All six types are new in this migration. Existing enum types from earlier
# migrations are deliberately not recreated or modified.
# ---------------------------------------------------------------------------

source_type_enum = postgresql.ENUM(
    "ISSUING_AUTHORITY",
    "DIGITAL_REPOSITORY",
    "UNIVERSITY",
    "GOVERNMENT_PORTAL",
    "INTERNAL_REFERENCE",
    name="source_type",
    create_type=False,
)

verification_method_enum = postgresql.ENUM(
    "QR_CODE",
    "OFFICIAL_API",
    "OFFICIAL_PORTAL",
    "DIGILOCKER",
    "DIGITAL_SIGNATURE",
    "MANUAL",
    name="verification_method",
    create_type=False,
)

verification_status_enum = postgresql.ENUM(
    "PENDING",
    "VERIFIED",
    "MISMATCH",
    "EXPIRED",
    "SOURCE_UNAVAILABLE",
    "MANUAL_REVIEW_REQUIRED",
    "FAILED",
    "CANCELLED",
    name="verification_status",
    create_type=False,
)

finding_category_enum = postgresql.ENUM(
    "MISSING_DOCUMENT",
    "INCOMPLETE_DOCUMENT",
    "EXPIRED_DOCUMENT",
    "FIELD_MISMATCH",
    "DUPLICATE_DOCUMENT",
    "METADATA_ANOMALY",
    "CONTENT_ANOMALY",
    "SIGNATURE_ISSUE",
    "SOURCE_MISMATCH",
    "SOURCE_UNAVAILABLE",
    "LOW_OCR_CONFIDENCE",
    "REGULATORY_GAP",
    "INFRASTRUCTURE_OBSERVATION",
    "OTHER",
    name="finding_category",
    create_type=False,
)

finding_severity_enum = postgresql.ENUM(
    "INFO",
    "LOW",
    "MEDIUM",
    "HIGH",
    "CRITICAL",
    name="finding_severity",
    create_type=False,
)

finding_status_enum = postgresql.ENUM(
    "OPEN",
    "ACCEPTED",
    "DISMISSED",
    "CLARIFICATION_REQUESTED",
    "ESCALATED",
    "RESOLVED",
    "SUPERSEDED",
    name="finding_status",
    create_type=False,
)


# ---------------------------------------------------------------------------
# UPGRADE
# ---------------------------------------------------------------------------


def upgrade() -> None:
    """Upgrade schema."""

    # Create the six new PostgreSQL enum types before creating dependent
    # tables. These types do not exist in the previous migrations.

    op.execute("""
        CREATE TYPE source_type AS ENUM (
            'ISSUING_AUTHORITY',
            'DIGITAL_REPOSITORY',
            'UNIVERSITY',
            'GOVERNMENT_PORTAL',
            'INTERNAL_REFERENCE'
        )
    """)

    op.execute("""
        CREATE TYPE verification_method AS ENUM (
            'QR_CODE',
            'OFFICIAL_API',
            'OFFICIAL_PORTAL',
            'DIGILOCKER',
            'DIGITAL_SIGNATURE',
            'MANUAL'
        )
    """)

    op.execute("""
        CREATE TYPE verification_status AS ENUM (
            'PENDING',
            'VERIFIED',
            'MISMATCH',
            'EXPIRED',
            'SOURCE_UNAVAILABLE',
            'MANUAL_REVIEW_REQUIRED',
            'FAILED',
            'CANCELLED'
        )
    """)

    op.execute("""
        CREATE TYPE finding_category AS ENUM (
            'MISSING_DOCUMENT',
            'INCOMPLETE_DOCUMENT',
            'EXPIRED_DOCUMENT',
            'FIELD_MISMATCH',
            'DUPLICATE_DOCUMENT',
            'METADATA_ANOMALY',
            'CONTENT_ANOMALY',
            'SIGNATURE_ISSUE',
            'SOURCE_MISMATCH',
            'SOURCE_UNAVAILABLE',
            'LOW_OCR_CONFIDENCE',
            'REGULATORY_GAP',
            'INFRASTRUCTURE_OBSERVATION',
            'OTHER'
        )
    """)

    op.execute("""
        CREATE TYPE finding_severity AS ENUM (
            'INFO',
            'LOW',
            'MEDIUM',
            'HIGH',
            'CRITICAL'
        )
    """)

    op.execute("""
        CREATE TYPE finding_status AS ENUM (
            'OPEN',
            'ACCEPTED',
            'DISMISSED',
            'CLARIFICATION_REQUESTED',
            'ESCALATED',
            'RESOLVED',
            'SUPERSEDED'
        )
    """)

    # -----------------------------------------------------------------------
    # 1. Verification sources
    # -----------------------------------------------------------------------

    op.create_table(
        "verification_sources",
        sa.Column(
            "verification_source_id",
            sa.UUID(),
            server_default=sa.text("gen_random_uuid()"),
            nullable=False,
        ),
        sa.Column("source_code", sa.String(length=100), nullable=False),
        sa.Column("source_name", sa.String(length=250), nullable=False),
        sa.Column("source_type", source_type_enum, nullable=False),
        sa.Column(
            "supported_document_types",
            postgresql.ARRAY(sa.SmallInteger()),
            nullable=True,
        ),
        sa.Column("official_domain", sa.String(length=255), nullable=True),
        sa.Column("integration_mode", sa.String(length=40), nullable=False),
        sa.Column(
            "is_authorized",
            sa.Boolean(),
            server_default=sa.text("false"),
            nullable=False,
        ),
        sa.Column(
            "is_enabled",
            sa.Boolean(),
            server_default=sa.text("false"),
            nullable=False,
        ),
        sa.Column("credential_secret_reference", sa.Text(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.CheckConstraint(
            "integration_mode IN "
            "('API', 'PORTAL', 'QR_RESOLUTION', 'DIGITAL_SIGNATURE', "
            "'MANUAL', 'MOCK')",
            name="chk_verification_source_integration_mode",
        ),
        sa.PrimaryKeyConstraint("verification_source_id"),
        sa.UniqueConstraint("source_code"),
    )

    # -----------------------------------------------------------------------
    # 2. Source synchronization runs
    # -----------------------------------------------------------------------

    op.create_table(
        "source_sync_runs",
        sa.Column(
            "source_sync_run_id",
            sa.UUID(),
            server_default=sa.text("gen_random_uuid()"),
            nullable=False,
        ),
        sa.Column("verification_source_id", sa.UUID(), nullable=False),
        sa.Column("environment", sa.String(length=20), nullable=False),
        sa.Column("sync_kind", sa.String(length=40), nullable=False),
        sa.Column("adapter_version", sa.String(length=80), nullable=False),
        sa.Column("status", sa.String(length=24), nullable=False),
        sa.Column(
            "request_correlation_id",
            sa.String(length=160),
            nullable=True,
        ),
        sa.Column(
            "source_published_at",
            sa.DateTime(timezone=True),
            nullable=True,
        ),
        sa.Column(
            "source_updated_at",
            sa.DateTime(timezone=True),
            nullable=True,
        ),
        sa.Column(
            "started_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "completed_at",
            sa.DateTime(timezone=True),
            nullable=True,
        ),
        sa.Column(
            "records_received",
            sa.Integer(),
            server_default=sa.text("0"),
            nullable=False,
        ),
        sa.Column("response_sha256", sa.CHAR(length=64), nullable=True),
        sa.Column(
            "sanitized_summary",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default=sa.text("'{}'::jsonb"),
            nullable=False,
        ),
        sa.Column("error_code", sa.String(length=100), nullable=True),
        sa.Column("error_summary", sa.Text(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.CheckConstraint(
            "environment IN ('SIMULATED', 'SANDBOX', 'PRODUCTION', 'PUBLIC_DATA')",
            name="chk_source_sync_environment",
        ),
        sa.CheckConstraint(
            "status IN "
            "('QUEUED', 'RUNNING', 'SUCCEEDED', 'PARTIAL', "
            "'FAILED', 'CANCELLED')",
            name="chk_source_sync_status",
        ),
        sa.CheckConstraint(
            "sync_kind IN ('FULL', 'INCREMENTAL', 'ON_DEMAND', 'HEALTH_CHECK')",
            name="chk_source_sync_kind",
        ),
        sa.CheckConstraint(
            "completed_at IS NULL OR completed_at >= started_at",
            name="chk_source_sync_completed_at",
        ),
        sa.CheckConstraint(
            "records_received >= 0",
            name="chk_source_sync_records_received",
        ),
        sa.ForeignKeyConstraint(
            ["verification_source_id"],
            ["verification_sources.verification_source_id"],
        ),
        sa.PrimaryKeyConstraint("source_sync_run_id"),
    )

    op.create_index(
        "idx_source_sync_runs_source_time",
        "source_sync_runs",
        [
            "verification_source_id",
            sa.literal_column("started_at DESC"),
        ],
        unique=False,
    )

    op.create_index(
        "idx_source_sync_runs_status_time",
        "source_sync_runs",
        [
            "status",
            sa.literal_column("started_at DESC"),
        ],
        unique=False,
    )

    # -----------------------------------------------------------------------
    # 3. Institution record versions
    # -----------------------------------------------------------------------

    op.create_table(
        "institution_record_versions",
        sa.Column(
            "institution_record_version_id",
            sa.UUID(),
            server_default=sa.text("gen_random_uuid()"),
            nullable=False,
        ),
        sa.Column("institution_id", sa.UUID(), nullable=False),
        sa.Column("record_version", sa.Integer(), nullable=False),
        sa.Column(
            "record_data",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
        ),
        sa.Column("source_system", sa.String(length=120), nullable=False),
        sa.Column("source_reference", sa.Text(), nullable=True),
        sa.Column(
            "effective_from",
            sa.DateTime(timezone=True),
            nullable=False,
        ),
        sa.Column(
            "effective_to",
            sa.DateTime(timezone=True),
            nullable=True,
        ),
        sa.Column(
            "recorded_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column("recorded_by", sa.UUID(), nullable=True),
        sa.Column("source_sync_run_id", sa.UUID(), nullable=True),
        sa.Column(
            "source_updated_at",
            sa.DateTime(timezone=True),
            nullable=True,
        ),
        sa.Column("source_payload_sha256", sa.CHAR(length=64), nullable=True),
        sa.CheckConstraint(
            "record_version > 0",
            name="chk_institution_record_version",
        ),
        sa.ForeignKeyConstraint(
            ["institution_id"],
            ["institutions.institution_id"],
        ),
        sa.ForeignKeyConstraint(
            ["recorded_by"],
            ["users.user_id"],
        ),
        sa.ForeignKeyConstraint(
            ["source_sync_run_id"],
            ["source_sync_runs.source_sync_run_id"],
        ),
        sa.PrimaryKeyConstraint("institution_record_version_id"),
        sa.UniqueConstraint(
            "institution_id",
            "record_version",
            name="uq_institution_record_version",
        ),
    )

    op.create_index(
        "idx_institution_record_versions_source_sync",
        "institution_record_versions",
        ["source_sync_run_id"],
        unique=False,
    )

    # -----------------------------------------------------------------------
    # 4. Digital signature checks
    # -----------------------------------------------------------------------

    op.create_table(
        "digital_signature_checks",
        sa.Column(
            "digital_signature_check_id",
            sa.UUID(),
            server_default=sa.text("gen_random_uuid()"),
            nullable=False,
        ),
        sa.Column("document_version_id", sa.UUID(), nullable=False),
        sa.Column(
            "signature_index",
            sa.Integer(),
            server_default=sa.text("0"),
            nullable=False,
        ),
        sa.Column("signature_format", sa.String(length=40), nullable=True),
        sa.Column("digest_algorithm", sa.String(length=40), nullable=True),
        sa.Column("signer_subject", sa.Text(), nullable=True),
        sa.Column(
            "signer_certificate_fingerprint",
            sa.CHAR(length=64),
            nullable=True,
        ),
        sa.Column("signature_integrity_valid", sa.Boolean(), nullable=True),
        sa.Column("certificate_chain_valid", sa.Boolean(), nullable=True),
        sa.Column("revocation_status", sa.String(length=32), nullable=True),
        sa.Column("timestamp_status", sa.String(length=32), nullable=True),
        sa.Column("trust_policy_id", sa.String(length=120), nullable=True),
        sa.Column(
            "validation_details",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default=sa.text("'{}'::jsonb"),
            nullable=False,
        ),
        sa.Column(
            "checked_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.CheckConstraint(
            "revocation_status IS NULL OR revocation_status IN "
            "('GOOD', 'REVOKED', 'UNKNOWN', 'UNAVAILABLE', 'NOT_CHECKED')",
            name="chk_signature_revocation_status",
        ),
        sa.CheckConstraint(
            "timestamp_status IS NULL OR timestamp_status IN "
            "('VALID', 'INVALID', 'UNAVAILABLE', 'NOT_PRESENT', 'NOT_CHECKED')",
            name="chk_signature_timestamp_status",
        ),
        sa.ForeignKeyConstraint(
            ["document_version_id"],
            ["document_versions.document_version_id"],
        ),
        sa.PrimaryKeyConstraint("digital_signature_check_id"),
    )

    # -----------------------------------------------------------------------
    # 5. Document integrity checks
    # -----------------------------------------------------------------------

    op.create_table(
        "document_integrity_checks",
        sa.Column(
            "document_integrity_check_id",
            sa.UUID(),
            server_default=sa.text("gen_random_uuid()"),
            nullable=False,
        ),
        sa.Column("document_version_id", sa.UUID(), nullable=False),
        sa.Column("check_type", sa.String(length=80), nullable=False),
        sa.Column("outcome", sa.String(length=40), nullable=False),
        sa.Column(
            "details",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default=sa.text("'{}'::jsonb"),
            nullable=False,
        ),
        sa.Column("tool_name", sa.String(length=120), nullable=True),
        sa.Column("tool_version", sa.String(length=80), nullable=True),
        sa.Column(
            "checked_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.CheckConstraint(
            "check_type IN "
            "('HASH_DUPLICATE', 'PDF_METADATA', "
            "'VISUAL_TAMPERING_INDICATOR', 'SIGNATURE_STRUCTURE', "
            "'FILE_STRUCTURE')",
            name="chk_document_integrity_check_type",
        ),
        sa.CheckConstraint(
            "outcome IN ('PASS', 'WARNING', 'ANOMALY', 'ERROR', 'INCONCLUSIVE')",
            name="chk_document_integrity_outcome",
        ),
        sa.ForeignKeyConstraint(
            ["document_version_id"],
            ["document_versions.document_version_id"],
        ),
        sa.PrimaryKeyConstraint("document_integrity_check_id"),
    )

    # -----------------------------------------------------------------------
    # 6. Document metadata observations
    # -----------------------------------------------------------------------

    op.create_table(
        "document_metadata_observations",
        sa.Column(
            "document_metadata_observation_id",
            sa.UUID(),
            server_default=sa.text("gen_random_uuid()"),
            nullable=False,
        ),
        sa.Column("document_version_id", sa.UUID(), nullable=False),
        sa.Column("metadata_source", sa.String(length=40), nullable=False),
        sa.Column("metadata_key", sa.String(length=160), nullable=False),
        sa.Column("metadata_value", sa.Text(), nullable=True),
        sa.Column(
            "trust_level",
            sa.String(length=24),
            server_default=sa.text("'UNTRUSTED'"),
            nullable=False,
        ),
        sa.Column(
            "observed_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.CheckConstraint(
            "metadata_source IN "
            "('PDF_INFO', 'XMP', 'EXIF', 'FILE_SYSTEM', 'SERVER_INGEST')",
            name="chk_document_metadata_source",
        ),
        sa.CheckConstraint(
            "trust_level IN "
            "('UNTRUSTED', 'SERVER_OBSERVED', 'CRYPTOGRAPHICALLY_BOUND')",
            name="chk_document_metadata_trust_level",
        ),
        sa.ForeignKeyConstraint(
            ["document_version_id"],
            ["document_versions.document_version_id"],
        ),
        sa.PrimaryKeyConstraint("document_metadata_observation_id"),
    )

    # -----------------------------------------------------------------------
    # 7. Document security scans
    # -----------------------------------------------------------------------

    op.create_table(
        "document_security_scans",
        sa.Column(
            "document_security_scan_id",
            sa.UUID(),
            server_default=sa.text("gen_random_uuid()"),
            nullable=False,
        ),
        sa.Column("document_version_id", sa.UUID(), nullable=False),
        sa.Column("scanner_name", sa.String(length=120), nullable=False),
        sa.Column("scanner_version", sa.String(length=80), nullable=True),
        sa.Column(
            "signature_database_version",
            sa.String(length=100),
            nullable=True,
        ),
        sa.Column("scan_status", sa.String(length=24), nullable=False),
        sa.Column("threat_name", sa.String(length=240), nullable=True),
        sa.Column(
            "scanned_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column("scan_log_reference", sa.Text(), nullable=True),
        sa.CheckConstraint(
            "scan_status IN ('CLEAN', 'DETECTED', 'ERROR', 'NOT_SCANNED')",
            name="chk_document_security_scan_status",
        ),
        sa.ForeignKeyConstraint(
            ["document_version_id"],
            ["document_versions.document_version_id"],
        ),
        sa.PrimaryKeyConstraint("document_security_scan_id"),
    )

    # -----------------------------------------------------------------------
    # 8. Validation runs
    # -----------------------------------------------------------------------

    op.create_table(
        "validation_runs",
        sa.Column(
            "validation_run_id",
            sa.UUID(),
            server_default=sa.text("gen_random_uuid()"),
            nullable=False,
        ),
        sa.Column("application_revision_id", sa.UUID(), nullable=False),
        sa.Column("checklist_template_id", sa.UUID(), nullable=True),
        sa.Column("triggered_by", sa.UUID(), nullable=True),
        sa.Column("run_type", sa.String(length=40), nullable=False),
        sa.Column("engine_version", sa.String(length=80), nullable=True),
        sa.Column("status", sa.String(length=30), nullable=False),
        sa.Column(
            "started_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "completed_at",
            sa.DateTime(timezone=True),
            nullable=True,
        ),
        sa.Column(
            "evaluation_as_of",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.CheckConstraint(
            "run_type IN ('FULL', 'DOCUMENT_ONLY', 'RULE_ONLY', 'RECHECK')",
            name="chk_validation_run_type",
        ),
        sa.CheckConstraint(
            "status IN ('QUEUED', 'RUNNING', 'COMPLETED', 'PARTIAL', 'FAILED')",
            name="chk_validation_run_status",
        ),
        sa.CheckConstraint(
            "completed_at IS NULL OR completed_at >= started_at",
            name="chk_validation_run_completed_at",
        ),
        sa.ForeignKeyConstraint(
            ["application_revision_id"],
            ["application_revisions.application_revision_id"],
        ),
        sa.ForeignKeyConstraint(
            ["checklist_template_id"],
            ["checklist_templates.checklist_template_id"],
        ),
        sa.ForeignKeyConstraint(
            ["triggered_by"],
            ["users.user_id"],
        ),
        sa.PrimaryKeyConstraint("validation_run_id"),
    )

    # -----------------------------------------------------------------------
    # 9. Verification attempts
    # -----------------------------------------------------------------------

    op.create_table(
        "verification_attempts",
        sa.Column(
            "verification_attempt_id",
            sa.UUID(),
            server_default=sa.text("gen_random_uuid()"),
            nullable=False,
        ),
        sa.Column("document_version_id", sa.UUID(), nullable=False),
        sa.Column("verification_source_id", sa.UUID(), nullable=True),
        sa.Column("method", verification_method_enum, nullable=False),
        sa.Column(
            "status",
            verification_status_enum,
            server_default=sa.text("'PENDING'"),
            nullable=False,
        ),
        sa.Column("requested_by", sa.UUID(), nullable=True),
        sa.Column(
            "source_reference_number",
            sa.String(length=200),
            nullable=True,
        ),
        sa.Column(
            "request_correlation_id",
            sa.String(length=160),
            nullable=True,
        ),
        sa.Column(
            "response_summary",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default=sa.text("'{}'::jsonb"),
            nullable=False,
        ),
        sa.Column(
            "compared_fields",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default=sa.text("'{}'::jsonb"),
            nullable=False,
        ),
        sa.Column("source_response_reference", sa.Text(), nullable=True),
        sa.Column(
            "requested_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "completed_at",
            sa.DateTime(timezone=True),
            nullable=True,
        ),
        sa.ForeignKeyConstraint(
            ["document_version_id"],
            ["document_versions.document_version_id"],
        ),
        sa.ForeignKeyConstraint(
            ["requested_by"],
            ["users.user_id"],
        ),
        sa.ForeignKeyConstraint(
            ["verification_source_id"],
            ["verification_sources.verification_source_id"],
        ),
        sa.PrimaryKeyConstraint("verification_attempt_id"),
    )

    op.create_index(
        "idx_verification_doc_status",
        "verification_attempts",
        ["document_version_id", "status"],
        unique=False,
    )

    # -----------------------------------------------------------------------
    # 10. Validation results
    # -----------------------------------------------------------------------

    op.create_table(
        "validation_results",
        sa.Column(
            "validation_result_id",
            sa.UUID(),
            server_default=sa.text("gen_random_uuid()"),
            nullable=False,
        ),
        sa.Column("validation_run_id", sa.UUID(), nullable=False),
        sa.Column("application_requirement_id", sa.UUID(), nullable=True),
        sa.Column("validation_rule_version_id", sa.UUID(), nullable=True),
        sa.Column("result_status", sa.String(length=30), nullable=False),
        sa.Column(
            "expected_value",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=True,
        ),
        sa.Column(
            "observed_value",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=True,
        ),
        sa.Column("explanation", sa.Text(), nullable=False),
        sa.Column(
            "evaluated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.CheckConstraint(
            "result_status IN "
            "('SATISFIED', 'DEFICIENT', 'NOT_APPLICABLE', "
            "'UNABLE_TO_DETERMINE', 'WARNING')",
            name="chk_validation_result_status",
        ),
        sa.ForeignKeyConstraint(
            ["application_requirement_id"],
            ["application_requirements.application_requirement_id"],
        ),
        sa.ForeignKeyConstraint(
            ["validation_rule_version_id"],
            ["validation_rule_versions.validation_rule_version_id"],
        ),
        sa.ForeignKeyConstraint(
            ["validation_run_id"],
            ["validation_runs.validation_run_id"],
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("validation_result_id"),
    )

    # -----------------------------------------------------------------------
    # 11. Validation run rule versions
    # -----------------------------------------------------------------------

    op.create_table(
        "validation_run_rule_versions",
        sa.Column("validation_run_id", sa.UUID(), nullable=False),
        sa.Column("validation_rule_version_id", sa.UUID(), nullable=False),
        sa.ForeignKeyConstraint(
            ["validation_rule_version_id"],
            ["validation_rule_versions.validation_rule_version_id"],
        ),
        sa.ForeignKeyConstraint(
            ["validation_run_id"],
            ["validation_runs.validation_run_id"],
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint(
            "validation_run_id",
            "validation_rule_version_id",
        ),
    )

    # -----------------------------------------------------------------------
    # 12. Validation run source versions
    # -----------------------------------------------------------------------

    op.create_table(
        "validation_run_source_versions",
        sa.Column("validation_run_id", sa.UUID(), nullable=False),
        sa.Column("institution_record_version_id", sa.UUID(), nullable=False),
        sa.Column("source_sync_run_id", sa.UUID(), nullable=True),
        sa.Column("source_code", sa.String(length=100), nullable=False),
        sa.Column(
            "captured_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["institution_record_version_id"],
            ["institution_record_versions.institution_record_version_id"],
        ),
        sa.ForeignKeyConstraint(
            ["source_sync_run_id"],
            ["source_sync_runs.source_sync_run_id"],
        ),
        sa.ForeignKeyConstraint(
            ["validation_run_id"],
            ["validation_runs.validation_run_id"],
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint(
            "validation_run_id",
            "institution_record_version_id",
        ),
    )

    op.create_index(
        "idx_validation_run_source_versions_source",
        "validation_run_source_versions",
        [
            "source_code",
            sa.literal_column("captured_at DESC"),
        ],
        unique=False,
    )

    # -----------------------------------------------------------------------
    # 13. Findings
    # -----------------------------------------------------------------------

    op.create_table(
        "findings",
        sa.Column(
            "finding_id",
            sa.UUID(),
            server_default=sa.text("gen_random_uuid()"),
            nullable=False,
        ),
        sa.Column("application_id", sa.UUID(), nullable=False),
        sa.Column("application_revision_id", sa.UUID(), nullable=False),
        sa.Column("validation_run_id", sa.UUID(), nullable=True),
        sa.Column("validation_result_id", sa.UUID(), nullable=True),
        sa.Column("category", finding_category_enum, nullable=False),
        sa.Column(
            "severity",
            finding_severity_enum,
            server_default=sa.text("'MEDIUM'"),
            nullable=False,
        ),
        sa.Column(
            "status",
            finding_status_enum,
            server_default=sa.text("'OPEN'"),
            nullable=False,
        ),
        sa.Column("title", sa.String(length=250), nullable=False),
        sa.Column("internal_reason", sa.Text(), nullable=False),
        sa.Column("recommended_action", sa.Text(), nullable=True),
        sa.Column(
            "is_internal_only",
            sa.Boolean(),
            server_default=sa.text("true"),
            nullable=False,
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["application_id"],
            ["applications.application_id"],
        ),
        sa.ForeignKeyConstraint(
            ["application_revision_id"],
            ["application_revisions.application_revision_id"],
        ),
        sa.ForeignKeyConstraint(
            ["validation_result_id"],
            ["validation_results.validation_result_id"],
        ),
        sa.ForeignKeyConstraint(
            ["validation_run_id"],
            ["validation_runs.validation_run_id"],
        ),
        sa.PrimaryKeyConstraint("finding_id"),
    )

    op.create_index(
        "idx_findings_app_status",
        "findings",
        ["application_id", "status", "severity"],
        unique=False,
    )

    # -----------------------------------------------------------------------
    # 14. Finding evidence
    # -----------------------------------------------------------------------

    op.create_table(
        "finding_evidence",
        sa.Column(
            "finding_evidence_id",
            sa.UUID(),
            server_default=sa.text("gen_random_uuid()"),
            nullable=False,
        ),
        sa.Column("finding_id", sa.UUID(), nullable=False),
        sa.Column("document_version_id", sa.UUID(), nullable=True),
        sa.Column("extracted_field_id", sa.UUID(), nullable=True),
        sa.Column("verification_attempt_id", sa.UUID(), nullable=True),
        sa.Column("validation_result_id", sa.UUID(), nullable=True),
        sa.Column("page_number", sa.Integer(), nullable=True),
        sa.Column("evidence_type", sa.String(length=80), nullable=False),
        sa.Column("evidence_reference", sa.Text(), nullable=True),
        sa.Column("evidence_summary", sa.Text(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.CheckConstraint(
            "num_nonnulls("
            "document_version_id, "
            "extracted_field_id, "
            "verification_attempt_id, "
            "validation_result_id"
            ") >= 1",
            name="chk_finding_evidence_target",
        ),
        sa.CheckConstraint(
            "page_number IS NULL OR page_number > 0",
            name="chk_finding_evidence_page",
        ),
        sa.ForeignKeyConstraint(
            ["document_version_id"],
            ["document_versions.document_version_id"],
        ),
        sa.ForeignKeyConstraint(
            ["extracted_field_id"],
            ["extracted_fields.extracted_field_id"],
        ),
        sa.ForeignKeyConstraint(
            ["finding_id"],
            ["findings.finding_id"],
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["validation_result_id"],
            ["validation_results.validation_result_id"],
        ),
        sa.ForeignKeyConstraint(
            ["verification_attempt_id"],
            ["verification_attempts.verification_attempt_id"],
        ),
        sa.PrimaryKeyConstraint("finding_evidence_id"),
    )


# ---------------------------------------------------------------------------
# DOWNGRADE
# ---------------------------------------------------------------------------


def downgrade() -> None:
    """Downgrade schema."""

    # Drop dependent tables and indexes in reverse dependency order.

    op.drop_table("finding_evidence")

    op.drop_index(
        "idx_findings_app_status",
        table_name="findings",
    )
    op.drop_table("findings")

    op.drop_index(
        "idx_validation_run_source_versions_source",
        table_name="validation_run_source_versions",
    )
    op.drop_table("validation_run_source_versions")

    op.drop_table("validation_run_rule_versions")
    op.drop_table("validation_results")

    op.drop_index(
        "idx_verification_doc_status",
        table_name="verification_attempts",
    )
    op.drop_table("verification_attempts")

    op.drop_table("validation_runs")
    op.drop_table("document_security_scans")
    op.drop_table("document_metadata_observations")
    op.drop_table("document_integrity_checks")
    op.drop_table("digital_signature_checks")

    op.drop_index(
        "idx_institution_record_versions_source_sync",
        table_name="institution_record_versions",
    )
    op.drop_table("institution_record_versions")

    op.drop_index(
        "idx_source_sync_runs_status_time",
        table_name="source_sync_runs",
    )
    op.drop_index(
        "idx_source_sync_runs_source_time",
        table_name="source_sync_runs",
    )
    op.drop_table("source_sync_runs")
    op.drop_table("verification_sources")

    # Drop only the six enum types introduced by this migration.
    # Existing enum types from previous migrations remain untouched.

    op.execute("DROP TYPE finding_status")
    op.execute("DROP TYPE finding_severity")
    op.execute("DROP TYPE finding_category")
    op.execute("DROP TYPE verification_status")
    op.execute("DROP TYPE verification_method")
    op.execute("DROP TYPE source_type")

"""Add SAC appeal records and separate SAC/Council Secretariat roles.

Revision ID: e135f7a8b9c0
Revises: d924e5f6a7b8
"""
from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = "e135f7a8b9c0"
down_revision: str | Sequence[str] | None = "d924e5f6a7b8"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.execute("ALTER TYPE team_role ADD VALUE IF NOT EXISTS 'SAC_SECRETARIAT'")
    op.execute("ALTER TYPE team_role ADD VALUE IF NOT EXISTS 'COUNCIL_SECRETARIAT'")

    op.drop_constraint("chk_role_code", "roles", type_="check")
    op.create_check_constraint(
        "chk_role_code",
        "roles",
        "role_code IN ('INSTITUTION_USER', 'INTAKE_OFFICER', 'SCRUTINY_OFFICER', "
        "'REGIONAL_OFFICER', 'EVC_COORDINATOR', 'EVC_MEMBER', 'COMMITTEE_SECRETARIAT', "
        "'SAC_SECRETARIAT', 'COUNCIL_SECRETARIAT', 'BUREAU_SUPERVISOR', "
        "'COMPETENT_AUTHORITY', 'REGULATORY_POLICY_PUBLISHER', 'AUDITOR', 'LEAD_AUDITOR', 'ADMIN')",
    )
    op.execute(sa.text("""
        INSERT INTO roles (role_code, role_name)
        VALUES
            ('SAC_SECRETARIAT', 'Standing Appellate Committee Secretariat'),
            ('COUNCIL_SECRETARIAT', 'Council Secretariat')
        ON CONFLICT (role_code) DO NOTHING
    """))

    op.create_table(
        "sac_appeals",
        sa.Column("sac_appeal_id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("executive_committee_decision_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("executive_committee_decisions.executive_committee_decision_id", ondelete="RESTRICT"), nullable=False),
        sa.Column("workflow_case_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("workflow_cases.workflow_case_id", ondelete="CASCADE"), nullable=False),
        sa.Column("application_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("applications.application_id", ondelete="CASCADE"), nullable=False),
        sa.Column("shc_proceeding_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("shc_proceedings.shc_proceeding_id", ondelete="SET NULL"), nullable=True),
        sa.Column("status", sa.String(36), nullable=False, server_default="FILED"),
        sa.Column("appeal_reference", sa.String(180), nullable=True),
        sa.Column("appeal_grounds", sa.Text(), nullable=False),
        sa.Column("supporting_material_reference", sa.Text(), nullable=False),
        sa.Column("filed_by", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.user_id"), nullable=False),
        sa.Column("filed_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("appeal_deadline_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("hearing_mode", sa.String(20), nullable=True),
        sa.Column("hearing_scheduled_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("hearing_details", sa.Text(), nullable=True),
        sa.Column("official_schedule_reference", sa.String(180), nullable=True),
        sa.Column("schedule_revision", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("regulation_bureau_observation_reference", sa.String(180), nullable=True),
        sa.Column("regulation_bureau_observations", sa.Text(), nullable=True),
        sa.Column("bureau_observations_recorded_by", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.user_id"), nullable=True),
        sa.Column("bureau_observations_recorded_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("representative_one_name", sa.String(160), nullable=True),
        sa.Column("representative_one_designation", sa.String(160), nullable=True),
        sa.Column("representative_one_id_reference", sa.String(500), nullable=True),
        sa.Column("representative_one_id_self_attested", sa.Boolean(), nullable=True),
        sa.Column("representative_two_name", sa.String(160), nullable=True),
        sa.Column("representative_two_designation", sa.String(160), nullable=True),
        sa.Column("representative_two_id_reference", sa.String(500), nullable=True),
        sa.Column("representative_two_id_self_attested", sa.Boolean(), nullable=True),
        sa.Column("hearing_summary", sa.Text(), nullable=True),
        sa.Column("hearing_recorded_by", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.user_id"), nullable=True),
        sa.Column("hearing_recorded_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("recommendation_code", sa.String(40), nullable=True),
        sa.Column("recommendation_text", sa.Text(), nullable=True),
        sa.Column("recommendation_reference", sa.String(180), nullable=True),
        sa.Column("recommendation_recorded_by", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.user_id"), nullable=True),
        sa.Column("recommendation_recorded_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("council_outcome_code", sa.String(48), nullable=True),
        sa.Column("council_decision_reference", sa.String(180), nullable=True),
        sa.Column("council_decision_text", sa.Text(), nullable=True),
        sa.Column("council_decision_uploaded_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("council_decision_recorded_by", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.user_id"), nullable=True),
        sa.Column("council_decision_recorded_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.UniqueConstraint("executive_committee_decision_id", name="uq_sac_appeals_ec_decision"),
        sa.CheckConstraint("status IN ('FILED', 'SCHEDULED', 'HEARING_RECORDED', 'RECOMMENDATION_RECORDED', 'COUNCIL_DECISION_RECORDED')", name="chk_sac_appeals_status"),
        sa.CheckConstraint("hearing_mode IS NULL OR hearing_mode IN ('ONLINE', 'IN_PERSON')", name="chk_sac_appeals_hearing_mode"),
        sa.CheckConstraint("schedule_revision >= 0", name="chk_sac_appeals_schedule_revision"),
        sa.CheckConstraint("status <> 'SCHEDULED' OR (hearing_scheduled_at IS NOT NULL AND hearing_mode IS NOT NULL AND hearing_details IS NOT NULL AND schedule_revision > 0)", name="chk_sac_appeals_schedule"),
        sa.CheckConstraint("status NOT IN ('HEARING_RECORDED', 'RECOMMENDATION_RECORDED', 'COUNCIL_DECISION_RECORDED') OR (representative_one_name IS NOT NULL AND representative_one_designation IS NOT NULL AND representative_one_id_reference IS NOT NULL AND representative_one_id_self_attested IS TRUE AND representative_two_name IS NOT NULL AND representative_two_designation IS NOT NULL AND representative_two_id_reference IS NOT NULL AND representative_two_id_self_attested IS TRUE AND hearing_summary IS NOT NULL AND hearing_recorded_at IS NOT NULL AND hearing_recorded_by IS NOT NULL)", name="chk_sac_appeals_hearing_record"),
        sa.CheckConstraint("status NOT IN ('RECOMMENDATION_RECORDED', 'COUNCIL_DECISION_RECORDED') OR (recommendation_code IS NOT NULL AND recommendation_text IS NOT NULL AND recommendation_recorded_at IS NOT NULL AND recommendation_recorded_by IS NOT NULL)", name="chk_sac_appeals_recommendation"),
        sa.CheckConstraint("status <> 'COUNCIL_DECISION_RECORDED' OR (council_outcome_code IS NOT NULL AND council_decision_reference IS NOT NULL AND council_decision_text IS NOT NULL AND council_decision_uploaded_at IS NOT NULL AND council_decision_recorded_at IS NOT NULL AND council_decision_recorded_by IS NOT NULL)", name="chk_sac_appeals_council_decision"),
        sa.CheckConstraint("recommendation_code IS NULL OR recommendation_code IN ('RECOMMEND_TO_COUNCIL', 'NOT_RECOMMEND_TO_COUNCIL', 'FURTHER_REVIEW_REQUIRED')", name="chk_sac_appeals_recommendation_code"),
        sa.CheckConstraint("council_outcome_code IS NULL OR council_outcome_code IN ('UPHOLD_EXECUTIVE_COMMITTEE', 'SET_ASIDE_EXECUTIVE_COMMITTEE', 'MODIFY_EXECUTIVE_COMMITTEE', 'REMAND_FOR_RECONSIDERATION')", name="chk_sac_appeals_council_outcome"),
        sa.CheckConstraint("filed_at <= appeal_deadline_at", name="chk_sac_appeals_filed_within_deadline"),
    )
    op.create_index("idx_sac_appeals_status_hearing", "sac_appeals", ["status", "hearing_scheduled_at"])
    op.create_index("idx_sac_appeals_institution_filed", "sac_appeals", ["application_id", "filed_at"])


def downgrade() -> None:
    op.drop_index("idx_sac_appeals_institution_filed", table_name="sac_appeals")
    op.drop_index("idx_sac_appeals_status_hearing", table_name="sac_appeals")
    op.drop_table("sac_appeals")
    op.execute(sa.text("DELETE FROM roles WHERE role_code IN ('SAC_SECRETARIAT', 'COUNCIL_SECRETARIAT')"))
    op.drop_constraint("chk_role_code", "roles", type_="check")
    op.create_check_constraint(
        "chk_role_code",
        "roles",
        "role_code IN ('INSTITUTION_USER', 'INTAKE_OFFICER', 'SCRUTINY_OFFICER', "
        "'REGIONAL_OFFICER', 'EVC_COORDINATOR', 'EVC_MEMBER', 'COMMITTEE_SECRETARIAT', "
        "'BUREAU_SUPERVISOR', 'COMPETENT_AUTHORITY', 'REGULATORY_POLICY_PUBLISHER', "
        "'AUDITOR', 'LEAD_AUDITOR', 'ADMIN')",
    )
    # PostgreSQL enum additions are intentionally retained on downgrade. They are
    # harmless unused values and removing enum labels is not a supported ALTER TYPE operation.

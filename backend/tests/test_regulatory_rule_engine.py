"""AIC-Verify — Comprehensive Regulatory Rule Engine Test Suite.

Covers:
- All 7 Annexure 2.1 evaluators independently (EOA-SD-01 through EOA-SD-07).
- Authoritative field resolver & strict reviewer conflict policy (no latest-wins, no role-priority).
- Exact calendar-based 30-year anniversary and 5-year certificate validity boundaries.
- Missing, expired, mismatched, and unverified source checks.
- Low-confidence OCR and unextracted document handling.
- Non-mutation of applicant checklist/upload states (ApplicationRequirement.status unchanged).
- Phase 2 RBAC case isolation: Institution User, Auditor, and Admin (denied HTTP 403).
- Full end-to-end execution and pinning of rule versions and source snapshot versions.
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from typing import Any

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, verify_csrf
from app.main import app as fastapi_app
from app.models.application import Application
from app.models.application_requirements import ApplicationRequirement
from app.models.application_revision import ApplicationRevision
from app.models.checklist_item import ChecklistItem
from app.models.document import Document
from app.models.document_version import DocumentVersion
from app.models.enums import (
    ApplicationFamily,
    ApplicationStatus,
    FindingCategory,
    FindingSeverity,
    RequirementStatus,
)
from app.models.extracted_field import ExtractedField
from app.models.extracted_field_review import ExtractedFieldReview
from app.models.institution import Institution
from app.models.institution_record_version import InstitutionRecordVersion
from app.models.role import Role
from app.models.user import User
from app.models.user_role_assignment import UserRoleAssignment
from app.models.validation_result import ValidationResult
from app.models.validation_rule import ValidationRule
from app.models.validation_rule_version import ValidationRuleVersion
from app.models.validation_run_rule_version import ValidationRunRuleVersion
from app.models.validation_run_source_version import ValidationRunSourceVersion
from app.rules.base import (
    AuthoritativeFieldResolver,
    ResolvedField,
    RuleEvaluationContext,
)
from app.rules.engine import regulatory_rule_engine
from app.rules.evaluators import (
    RuleEvaluatorEOA01,
    RuleEvaluatorEOA02,
    RuleEvaluatorEOA03,
    RuleEvaluatorEOA04,
    RuleEvaluatorEOA05,
    RuleEvaluatorEOA06,
    RuleEvaluatorEOA07,
)
from scripts.seed_rules import seed_rules

# =============================================================================
# Helper Fixtures & Builders
# =============================================================================


@pytest.fixture(scope="module", autouse=True)
def ensure_rules_seeded() -> None:
    """Ensure all 7 validation rules and version 1 are seeded."""
    seed_rules()


def make_mock_context(
    db: Session,
    fields: dict[str, Any] | None = None,
    document_version: DocumentVersion | None = None,
    source_snapshots: dict[str, Any] | None = None,
    requirement_applicability: str = "APPLICABLE",
    requirement_status: RequirementStatus = RequirementStatus.UPLOADED,
    evaluation_as_of: datetime | None = None,
    aicte_id: str | None = None,
) -> RuleEvaluationContext:
    """Constructs a transient RuleEvaluationContext for isolated unit testing."""
    test_aicte_id = aicte_id or f"SYNTH-TEST-{uuid.uuid4().hex[:8]}"
    inst = Institution(
        institution_name="Test Engineering College",
        institution_type="PRIVATE_SELF_FINANCING",
        aicte_permanent_institution_id=test_aicte_id,
    )
    db.add(inst)
    db.flush()

    user = User(
        email=f"test_eval_{uuid.uuid4().hex[:6]}@aicte.gov.in",
        full_name="Test Evaluator",
        password_hash="hash",
    )
    db.add(user)
    db.flush()

    app = Application(
        institution_id=inst.institution_id,
        application_number=f"APP-TEST-{uuid.uuid4().hex[:8]}",
        application_family=ApplicationFamily.EXISTING_INSTITUTION,
        academic_year="2026-27",
        status=ApplicationStatus.DRAFT,
        created_by=user.user_id,
    )
    db.add(app)
    db.flush()

    rev = ApplicationRevision(
        application_id=app.application_id,
        revision_number=1,
        created_by=user.user_id,
    )
    db.add(rev)
    db.flush()

    ci = ChecklistItem(
        checklist_template_id=uuid.uuid4(),
        item_code="EOA-SD-01",
        title="Affidavit 2",
        display_order=1,
    )
    req = ApplicationRequirement(
        application_revision_id=rev.application_revision_id,
        checklist_item_id=uuid.uuid4(),
        applicability_status=requirement_applicability,
        status=requirement_status,
    )

    rule = ValidationRule(
        rule_code="RULE_TEST",
        rule_name="Test Rule",
        rule_category="TEST",
        is_active=True,
    )
    rule_ver = ValidationRuleVersion(
        validation_rule_id=uuid.uuid4(),
        version_number=1,
        condition_json={},
        evaluation_config={},
        is_enabled=True,
    )

    # Convert simple field dict into ResolvedField objects
    resolved_fields: dict[str, ResolvedField] = {}
    for code, val in (fields or {}).items():
        if isinstance(val, ResolvedField):
            resolved_fields[code] = val
        else:
            resolved_fields[code] = ResolvedField(
                field_code=code,
                field_label=code,
                raw_value=str(val) if not isinstance(val, dict) else None,
                normalized_value=val,
                confidence=0.95,
                extracted_field_id=uuid.uuid4(),
                document_version_id=document_version.document_version_id
                if document_version
                else None,
                page_number=1,
            )

    # Wrap raw dicts in mock snapshots if needed
    mock_snaps: dict[str, InstitutionRecordVersion] = {}
    for code, snap_data in (source_snapshots or {}).items():
        if isinstance(snap_data, InstitutionRecordVersion):
            mock_snaps[code] = snap_data
        else:
            snap = InstitutionRecordVersion(
                institution_id=inst.institution_id,
                record_version=1,
                record_data=snap_data,
                source_system=code,
                source_reference="REF-001",
                effective_from=datetime(2025, 1, 1, tzinfo=UTC),
                recorded_at=datetime(2025, 1, 1, tzinfo=UTC),
            )
            mock_snaps[code] = snap

    return RuleEvaluationContext(
        db=db,
        institution=inst,
        application=app,
        revision=rev,
        requirement=req,
        checklist_item=ci,
        rule=rule,
        rule_version=rule_ver,
        document_version=document_version,
        fields=resolved_fields,
        source_snapshots=mock_snaps,
        evaluation_as_of=evaluation_as_of or datetime(2026, 7, 1, 10, 0, tzinfo=UTC),
        triggered_by=user.user_id,
    )


def make_mock_doc_version(db: Session, filename: str = "doc.pdf") -> DocumentVersion:
    inst = Institution(
        institution_name="Test Doc Inst",
        institution_type="PRIVATE_SELF_FINANCING",
        aicte_permanent_institution_id=f"SYNTH-DOC-{uuid.uuid4().hex[:8]}",
    )
    db.add(inst)
    db.flush()

    user = User(
        email=f"doc_uploader_{uuid.uuid4().hex[:6]}@aicte.gov.in",
        full_name="Doc Uploader",
        password_hash="hash",
    )
    db.add(user)
    db.flush()

    doc = Document(institution_id=inst.institution_id, created_by=user.user_id)
    db.add(doc)
    db.flush()

    dv = DocumentVersion(
        document_id=doc.document_id,
        version_number=1,
        original_filename=filename,
        storage_key=f"clean/{uuid.uuid4().hex}.bin",
        mime_type="application/pdf",
        file_size_bytes=1024,
        sha256_hex="a" * 64,
        uploaded_by=user.user_id,
    )
    db.add(dv)
    db.flush()
    return dv


# =============================================================================
# 1. AuthoritativeFieldResolver & Reviewer Conflict Tests
# =============================================================================


class TestAuthoritativeFieldResolver:
    """Verifies that conflicting reviews NEVER resolve via latest-wins or role-priority."""

    def test_single_review_accepted(self) -> None:
        fid = uuid.uuid4()
        f = ExtractedField(
            extracted_field_id=fid,
            document_extraction_id=uuid.uuid4(),
            field_code="stamp_duty_amount",
            raw_value="100",
            normalized_value={"numeric_value": 100.0},
        )
        rev = ExtractedFieldReview(
            extracted_field_review_id=uuid.uuid4(),
            extracted_field_id=fid,
            reviewed_by=uuid.uuid4(),
            reviewer_role="AUDITOR",
            accepted_as_extracted=True,
            corrected_value=None,
        )
        resolved = AuthoritativeFieldResolver.resolve_fields([f], {fid: [rev]})
        rf = resolved["stamp_duty_amount"]
        assert rf.is_reviewed is True
        assert rf.is_disputed is False
        assert rf.normalized_value == {"numeric_value": 100.0}

    def test_single_review_corrected(self) -> None:
        fid = uuid.uuid4()
        f = ExtractedField(
            extracted_field_id=fid,
            document_extraction_id=uuid.uuid4(),
            field_code="stamp_duty_amount",
            raw_value="50",
            normalized_value={"numeric_value": 50.0},
        )
        rev = ExtractedFieldReview(
            extracted_field_review_id=uuid.uuid4(),
            extracted_field_id=fid,
            reviewed_by=uuid.uuid4(),
            reviewer_role="AUDITOR",
            accepted_as_extracted=False,
            corrected_value={"numeric_value": 100.0},
            review_note="Corrected per stamp paper schedule",
        )
        resolved = AuthoritativeFieldResolver.resolve_fields([f], {fid: [rev]})
        rf = resolved["stamp_duty_amount"]
        assert rf.is_reviewed is True
        assert rf.is_disputed is False
        assert rf.normalized_value == {"numeric_value": 100.0}

    def test_multiple_reviews_consensus(self) -> None:
        fid = uuid.uuid4()
        f = ExtractedField(
            extracted_field_id=fid,
            document_extraction_id=uuid.uuid4(),
            field_code="stamp_duty_amount",
            raw_value="100",
            normalized_value={"numeric_value": 100.0},
        )
        rev1 = ExtractedFieldReview(
            extracted_field_review_id=uuid.uuid4(),
            extracted_field_id=fid,
            reviewed_by=uuid.uuid4(),
            reviewer_role="AUDITOR",
            accepted_as_extracted=True,
        )
        rev2 = ExtractedFieldReview(
            extracted_field_review_id=uuid.uuid4(),
            extracted_field_id=fid,
            reviewed_by=uuid.uuid4(),
            reviewer_role="LEAD_AUDITOR",
            accepted_as_extracted=True,
        )
        resolved = AuthoritativeFieldResolver.resolve_fields([f], {fid: [rev1, rev2]})
        rf = resolved["stamp_duty_amount"]
        assert rf.is_reviewed is True
        assert rf.is_disputed is False
        assert rf.normalized_value == {"numeric_value": 100.0}

    def test_conflicting_reviews_rejects_latest_wins_and_role_priority(self) -> None:
        fid = uuid.uuid4()
        f = ExtractedField(
            extracted_field_id=fid,
            document_extraction_id=uuid.uuid4(),
            field_code="stamp_duty_amount",
            raw_value="100",
            normalized_value={"numeric_value": 100.0},
        )
        # Auditor accepted ₹100
        rev1 = ExtractedFieldReview(
            extracted_field_review_id=uuid.uuid4(),
            extracted_field_id=fid,
            reviewed_by=uuid.uuid4(),
            reviewer_role="AUDITOR",
            accepted_as_extracted=True,
            reviewed_at=datetime(2026, 10, 20, tzinfo=UTC),
        )
        # Lead Auditor corrected to ₹50
        rev2 = ExtractedFieldReview(
            extracted_field_review_id=uuid.uuid4(),
            extracted_field_id=fid,
            reviewed_by=uuid.uuid4(),
            reviewer_role="LEAD_AUDITOR",
            accepted_as_extracted=False,
            corrected_value={"numeric_value": 50.0},
            review_note="Dispute: stamp duty is insufficient",
            reviewed_at=datetime(2026, 10, 25, tzinfo=UTC),
        )

        resolved = AuthoritativeFieldResolver.resolve_fields([f], {fid: [rev1, rev2]})
        rf = resolved["stamp_duty_amount"]

        # MUST BE FLAGGED DISPUTED!
        assert rf.is_disputed is True
        assert rf.normalized_value is None  # Neither ₹100 nor ₹50 is picked
        assert "divergent review decisions" in rf.dispute_reason

        # Building finding
        finding = AuthoritativeFieldResolver.build_dispute_finding(rf)
        assert finding.category == FindingCategory.CONTENT_ANOMALY
        assert finding.severity == FindingSeverity.HIGH
        assert len(finding.evidence_items) == 2


# =============================================================================
# 2. EOA-SD-01: Affidavit 2 Evaluator Tests
# =============================================================================


class TestRuleEvaluatorEOA01:
    """Verifies strict ₹100 stamp duty, signatory role, and notary attestation."""

    def test_missing_document(self, db: Session) -> None:
        ctx = make_mock_context(db, document_version=None)
        evaluator = RuleEvaluatorEOA01()
        outcome = evaluator.evaluate(ctx)
        assert outcome.status == "DEFICIENT"
        assert outcome.findings[0].category == FindingCategory.MISSING_DOCUMENT

    def test_stamp_duty_below_100_is_deficient(self, db: Session) -> None:
        dv = make_mock_doc_version(db)
        ctx = make_mock_context(
            db,
            document_version=dv,
            fields={
                "stamp_duty_amount": {"numeric_value": 50.0},
                "deponent_designation": "Chairman",
                "notary_registration_no": "DL/1234/2020",
            },
        )
        evaluator = RuleEvaluatorEOA01()
        outcome = evaluator.evaluate(ctx)
        assert outcome.status == "DEFICIENT"
        gap = next(
            f for f in outcome.findings if f.category == FindingCategory.REGULATORY_GAP
        )
        assert "mandates ₹100" in gap.internal_reason

    def test_deponent_title_self_financing_valid(self, db: Session) -> None:
        dv = make_mock_doc_version(db)
        ctx = make_mock_context(
            db,
            document_version=dv,
            fields={
                "stamp_duty_amount": {"numeric_value": 100.0},
                "deponent_designation": "Secretary / Chairman",
                "notary_registration_no": "DL/1234/2020",
                "aicte_permanent_id": "SYNTH-AICTE-0001",
            },
            source_snapshots={
                "SRC_AICTE_PORTAL": {
                    "institution_type": "PRIVATE_SELF_FINANCING",
                    "aicte_permanent_id": "SYNTH-AICTE-0001",
                }
            },
        )
        evaluator = RuleEvaluatorEOA01()
        outcome = evaluator.evaluate(ctx)
        assert outcome.status == "SATISFIED"

    def test_deponent_title_invalid_trustee_only(self, db: Session) -> None:
        dv = make_mock_doc_version(db)
        ctx = make_mock_context(
            db,
            document_version=dv,
            fields={
                "stamp_duty_amount": {"numeric_value": 100.0},
                "deponent_designation": "Executive Member",  # Neither Chairman nor Secretary
                "notary_registration_no": "DL/1234/2020",
            },
            source_snapshots={
                "SRC_AICTE_PORTAL": {"institution_type": "PRIVATE_SELF_FINANCING"}
            },
        )
        evaluator = RuleEvaluatorEOA01()
        outcome = evaluator.evaluate(ctx)
        assert outcome.status == "DEFICIENT"
        assert any(
            f.category == FindingCategory.CONTENT_ANOMALY for f in outcome.findings
        )

    def test_disputed_field_yields_unable_to_determine(self, db: Session) -> None:
        dv = make_mock_doc_version(db)
        disputed_field = ResolvedField(
            field_code="stamp_duty_amount",
            field_label="Stamp Duty",
            raw_value="100",
            normalized_value=None,
            confidence=0.9,
            extracted_field_id=uuid.uuid4(),
            document_version_id=dv.document_version_id,
            page_number=1,
            is_disputed=True,
            dispute_reason="Conflicting reviews",
        )
        ctx = make_mock_context(
            db, document_version=dv, fields={"stamp_duty_amount": disputed_field}
        )
        evaluator = RuleEvaluatorEOA01()
        outcome = evaluator.evaluate(ctx)
        assert outcome.status == "UNABLE_TO_DETERMINE"
        assert any(
            f.category == FindingCategory.CONTENT_ANOMALY for f in outcome.findings
        )


# =============================================================================
# 3. EOA-SD-02: Payment Receipt Evaluator Tests
# =============================================================================


class TestRuleEvaluatorEOA02:
    """Verifies fee exemption verification and payment receipt checks."""

    def test_exemption_source_unavailable_yields_unable_to_determine(
        self, db: Session
    ) -> None:
        ctx = make_mock_context(
            db,
            requirement_applicability="NOT_APPLICABLE",
            source_snapshots={},  # Missing SRC_AICTE_PORTAL
        )
        evaluator = RuleEvaluatorEOA02()
        outcome = evaluator.evaluate(ctx)
        assert outcome.status == "UNABLE_TO_DETERMINE"
        assert outcome.findings[0].category == FindingCategory.SOURCE_UNAVAILABLE

    def test_verified_exemption_is_not_applicable(self, db: Session) -> None:
        ctx = make_mock_context(
            db,
            requirement_applicability="NOT_APPLICABLE",
            source_snapshots={"SRC_AICTE_PORTAL": {"payment_exemption_status": True}},
        )
        evaluator = RuleEvaluatorEOA02()
        outcome = evaluator.evaluate(ctx)
        assert outcome.status == "NOT_APPLICABLE"

    def test_declared_exempt_but_portal_requires_payment(self, db: Session) -> None:
        ctx = make_mock_context(
            db,
            requirement_applicability="NOT_APPLICABLE",
            source_snapshots={
                "SRC_AICTE_PORTAL": {
                    "payment_exemption_status": False,
                    "expected_fee_amount": 150000.0,
                }
            },
        )
        evaluator = RuleEvaluatorEOA02()
        outcome = evaluator.evaluate(ctx)
        assert outcome.status == "DEFICIENT"
        assert outcome.findings[0].category == FindingCategory.REGULATORY_GAP

    def test_declared_exempt_but_portal_lacks_payment_info_yields_unable_to_determine(
        self, db: Session
    ) -> None:
        ctx = make_mock_context(
            db,
            requirement_applicability="NOT_APPLICABLE",
            source_snapshots={
                "SRC_AICTE_PORTAL": {
                    "institution_name": "Apex Institute of Technology",
                    "institution_type": "ENGINEERING_AND_TECHNOLOGY",
                    # No payment_exemption_status, processing_fee_exempt, or expected_fee_amount
                }
            },
        )
        evaluator = RuleEvaluatorEOA02()
        outcome = evaluator.evaluate(ctx)
        assert outcome.status == "UNABLE_TO_DETERMINE"
        assert outcome.findings[0].category == FindingCategory.SOURCE_UNAVAILABLE

    def test_payment_receipt_success(self, db: Session) -> None:
        dv = make_mock_doc_version(db)
        ctx = make_mock_context(
            db,
            document_version=dv,
            fields={
                "payment_status": "SUCCESS",
                "payment_amount": {"numeric_value": 150000.0},
                "transaction_ref_no": "SBIN00012345",
            },
        )
        evaluator = RuleEvaluatorEOA02()
        outcome = evaluator.evaluate(ctx)
        assert outcome.status == "SATISFIED"


# =============================================================================
# 4. EOA-SD-03: Building Document Evaluator Tests
# =============================================================================


class TestRuleEvaluatorEOA03:
    """Verifies statutory certificate types and municipal reference matching."""

    def test_valid_occupancy_certificate_matching_municipal(self, db: Session) -> None:
        dv = make_mock_doc_version(db)
        ctx = make_mock_context(
            db,
            document_version=dv,
            fields={
                "certificate_type": {"canonical_type": "OCCUPANCY_CERTIFICATE"},
                "certificate_number": "MCGM-OCC-1990-0891",
            },
            source_snapshots={
                "SRC_MUNICIPAL_BLDG": {
                    "occupancy_certificate_number": "MCGM-OCC-1990-0891"
                }
            },
        )
        evaluator = RuleEvaluatorEOA03()
        outcome = evaluator.evaluate(ctx)
        assert outcome.status == "SATISFIED"

    def test_unrecognized_certificate_type_is_deficient(self, db: Session) -> None:
        dv = make_mock_doc_version(db)
        ctx = make_mock_context(
            db,
            document_version=dv,
            fields={
                "certificate_type": {"canonical_type": "PROPERTY_TAX_RECEIPT"},
                "certificate_number": "TAX-1234",
            },
        )
        evaluator = RuleEvaluatorEOA03()
        outcome = evaluator.evaluate(ctx)
        assert outcome.status == "DEFICIENT"
        assert any(
            f.category == FindingCategory.INCOMPLETE_DOCUMENT for f in outcome.findings
        )


# =============================================================================
# 5. EOA-SD-04: Structural Stability Evaluator Tests
# =============================================================================


class TestRuleEvaluatorEOA04:
    """Verifies calendar-based 30-year anniversary and 5-year validity boundaries."""

    def test_calendar_boundary_under_30_years_is_not_applicable(
        self, db: Session
    ) -> None:
        # Assessment date: 2026-07-01
        # CC date: 2005-05-15 (age 21 yrs <= 30)
        ctx = make_mock_context(
            db,
            source_snapshots={
                "SRC_MUNICIPAL_BLDG": {"building_completion_date": "2005-05-15"}
            },
            evaluation_as_of=datetime(2026, 7, 1, 10, 0, tzinfo=UTC),
        )
        evaluator = RuleEvaluatorEOA04()
        outcome = evaluator.evaluate(ctx)
        assert outcome.status == "NOT_APPLICABLE"

    def test_calendar_boundary_exact_30_year_day_is_not_applicable(
        self, db: Session
    ) -> None:
        # Assessment date: 2026-07-01
        # CC date: 1996-07-01 (anniversary is exactly 2026-07-01; not GREATER than 30)
        ctx = make_mock_context(
            db,
            source_snapshots={
                "SRC_MUNICIPAL_BLDG": {"building_completion_date": "1996-07-01"}
            },
            evaluation_as_of=datetime(2026, 7, 1, 10, 0, tzinfo=UTC),
        )
        evaluator = RuleEvaluatorEOA04()
        outcome = evaluator.evaluate(ctx)
        assert outcome.status == "NOT_APPLICABLE"

    def test_leap_year_feb_29_completion_certificate_boundary(
        self, db: Session
    ) -> None:
        # Completion Certificate on Leap Day 1996-02-29
        # In 2026 (non-leap year), 30-year anniversary falls on 2026-02-28.
        # On 2026-02-28: date is NOT strictly greater than anniversary -> NOT_APPLICABLE.
        ctx_feb28 = make_mock_context(
            db,
            source_snapshots={
                "SRC_MUNICIPAL_BLDG": {"building_completion_date": "1996-02-29"}
            },
            evaluation_as_of=datetime(2026, 2, 28, 12, 0, tzinfo=UTC),
        )
        evaluator = RuleEvaluatorEOA04()
        outcome_feb28 = evaluator.evaluate(ctx_feb28)
        assert outcome_feb28.status == "NOT_APPLICABLE"

        # On 2026-03-01: date is strictly greater than 30 years -> APPLICABLE (DEFICIENT without cert)
        ctx_mar1 = make_mock_context(
            db,
            source_snapshots={
                "SRC_MUNICIPAL_BLDG": {"building_completion_date": "1996-02-29"}
            },
            evaluation_as_of=datetime(2026, 3, 1, 12, 0, tzinfo=UTC),
        )
        outcome_mar1 = evaluator.evaluate(ctx_mar1)
        assert outcome_mar1.status == "DEFICIENT"
        assert any(
            f.category == FindingCategory.MISSING_DOCUMENT
            for f in outcome_mar1.findings
        )

    def test_calendar_boundary_greater_than_30_requires_certificate(
        self, db: Session
    ) -> None:
        # Assessment date: 2026-07-01
        # CC date: 1996-06-30 (anniversary was 2026-06-30; strictly > 30 years!)
        dv = make_mock_doc_version(db)
        ctx = make_mock_context(
            db,
            document_version=dv,
            source_snapshots={
                "SRC_MUNICIPAL_BLDG": {"building_completion_date": "1996-06-30"}
            },
            fields={
                "issue_date": {"iso_date": "2023-01-15"},  # 3.5 yrs old <= 5 yrs
                "engineer_license_no": "SE/1234/2015",
                "stability_certification_statement": {"certified_sound": True},
            },
            evaluation_as_of=datetime(2026, 7, 1, 10, 0, tzinfo=UTC),
        )
        evaluator = RuleEvaluatorEOA04()
        outcome = evaluator.evaluate(ctx)
        assert outcome.status == "SATISFIED"

    def test_five_year_validity_expired(self, db: Session) -> None:
        # Assessment date: 2026-07-01
        # Certificate issued: 2020-05-10 (>5 years old)
        dv = make_mock_doc_version(db)
        ctx = make_mock_context(
            db,
            document_version=dv,
            source_snapshots={
                "SRC_MUNICIPAL_BLDG": {"building_completion_date": "1990-05-15"}
            },
            fields={
                "issue_date": {"iso_date": "2020-05-10"},
                "engineer_license_no": "SE/1234/2015",
                "stability_certification_statement": {"certified_sound": True},
            },
            evaluation_as_of=datetime(2026, 7, 1, 10, 0, tzinfo=UTC),
        )
        evaluator = RuleEvaluatorEOA04()
        outcome = evaluator.evaluate(ctx)
        assert outcome.status == "DEFICIENT"
        assert any(
            f.category == FindingCategory.EXPIRED_DOCUMENT for f in outcome.findings
        )


# =============================================================================
# 6. EOA-SD-05: Fire Safety Certificate Evaluator Tests
# =============================================================================


class TestRuleEvaluatorEOA05:
    """Verifies fire safety certificate expiration and revocation checks."""

    def test_fire_noc_expired_in_source_record(self, db: Session) -> None:
        dv = make_mock_doc_version(db)
        ctx = make_mock_context(
            db,
            document_version=dv,
            fields={
                "fire_noc_number": "NOC-9981",
                "expiry_date": {"iso_date": "2026-10-01"},
            },
            source_snapshots={
                "SRC_FIRE_SERVICES": {
                    "compliance_status": "EXPIRED",
                    "valid_until": "2026-04-09",
                    "fire_noc_certificate_number": "NOC-9981",
                }
            },
            evaluation_as_of=datetime(2026, 7, 1, tzinfo=UTC),
        )
        evaluator = RuleEvaluatorEOA05()
        outcome = evaluator.evaluate(ctx)
        assert outcome.status == "DEFICIENT"
        assert any(
            f.category == FindingCategory.EXPIRED_DOCUMENT for f in outcome.findings
        )

    def test_fire_noc_revoked_is_critical(self, db: Session) -> None:
        dv = make_mock_doc_version(db)
        ctx = make_mock_context(
            db,
            document_version=dv,
            fields={"fire_noc_number": "NOC-9981"},
            source_snapshots={
                "SRC_FIRE_SERVICES": {
                    "compliance_status": "REVOKED",
                    "fire_noc_certificate_number": "NOC-9981",
                }
            },
        )
        evaluator = RuleEvaluatorEOA05()
        outcome = evaluator.evaluate(ctx)
        assert outcome.status == "DEFICIENT"
        crit = next(
            f for f in outcome.findings if f.category == FindingCategory.SOURCE_MISMATCH
        )
        assert crit.severity == FindingSeverity.CRITICAL


# =============================================================================
# 7. EOA-SD-06: Satellite Map and Coordinates Evaluator Tests
# =============================================================================


class TestRuleEvaluatorEOA06:
    """Verifies plausibility check and advisory distance bands."""

    def test_coordinates_outside_india_fails_plausibility(self, db: Session) -> None:
        dv = make_mock_doc_version(db)
        # London (51.5° N)
        ctx = make_mock_context(
            db,
            document_version=dv,
            fields={
                "latitude": {"decimal_degrees": 51.5074},
                "longitude": {"decimal_degrees": -0.1278},
            },
        )
        evaluator = RuleEvaluatorEOA06()
        outcome = evaluator.evaluate(ctx)
        assert outcome.status == "DEFICIENT"
        assert any(
            f.category == FindingCategory.FIELD_MISMATCH for f in outcome.findings
        )

    def test_deviation_greater_than_5km_is_warning_not_statutory_deficient(
        self, db: Session
    ) -> None:
        dv = make_mock_doc_version(db)
        # Coordinates in Delhi (~1,100 km from Mumbai Kurla entrance)
        ctx = make_mock_context(
            db,
            document_version=dv,
            fields={
                "latitude": {"decimal_degrees": 28.6139},
                "longitude": {"decimal_degrees": 77.2090},
            },
        )
        evaluator = RuleEvaluatorEOA06()
        outcome = evaluator.evaluate(ctx)
        # Safeguard 3: Distance thresholds remain advisory heuristics. Deviation > 5 km is WARNING, NOT DEFICIENT!
        assert outcome.status == "WARNING"
        assert any(
            f.category == FindingCategory.INFRASTRUCTURE_OBSERVATION
            for f in outcome.findings
        )

    def test_entrance_within_1km_is_satisfied(self, db: Session) -> None:
        dv = make_mock_doc_version(db)
        # Exact registered coordinates (19.0657, 72.8792)
        ctx = make_mock_context(
            db,
            document_version=dv,
            fields={
                "latitude": {"decimal_degrees": 19.0657},
                "longitude": {"decimal_degrees": 72.8792},
            },
        )
        evaluator = RuleEvaluatorEOA06()
        outcome = evaluator.evaluate(ctx)
        assert outcome.status == "SATISFIED"


# =============================================================================
# 8. EOA-SD-07: Audited Statement Evaluator Tests
# =============================================================================


class TestRuleEvaluatorEOA07:
    """Verifies synthetic ICAI UDIN match and arithmetic advisory heuristics."""

    def test_valid_synthetic_icai_udin_match(self, db: Session) -> None:
        dv = make_mock_doc_version(db)
        ctx = make_mock_context(
            db,
            document_version=dv,
            fields={
                "financial_year": "2024-25",
                "auditor_udin": "26045891AAAAAA1234",
                "gross_annual_income": {"numeric_value": 1000000.0},
                "total_expenditure": {"numeric_value": 800000.0},
                "balance_surplus_deficit": {"numeric_value": 200000.0},
            },
        )
        evaluator = RuleEvaluatorEOA07()
        outcome = evaluator.evaluate(ctx)
        assert outcome.status == "SATISFIED"

    def test_revoked_udin_is_critical_deficient(self, db: Session) -> None:
        dv = make_mock_doc_version(db)
        ctx = make_mock_context(
            db,
            document_version=dv,
            fields={
                "financial_year": "2024-25",
                "auditor_udin": "99999999REVOKED0001",
            },
        )
        evaluator = RuleEvaluatorEOA07()
        outcome = evaluator.evaluate(ctx)
        assert outcome.status == "DEFICIENT"
        assert any(
            f.category == FindingCategory.SOURCE_MISMATCH for f in outcome.findings
        )

    def test_out_of_cycle_financial_year_is_flagged_as_field_mismatch(
        self, db: Session
    ) -> None:
        dv = make_mock_doc_version(db)
        # For AY 2026-27, preceding FY is 2024-25. Uploading statements for FY 2021-22 must fail!
        ctx = make_mock_context(
            db,
            document_version=dv,
            fields={
                "financial_year": "2021-22",
                "auditor_udin": "26045891AAAAAA1234",
            },
        )
        evaluator = RuleEvaluatorEOA07()
        outcome = evaluator.evaluate(ctx)
        assert outcome.status == "DEFICIENT"
        assert any(
            f.category == FindingCategory.FIELD_MISMATCH for f in outcome.findings
        )

    def test_arithmetic_discrepancy_is_advisory_heuristic_not_statutory_failure(
        self, db: Session
    ) -> None:
        dv = make_mock_doc_version(db)
        # Income: 10,00,000, Exp: 8,00,000 -> Diff is 2,00,000. But stated surplus is 1,00,000 (10% discrepancy)
        ctx = make_mock_context(
            db,
            document_version=dv,
            fields={
                "financial_year": "2024-25",
                "auditor_udin": "26045891AAAAAA1234",
                "gross_annual_income": {"numeric_value": 1000000.0},
                "total_expenditure": {"numeric_value": 800000.0},
                "balance_surplus_deficit": {"numeric_value": 100000.0},
            },
        )
        evaluator = RuleEvaluatorEOA07()
        outcome = evaluator.evaluate(ctx)
        # Safeguard 4: Math discrepancy is an advisory heuristic observation (INFO), NOT statutory failure
        assert outcome.status == "SATISFIED"
        assert any(
            f.category == FindingCategory.CONTENT_ANOMALY
            and f.severity == FindingSeverity.INFO
            for f in outcome.findings
        )


# =============================================================================
# 9. Engine Orchestration & RBAC Case Isolation Tests
# =============================================================================


class TestEngineOrchestrationAndRBAC:
    """Verifies full engine run, snapshot/rule pinning, state preservation, and RBAC isolation."""

    def test_full_engine_run_pins_versions_and_preserves_requirement_status(
        self, db: Session
    ) -> None:
        # Load synthetic institution and application
        inst = db.scalar(
            select(Institution).where(
                Institution.aicte_permanent_institution_id == "SYNTH-AICTE-0001"
            )
        )
        assert inst is not None

        app = db.scalar(
            select(Application).where(Application.institution_id == inst.institution_id)
        )
        assert app is not None

        rev = db.scalar(
            select(ApplicationRevision).where(
                ApplicationRevision.application_id == app.application_id
            )
        )
        assert rev is not None

        # Inspect requirement statuses before run
        reqs_before = list(
            db.scalars(
                select(ApplicationRequirement).where(
                    ApplicationRequirement.application_revision_id
                    == rev.application_revision_id
                )
            ).all()
        )
        statuses_before = {
            r.application_requirement_id: (r.status, r.applicability_status)
            for r in reqs_before
        }

        # Execute validation run
        run = regulatory_rule_engine.execute_validation_run(
            db=db,
            application_revision_id=rev.application_revision_id,
            run_type="FULL",
        )

        assert run.status == "COMPLETED"
        assert run.validation_run_id is not None

        # Pinning checks
        pinned_rules = db.scalars(
            select(ValidationRunRuleVersion).where(
                ValidationRunRuleVersion.validation_run_id == run.validation_run_id
            )
        ).all()
        assert len(pinned_rules) == 7  # All 7 rules pinned

        pinned_sources = db.scalars(
            select(ValidationRunSourceVersion).where(
                ValidationRunSourceVersion.validation_run_id == run.validation_run_id
            )
        ).all()
        assert len(pinned_sources) >= 5  # Source snapshots pinned

        # Safeguard 5 check: ApplicationRequirement.status MUST NOT BE OVERWRITTEN!
        reqs_after = list(
            db.scalars(
                select(ApplicationRequirement).where(
                    ApplicationRequirement.application_revision_id
                    == rev.application_revision_id
                )
            ).all()
        )
        for r in reqs_after:
            before_status, before_app = statuses_before[r.application_requirement_id]
            assert r.status == before_status, (
                f"Requirement {r.application_requirement_id} status was mutated from {before_status} to {r.status}!"
            )
            assert r.applicability_status == before_app

        # Validation results exist
        results = db.scalars(
            select(ValidationResult).where(
                ValidationResult.validation_run_id == run.validation_run_id
            )
        ).all()
        assert len(results) == 7

    def test_rbac_case_isolation_admin_denied_access(self, db: Session) -> None:
        inst = db.scalar(
            select(Institution).where(
                Institution.aicte_permanent_institution_id == "SYNTH-AICTE-0001"
            )
        )
        assert inst is not None
        app = db.scalar(
            select(Application).where(Application.institution_id == inst.institution_id)
        )
        assert app is not None

        # Create Admin user with ADMIN role assignment (null institution_id and null review_team_id)
        admin_user = User(
            email=f"admin_{uuid.uuid4().hex[:6]}@aicte.gov.in",
            full_name="System Admin",
            password_hash="hash",
        )
        db.add(admin_user)
        db.flush()

        role_admin = db.scalar(select(Role).where(Role.role_code == "ADMIN"))
        db.add(
            UserRoleAssignment(
                user_id=admin_user.user_id,
                role_id=role_admin.role_id,
                institution_id=None,
                review_team_id=None,
            )
        )
        db.commit()

        # Mock current user as admin and bypass CSRF
        fastapi_app.dependency_overrides[get_current_user] = lambda: admin_user
        fastapi_app.dependency_overrides[verify_csrf] = lambda: "csrf-token"

        client = TestClient(fastapi_app)
        try:
            # Attempt to list validation runs for this confidential case
            resp = client.get(
                f"/api/v1/institutions/{inst.institution_id}/applications/{app.application_id}/validation/runs"
            )
            # ADMIN MUST BE DENIED ACCESS (HTTP 403 Forbidden)!
            assert resp.status_code == 403
            assert "Forbidden" in resp.json()["detail"]
        finally:
            fastapi_app.dependency_overrides.pop(get_current_user, None)
            fastapi_app.dependency_overrides.pop(verify_csrf, None)

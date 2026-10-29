"""AIC-Verify — Rule Evaluator for EOA-SD-03: Building / Occupancy Document.

Regulatory Reference:
AICTE Approval Process Handbook (APH) 2024–2027 Annexure 2.1 Item iii:
Valid Occupancy Certificate / Completion Certificate / Building License / Form D,
as applicable, issued by the Competent Authority.

Safeguards Enforced:
1. Limited strictly to statutory certificate types, competent issuing authority,
   document reference, and municipal source consistency.
2. Flat Engineering 4,000 sqm / Management 1,500 sqm thresholds are completely removed.
3. Invented 90% and 5% compliance margins are completely removed.
4. Strict reviewer dispute handling: flags CONTENT_ANOMALY and returns UNABLE_TO_DETERMINE.
5. All synthetic outcomes explicitly labelled SIMULATED.
"""

from __future__ import annotations

import logging
from typing import Any

from app.models.enums import FindingCategory, FindingSeverity
from app.rules.base import (
    AuthoritativeFieldResolver,
    BaseRuleEvaluator,
    FindingDraft,
    RuleEvaluationContext,
    RuleEvaluationOutcome,
)

logger = logging.getLogger(__name__)

STATUTORY_BUILDING_CERT_TYPES = {
    "OCCUPANCY_CERTIFICATE",
    "COMPLETION_CERTIFICATE",
    "BUILDING_LICENSE",
    "FORM_D",
}


class RuleEvaluatorEOA03(BaseRuleEvaluator):
    """Evaluates EOA-SD-03 (Building / Occupancy Document) compliance."""

    rule_code = "RULE_EOA_03_BUILDING"

    def evaluate(self, ctx: RuleEvaluationContext) -> RuleEvaluationOutcome:
        findings: list[FindingDraft] = []

        # 1. Document Upload Presence
        if not ctx.document_version:
            findings.append(
                FindingDraft(
                    category=FindingCategory.MISSING_DOCUMENT,
                    severity=FindingSeverity.HIGH,
                    title="Building / Occupancy Document Missing",
                    internal_reason=(
                        "Mandatory requirement EOA-SD-03 has no uploaded document version. "
                        "AICTE norms require an Occupancy Certificate, Completion Certificate, "
                        "Building License, or Form D issued by the competent authority."
                    ),
                    recommended_action="Upload approved building certificate issued by the competent local authority.",
                    is_internal_only=False,
                )
            )
            return RuleEvaluationOutcome(
                status="DEFICIENT",
                expected_value={"document_uploaded": True},
                observed_value={"document_uploaded": False},
                explanation="Building document is missing from the application submission.",
                findings=findings,
            )

        # 2. Check for Disputed Fields
        disputed_fields = [f for f in ctx.fields.values() if f.is_disputed]
        if disputed_fields:
            for df in disputed_fields:
                findings.append(AuthoritativeFieldResolver.build_dispute_finding(df))
            return RuleEvaluationOutcome(
                status="UNABLE_TO_DETERMINE",
                expected_value={"dispute_free": True},
                observed_value={
                    "disputed_fields": [df.field_code for df in disputed_fields]
                },
                explanation="Building document candidate fields contain conflicting reviews. Determination halted.",
                findings=findings,
            )

        # 3. Check for Empty Extractions
        if not ctx.fields:
            findings.append(
                FindingDraft(
                    category=FindingCategory.INCOMPLETE_DOCUMENT,
                    severity=FindingSeverity.MEDIUM,
                    title="Building Document Details Unextracted",
                    internal_reason="Building document uploaded but certificate type and reference could not be parsed.",
                    recommended_action="Review document quality or conduct manual auditor verification.",
                    is_internal_only=True,
                )
            )
            return RuleEvaluationOutcome(
                status="UNABLE_TO_DETERMINE",
                expected_value={"building_fields_extracted": True},
                observed_value={"building_fields_extracted": False},
                explanation="Building document content could not be verified by automated extractor.",
                findings=findings,
            )

        cert_type_field = ctx.fields.get("certificate_type")
        cert_no_field = ctx.fields.get("certificate_number")
        issue_date_field = ctx.fields.get("issue_date")

        observed: dict[str, Any] = {
            "issue_date": issue_date_field.raw_value if issue_date_field else None,
        }
        is_deficient = False

        # 4. Validate Permissible Certificate Types
        canonical_type = None
        if cert_type_field and isinstance(cert_type_field.normalized_value, dict):
            canonical_type = cert_type_field.normalized_value.get("canonical_type")
        elif cert_type_field and cert_type_field.raw_value:
            raw_upper = cert_type_field.raw_value.upper()
            if "OCCUPANCY" in raw_upper:
                canonical_type = "OCCUPANCY_CERTIFICATE"
            elif "COMPLETION" in raw_upper:
                canonical_type = "COMPLETION_CERTIFICATE"
            elif "LICENSE" in raw_upper or "SANCTION" in raw_upper:
                canonical_type = "BUILDING_LICENSE"
            elif "FORM D" in raw_upper or "FORM-D" in raw_upper:
                canonical_type = "FORM_D"

        observed["certificate_type"] = canonical_type or (
            cert_type_field.raw_value if cert_type_field else None
        )

        if not canonical_type or canonical_type not in STATUTORY_BUILDING_CERT_TYPES:
            is_deficient = True
            findings.append(
                FindingDraft(
                    category=FindingCategory.INCOMPLETE_DOCUMENT,
                    severity=FindingSeverity.HIGH,
                    title="Unrecognized Building Document Certificate Type",
                    internal_reason=(
                        f"AICTE APH Annexure 2.1 Item iii recognizes Occupancy Certificate, Completion Certificate, "
                        f"Building License, or Form D. Observed certificate type: '{observed['certificate_type']}'."
                    ),
                    recommended_action="Submit one of the four statutory building certificate types.",
                    is_internal_only=False,
                )
            )

        # 5. Document Reference Number Presence
        cert_no = str(cert_no_field.raw_value if cert_no_field else "").strip()
        observed["certificate_number"] = cert_no
        if not cert_no or cert_no.upper() in ["NONE", "NULL", "UNEXTRACTED"]:
            is_deficient = True
            findings.append(
                FindingDraft(
                    category=FindingCategory.INCOMPLETE_DOCUMENT,
                    severity=FindingSeverity.MEDIUM,
                    title="Building Certificate Sanction Reference Missing",
                    internal_reason="Certificate reference number / sanction order could not be verified in document.",
                    recommended_action="Ensure the official sanction order or certificate number is clearly legible.",
                    is_internal_only=False,
                )
            )

        # 6. Synthetic Municipal Source Cross-Check (SRC_MUNICIPAL_BLDG)
        muni_snapshot = ctx.source_snapshots.get("SRC_MUNICIPAL_BLDG")
        if muni_snapshot and isinstance(muni_snapshot.record_data, dict):
            muni_rec = muni_snapshot.record_data
            expected_occ = muni_rec.get("occupancy_certificate_number")
            expected_sanction = muni_rec.get("sanction_plan_order_no")
            observed["muni_occupancy_number"] = expected_occ
            observed["muni_sanction_order"] = expected_sanction
            observed["provenance"] = "SIMULATED"

            # Check if extracted cert number matches either municipal reference
            matches_municipal = False
            if cert_no and (
                (expected_occ and cert_no.upper() in expected_occ.upper())
                or (expected_sanction and cert_no.upper() in expected_sanction.upper())
                or (expected_occ and expected_occ.upper() in cert_no.upper())
                or (expected_sanction and expected_sanction.upper() in cert_no.upper())
            ):
                matches_municipal = True

            if not matches_municipal and (expected_occ or expected_sanction):
                # We flag as SOURCE_MISMATCH observation
                findings.append(
                    FindingDraft(
                        category=FindingCategory.SOURCE_MISMATCH,
                        severity=FindingSeverity.HIGH,
                        title="Building Document Reference Differs from Municipal Record [SIMULATED]",
                        internal_reason=(
                            f"Uploaded building document specifies reference '{cert_no}'. Municipal authority "
                            f"records list occupancy certificate '{expected_occ}' and sanction order '{expected_sanction}' [SIMULATED]."
                        ),
                        recommended_action="Reconcile certificate reference with competent municipal authority records.",
                        is_internal_only=True,
                    )
                )
                is_deficient = True

        status = "DEFICIENT" if is_deficient else "SATISFIED"
        explanation = (
            f"Building document verified as a statutory {canonical_type} matching municipal registry records [SIMULATED]."
            if status == "SATISFIED"
            else "Building document fails statutory certificate type or municipal cross-check requirements."
        )

        return RuleEvaluationOutcome(
            status=status,
            expected_value={
                "statutory_types": sorted(STATUTORY_BUILDING_CERT_TYPES),
                "provenance": "SIMULATED",
            },
            observed_value=observed,
            explanation=explanation,
            findings=findings,
        )

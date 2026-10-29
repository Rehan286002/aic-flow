"""AIC-Verify — Rule Evaluator for EOA-SD-02: Payment Receipt.

Regulatory Reference:
AICTE Approval Process Handbook (APH) 2024–2027 Annexure 2.1 Item ii:
Copy of AICTE Web-Portal payment receipt, if any.

Safeguards Enforced:
1. Do not infer fee exemption solely from applicant declaration.
2. Missing or unavailable authoritative source evidence results in UNABLE_TO_DETERMINE.
3. All synthetic outcomes explicitly labelled SIMULATED.
4. If applicable, uploaded receipt must indicate SUCCESS/PAID status.
5. Strict reviewer dispute handling: flags CONTENT_ANOMALY and returns UNABLE_TO_DETERMINE.
"""

from __future__ import annotations

import logging

from app.models.enums import FindingCategory, FindingSeverity
from app.rules.base import (
    AuthoritativeFieldResolver,
    BaseRuleEvaluator,
    FindingDraft,
    RuleEvaluationContext,
    RuleEvaluationOutcome,
)

logger = logging.getLogger(__name__)


class RuleEvaluatorEOA02(BaseRuleEvaluator):
    """Evaluates EOA-SD-02 (AICTE Web-Portal Payment Receipt) compliance."""

    rule_code = "RULE_EOA_02_PAYMENT"

    def evaluate(self, ctx: RuleEvaluationContext) -> RuleEvaluationOutcome:
        findings: list[FindingDraft] = []

        # 1. Inspect Applicant Self-Disclosure Declaration (payment_applicable)
        # Check applicant declaration from application_field_values or requirement status
        applicant_claims_exempt = False
        if ctx.requirement.applicability_status == "NOT_APPLICABLE":
            applicant_claims_exempt = True

        # Check raw declared field value if present
        for fv in ctx.revision.field_values if ctx.revision else []:
            if (
                fv.field_definition
                and fv.field_definition.field_code == "payment_applicable"
            ):
                v = fv.value_json
                if (
                    v is False
                    or (isinstance(v, str) and v.lower() in ("false", "no", "0"))
                    or isinstance(v, dict)
                    and (v.get("applicable") is False or v.get("exempt") is True)
                ):
                    applicant_claims_exempt = True

        # 2. Check Exemption Branch
        if applicant_claims_exempt:
            source_snapshot = ctx.source_snapshots.get("SRC_AICTE_PORTAL")
            if not source_snapshot or not isinstance(source_snapshot.record_data, dict):
                # Safeguard 4: Missing or unavailable authoritative source evidence must result in UNABLE_TO_DETERMINE
                findings.append(
                    FindingDraft(
                        category=FindingCategory.SOURCE_UNAVAILABLE,
                        severity=FindingSeverity.MEDIUM,
                        title="Authoritative AICTE Portal Record Unavailable for Fee Exemption Check [SIMULATED]",
                        internal_reason=(
                            "Applicant declared regulatory payment not applicable. However, authoritative "
                            "institutional master records from SRC_AICTE_PORTAL could not be accessed to verify "
                            "the exemption status. Under regulatory verification rules, fee exemption cannot be "
                            "accepted solely on self-declaration."
                        ),
                        recommended_action="Ensure SRC_AICTE_PORTAL is synchronized or conduct manual fee audit.",
                        is_internal_only=True,
                    )
                )
                return RuleEvaluationOutcome(
                    status="UNABLE_TO_DETERMINE",
                    expected_value={"verified_exemption_source_available": True},
                    observed_value={
                        "verified_exemption_source_available": False,
                        "applicant_claims_exempt": True,
                    },
                    explanation=(
                        "Applicant declared fee exemption, but authoritative AICTE master records are unavailable "
                        "to corroborate the exemption [SIMULATED]."
                    ),
                    findings=findings,
                )

            # Master record is available: verify legal exemption
            rec = source_snapshot.record_data

            # Distinguish AICTE application processing-fee exemption from tuition-fee-waiver (TFW) exemption.
            # TFW is a student fee concession scheme under APH, NOT an institution application processing fee exemption.
            # Only authoritative processing fee exemption fields apply here.
            is_explicitly_exempt = rec.get("processing_fee_exempt") is True or rec.get(
                "payment_exemption_status"
            ) in (True, "EXEMPT", "EXEMPTED")

            # Check for explicit fee requirement contradicting the applicant declaration
            expected_fee = rec.get("expected_fee_amount")
            has_explicit_fee_requirement = (
                (
                    rec.get("processing_fee_exempt") is False
                    or rec.get("payment_exemption_status")
                    in (False, "NOT_EXEMPT", "REQUIRED")
                )
                and (expected_fee is not None and float(expected_fee) > 0)
            ) or (rec.get("processing_fee_required") is True)

            if is_explicitly_exempt:
                return RuleEvaluationOutcome(
                    status="NOT_APPLICABLE",
                    expected_value={
                        "payment_required": False,
                        "provenance": "SIMULATED",
                    },
                    observed_value={
                        "applicant_declared_exempt": True,
                        "portal_verified_exempt": True,
                        "provenance": "SIMULATED",
                    },
                    explanation=(
                        "Institution legally verified as exempt from regulatory application processing payment per "
                        "AICTE master institutional portal records [SIMULATED]. Requirement EOA-SD-02 is NOT_APPLICABLE."
                    ),
                    findings=findings,
                )
            elif has_explicit_fee_requirement:
                # Discrepancy: applicant claims exempt but portal explicitly indicates payment required
                fee_display = (
                    f"₹{float(expected_fee):,.2f}"
                    if expected_fee
                    else "statutory amount"
                )
                findings.append(
                    FindingDraft(
                        category=FindingCategory.REGULATORY_GAP,
                        severity=FindingSeverity.HIGH,
                        title="Uncorroborated Fee Exemption Declaration [SIMULATED]",
                        internal_reason=(
                            f"Applicant declared regulatory payment not applicable, but authoritative AICTE master "
                            f"portal records explicitly mandate an application processing fee of {fee_display} [SIMULATED]."
                        ),
                        recommended_action="Submit verified web-portal payment receipt or clarify exemption basis.",
                        is_internal_only=False,
                    )
                )
                return RuleEvaluationOutcome(
                    status="DEFICIENT",
                    expected_value={
                        "payment_exemption_verified": True,
                        "provenance": "SIMULATED",
                    },
                    observed_value={
                        "applicant_declared_exempt": True,
                        "portal_verified_exempt": False,
                        "provenance": "SIMULATED",
                    },
                    explanation=(
                        "Applicant self-declared payment exemption, but official institutional records indicate "
                        "payment is required under Approval Process Handbook norms [SIMULATED]."
                    ),
                    findings=findings,
                )
            else:
                # Missing or null authoritative exemption/payment-requirement information
                # Do NOT invent a negative portal response!
                findings.append(
                    FindingDraft(
                        category=FindingCategory.SOURCE_UNAVAILABLE,
                        severity=FindingSeverity.MEDIUM,
                        title="Authoritative Fee Exemption Data Inconclusive in AICTE Portal [SIMULATED]",
                        internal_reason=(
                            "Applicant declared regulatory payment not applicable. While authoritative master records "
                            "from SRC_AICTE_PORTAL were accessed, the institutional record contains no explicit "
                            "processing-fee exemption status or fee mandate schedule. Under regulatory verification policy, "
                            "a fee requirement or exemption cannot be assumed or invented without authoritative confirmation."
                        ),
                        recommended_action="Review institutional approval category or conduct manual fee reconciliation.",
                        is_internal_only=True,
                    )
                )
                return RuleEvaluationOutcome(
                    status="UNABLE_TO_DETERMINE",
                    expected_value={
                        "authoritative_payment_status_specified": True,
                        "provenance": "SIMULATED",
                    },
                    observed_value={
                        "authoritative_payment_status_specified": False,
                        "applicant_claims_exempt": True,
                        "provenance": "SIMULATED",
                    },
                    explanation=(
                        "Applicant declared fee exemption, but authoritative AICTE portal records lack explicit "
                        "processing-fee exemption or payment-requirement information [SIMULATED]."
                    ),
                    findings=findings,
                )

        # 3. Payment is Applicable: Check Document Upload Presence
        if not ctx.document_version:
            findings.append(
                FindingDraft(
                    category=FindingCategory.MISSING_DOCUMENT,
                    severity=FindingSeverity.HIGH,
                    title="AICTE Web-Portal Payment Receipt Missing",
                    internal_reason=(
                        "Payment receipt is applicable for this application, but no receipt document "
                        "has been uploaded under EOA-SD-02."
                    ),
                    recommended_action="Upload copy of official AICTE Web-Portal payment receipt or bank challan.",
                    is_internal_only=False,
                )
            )
            return RuleEvaluationOutcome(
                status="DEFICIENT",
                expected_value={"receipt_uploaded": True},
                observed_value={"receipt_uploaded": False},
                explanation="AICTE Web-Portal payment receipt document is missing.",
                findings=findings,
            )

        # 4. Check for Disputed Fields
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
                explanation="Payment receipt fields contain contradictory review decisions. Determination halted.",
                findings=findings,
            )

        # 5. Check for Empty Extractions
        if not ctx.fields:
            findings.append(
                FindingDraft(
                    category=FindingCategory.INCOMPLETE_DOCUMENT,
                    severity=FindingSeverity.MEDIUM,
                    title="Payment Receipt Content Unextracted",
                    internal_reason="Receipt document uploaded but transaction details could not be parsed.",
                    recommended_action="Verify receipt legibility or conduct manual auditor verification.",
                    is_internal_only=True,
                )
            )
            return RuleEvaluationOutcome(
                status="UNABLE_TO_DETERMINE",
                expected_value={"receipt_fields_extracted": True},
                observed_value={"receipt_fields_extracted": False},
                explanation="Payment receipt content could not be verified by automated extractor.",
                findings=findings,
            )

        # 6. Verify Payment Transaction Status
        status_field = ctx.fields.get("payment_status")
        txn_ref_field = ctx.fields.get("transaction_ref_no")
        amount_field = ctx.fields.get("payment_amount")

        pay_status = (
            str(status_field.raw_value or status_field.normalized_value or "")
            .upper()
            .strip()
        )
        observed_data = {
            "payment_status": pay_status,
            "transaction_ref": txn_ref_field.raw_value if txn_ref_field else None,
            "payment_amount": amount_field.raw_value if amount_field else None,
            "provenance": "SIMULATED",
        }

        if pay_status not in ["SUCCESS", "PAID"]:
            findings.append(
                FindingDraft(
                    category=FindingCategory.FIELD_MISMATCH,
                    severity=FindingSeverity.HIGH,
                    title="Payment Receipt Does Not Evince Completed Transaction",
                    internal_reason=(
                        f"Extracted payment status is '{pay_status or 'UNKNOWN'}'. AICTE rules require "
                        "a fully completed, successful transaction receipt."
                    ),
                    recommended_action="Provide transaction receipt reflecting SUCCESS or PAID status.",
                    is_internal_only=False,
                )
            )
            return RuleEvaluationOutcome(
                status="DEFICIENT",
                expected_value={"payment_status": ["SUCCESS", "PAID"]},
                observed_value=observed_data,
                explanation=f"Payment status is '{pay_status}' (not completed/successful).",
                findings=findings,
            )

        return RuleEvaluationOutcome(
            status="SATISFIED",
            expected_value={"payment_status": "SUCCESS", "receipt_uploaded": True},
            observed_value=observed_data,
            explanation="AICTE Web-Portal payment receipt verified with successful transaction status [SIMULATED].",
            findings=findings,
        )

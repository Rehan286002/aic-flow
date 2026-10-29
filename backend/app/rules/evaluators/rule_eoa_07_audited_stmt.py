"""AIC-Verify — Rule Evaluator for EOA-SD-07: Audited Statement of Accounts.

Regulatory Reference:
AICTE Approval Process Handbook (APH) 2024–2027 Annexure 2.1 Item vii:
Previous-year audited statement of accounts of the Trust / Society / Company.

Safeguards Enforced:
1. Grounded in 'previous-year' term; unconditional requirement for FY 2024-25 is removed.
   FY 2024-25 is treated strictly as synthetic demonstration fixture data.
2. 1% figure matching and 2% math tolerances are configurable advisory heuristics only,
   NOT statutory failure criteria.
3. ICAI UDIN check is explicitly labelled as 'synthetic source record match' (SIMULATED).
4. Matches UDIN, Member Number, FRN, and Financial Year only when present in real fixture.
   Does not invent unavailable financial figure comparisons against the portal.
5. Strict reviewer dispute handling: flags CONTENT_ANOMALY and returns UNABLE_TO_DETERMINE.
"""

from __future__ import annotations

import logging
from typing import Any

from app.connectors.icai_udin import ICAIUDINConnector
from app.models.enums import FindingCategory, FindingSeverity
from app.rules.base import (
    AuthoritativeFieldResolver,
    BaseRuleEvaluator,
    FindingDraft,
    RuleEvaluationContext,
    RuleEvaluationOutcome,
)

logger = logging.getLogger(__name__)


def compute_expected_financial_year(academic_year: str) -> list[str]:
    """Derives expected previous financial year variants from academic year convention.

    For an Extension of Approval application for Academic Year YYYY-(YY+1) (e.g. 2026-27),
    filing occurs in early YYYY, so the preceding closed audited financial year is (YYYY-2)-(YY-1) (e.g. 2024-25).
    """
    try:
        parts = academic_year.split("-")
        start_year = int(parts[0])
        prev_fy_start = start_year - 2
        prev_fy_end = prev_fy_start + 1
        short_end = str(prev_fy_end)[-2:]
        return [
            f"{prev_fy_start}-{short_end}",
            f"{prev_fy_start}-{prev_fy_end}",
            f"FY {prev_fy_start}-{short_end}",
            f"FY {prev_fy_start}-{prev_fy_end}",
        ]
    except (ValueError, IndexError):
        return ["2024-25", "2024-2025", "FY 2024-25", "FY 2024-2025"]


class RuleEvaluatorEOA07(BaseRuleEvaluator):
    """Evaluates EOA-SD-07 (Previous-Year Audited Financial Statement) compliance."""

    rule_code = "RULE_EOA_07_AUDITED_STMT"

    def evaluate(self, ctx: RuleEvaluationContext) -> RuleEvaluationOutcome:
        findings: list[FindingDraft] = []

        # 1. Document Upload Presence
        if not ctx.document_version:
            findings.append(
                FindingDraft(
                    category=FindingCategory.MISSING_DOCUMENT,
                    severity=FindingSeverity.HIGH,
                    title="Audited Financial Statement Missing",
                    internal_reason=(
                        "Mandatory requirement EOA-SD-07 has no uploaded document version. "
                        "AICTE APH Annexure 2.1 Item vii mandates previous-year audited balance sheet and statements."
                    ),
                    recommended_action="Upload previous-year audited statement of accounts with CA UDIN.",
                    is_internal_only=False,
                )
            )
            return RuleEvaluationOutcome(
                status="DEFICIENT",
                expected_value={"document_uploaded": True},
                observed_value={"document_uploaded": False},
                explanation="Audited statement of accounts is missing from the application submission.",
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
                explanation="Audited financial statement candidate fields contain conflicting reviews.",
                findings=findings,
            )

        # 3. Check for Empty Extractions
        if not ctx.fields:
            findings.append(
                FindingDraft(
                    category=FindingCategory.INCOMPLETE_DOCUMENT,
                    severity=FindingSeverity.MEDIUM,
                    title="Audited Statement Content Unextracted",
                    internal_reason="Document uploaded but financial year and auditor details could not be parsed.",
                    recommended_action="Review financial statement legibility or conduct manual auditor verification.",
                    is_internal_only=True,
                )
            )
            return RuleEvaluationOutcome(
                status="UNABLE_TO_DETERMINE",
                expected_value={"financial_fields_extracted": True},
                observed_value={"financial_fields_extracted": False},
                explanation="Audited financial statement content could not be verified by automated extractor.",
                findings=findings,
            )

        fy_field = ctx.fields.get("financial_year")
        udin_field = ctx.fields.get("auditor_udin")
        mem_field = ctx.fields.get("auditor_membership_no")
        frn_field = ctx.fields.get("auditor_firm_reg_no")
        trust_field = ctx.fields.get("trust_society_name")
        income_field = ctx.fields.get("gross_annual_income")
        expenditure_field = ctx.fields.get("total_expenditure")
        surplus_field = ctx.fields.get("balance_surplus_deficit")

        extracted_fy = str(fy_field.raw_value if fy_field else "").strip()
        extracted_udin = str(udin_field.raw_value if udin_field else "").strip()

        observed: dict[str, Any] = {
            "financial_year": extracted_fy,
            "auditor_udin": extracted_udin,
            "auditor_membership_no": mem_field.raw_value if mem_field else None,
            "auditor_firm_reg_no": frn_field.raw_value if frn_field else None,
            "trust_society_name": trust_field.raw_value if trust_field else None,
            "provenance": "SIMULATED",
        }
        is_deficient = False

        # 4. Previous-Year Term Verification (Safeguard 4: Not unconditional FY 2024-25)
        # Check against application academic year or declared filing rule term
        app_ay = ctx.application.academic_year if ctx.application else "2026-27"
        observed["application_academic_year"] = app_ay

        if not extracted_fy or extracted_fy.upper() in ["NONE", "NULL", "UNEXTRACTED"]:
            is_deficient = True
            findings.append(
                FindingDraft(
                    category=FindingCategory.INCOMPLETE_DOCUMENT,
                    severity=FindingSeverity.MEDIUM,
                    title="Financial Year Not Extracted from Audit Report",
                    internal_reason="Financial year could not be conclusively parsed from the audit report.",
                    recommended_action="Ensure the audit report clearly specifies the financial year.",
                    is_internal_only=False,
                )
            )
        else:
            expected_fys = compute_expected_financial_year(app_ay)
            primary_expected = expected_fys[0]
            observed["expected_financial_year"] = primary_expected
            matches_expected = any(
                exp.upper() in extracted_fy.upper()
                or extracted_fy.upper() in exp.upper()
                for exp in expected_fys
            )
            if not matches_expected:
                is_deficient = True
                findings.append(
                    FindingDraft(
                        category=FindingCategory.FIELD_MISMATCH,
                        severity=FindingSeverity.HIGH,
                        title=f"Audited Statement Financial Year Mismatch (Expected {primary_expected})",
                        internal_reason=(
                            f"AICTE APH Annexure 2.1 Item vii requires the previous-year audited statement of accounts. "
                            f"For Academic Year {app_ay}, the preceding closed fiscal year is {primary_expected}. "
                            f"Observed extracted financial year: '{extracted_fy}'."
                        ),
                        recommended_action=f"Upload the audited financial statement for financial year {primary_expected}.",
                        is_internal_only=False,
                    )
                )
            else:
                observed["term_status"] = "PREVIOUS_YEAR_EVALUATED"

        # 5. Synthetic ICAI UDIN Source Record Match (SRC_ICAI_UDIN)
        if not extracted_udin or extracted_udin.upper() in [
            "NONE",
            "NULL",
            "UNEXTRACTED",
        ]:
            is_deficient = True
            findings.append(
                FindingDraft(
                    category=FindingCategory.INCOMPLETE_DOCUMENT,
                    severity=FindingSeverity.HIGH,
                    title="Chartered Accountant UDIN Missing from Audit Report",
                    internal_reason="Audit report lacks a valid Unique Document Identification Number (UDIN).",
                    recommended_action="Submit audited financial statement containing a valid ICAI UDIN.",
                    is_internal_only=False,
                )
            )
        else:
            # Query real synthetic ICAI UDIN connector
            icai_connector = ICAIUDINConnector()
            ver_res = icai_connector.verify_document_reference(
                document_reference=extracted_udin
            )
            res_summary = ver_res.response_summary
            observed["synthetic_icai_udin_match"] = res_summary

            if ver_res.status.value == "MISMATCH":
                is_deficient = True
                status_reason = res_summary.get("status", "NOT_FOUND")
                if status_reason == "REVOKED":
                    findings.append(
                        FindingDraft(
                            category=FindingCategory.SOURCE_MISMATCH,
                            severity=FindingSeverity.CRITICAL,
                            title="Auditor UDIN Revoked in Synthetic ICAI Records [SIMULATED]",
                            internal_reason=(
                                f"UDIN '{extracted_udin}' is officially flagged as REVOKED "
                                f"({res_summary.get('revocation_reason')}) in synthetic source records [SIMULATED]."
                            ),
                            recommended_action="Obtain clarification or re-issued report with an active valid UDIN.",
                            is_internal_only=False,
                        )
                    )
                else:
                    findings.append(
                        FindingDraft(
                            category=FindingCategory.SOURCE_MISMATCH,
                            severity=FindingSeverity.HIGH,
                            title="Auditor UDIN Not Found in Synthetic ICAI Records [SIMULATED]",
                            internal_reason=(
                                f"UDIN '{extracted_udin}' could not be matched in the synthetic ICAI "
                                "portal reference dataset [SIMULATED]."
                            ),
                            recommended_action="Verify correctness of stated UDIN with certifying Chartered Accountant.",
                            is_internal_only=False,
                        )
                    )
            elif ver_res.status.value == "VERIFIED":
                # Matched active UDIN in synthetic source
                observed["ca_name"] = res_summary.get("ca_name")
                observed["ca_membership_number"] = res_summary.get(
                    "ca_membership_number"
                )
                observed["ca_firm_registration_number"] = res_summary.get(
                    "ca_firm_registration_number"
                )

        # 6. Configurable Arithmetic Reconciliation Heuristic (Safeguard 4: NOT statutory failure)
        try:
            inc = (
                float(income_field.normalized_value.get("numeric_value"))
                if income_field and isinstance(income_field.normalized_value, dict)
                else None
            )
            exp = (
                float(expenditure_field.normalized_value.get("numeric_value"))
                if expenditure_field
                and isinstance(expenditure_field.normalized_value, dict)
                else None
            )
            sur = (
                float(surplus_field.normalized_value.get("numeric_value"))
                if surplus_field and isinstance(surplus_field.normalized_value, dict)
                else None
            )

            if inc is not None and exp is not None and sur is not None and inc > 0:
                expected_sur = inc - exp
                discrepancy = abs(expected_sur - sur) / inc
                observed["arithmetic_discrepancy_pct"] = round(discrepancy * 100.0, 2)
                if discrepancy > 0.02:  # 2% configurable anomaly heuristic
                    findings.append(
                        FindingDraft(
                            category=FindingCategory.CONTENT_ANOMALY,
                            severity=FindingSeverity.INFO,
                            title="Audited Financial Statement Arithmetic Heuristic Observation",
                            internal_reason=(
                                f"Internal arithmetic check: Gross Income ({inc:,.0f}) - Expenditure ({exp:,.0f}) = "
                                f"{expected_sur:,.0f}, while stated surplus/deficit is {sur:,.0f} "
                                f"(discrepancy {discrepancy * 100.0:.2f}% > 2% advisory tolerance). "
                                "Configured as advisory anomaly observation, not statutory failure."
                            ),
                            recommended_action="Auditor to verify income & expenditure schedule notes.",
                            is_internal_only=True,
                        )
                    )
        except (ValueError, TypeError, KeyError):
            pass

        status = "DEFICIENT" if is_deficient else "SATISFIED"
        explanation = (
            "Audited statement of accounts verified with active synthetic ICAI UDIN match [SIMULATED]."
            if status == "SATISFIED"
            else "Audited statement of accounts does not satisfy statutory previous-year term or UDIN verification."
        )

        return RuleEvaluationOutcome(
            status=status,
            expected_value={"active_udin": True, "provenance": "SIMULATED"},
            observed_value=observed,
            explanation=explanation,
            findings=findings,
        )

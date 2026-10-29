"""Rule Evaluator for EOA-SD-04: Structural Stability Certificate.

Regulatory Reference:
AICTE Approval Process Handbook (APH) 2024–2027 Annexure 2.1 Item iv:
Valid Structural Stability Certificate from a registered Structural Engineer when the building
is more than 30 years from the issue of its Completion Certificate. (Validity period: 5 years).

Safeguards Enforced:
1. Calendar-based 30-year anniversary calculation (strictly > 30 years), not days / 365.25.
2. Uses the actual Completion Certificate issue date (not generic occupancy/completion dates).
3. 5-year certificate validity strictly enforced from certificate issue date.
4. Engineer's registration number alone does not prove registration; records unverified note.
5. Strict reviewer dispute handling: flags CONTENT_ANOMALY and returns UNABLE_TO_DETERMINE.
"""

from __future__ import annotations

import logging
from datetime import date, datetime
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

# AY 2026–27 structural-stability assessment reference date
DEFAULT_ASSESSMENT_DATE = date(2026, 7, 1)


def _add_calendar_years(d: date, years: int) -> date:
    """Adds exact calendar years to a date, handling leap-year Feb 29 safely."""
    try:
        return d.replace(year=d.year + years)
    except ValueError:
        # Feb 29 on non-leap year falls back to Feb 28
        return d.replace(year=d.year + years, day=28)


class RuleEvaluatorEOA04(BaseRuleEvaluator):
    """Evaluates EOA-SD-04 (Structural Stability Certificate) compliance."""

    rule_code = "RULE_EOA_04_STRUCTURAL"

    def evaluate(self, ctx: RuleEvaluationContext) -> RuleEvaluationOutcome:
        findings: list[FindingDraft] = []
        assessment_date = (
            ctx.evaluation_as_of.date()
            if ctx.evaluation_as_of
            else DEFAULT_ASSESSMENT_DATE
        )

        # 1. Establish Actual Completion Certificate Issue Date
        cc_issue_date: date | None = None

        # a) Check municipal building source record (SRC_MUNICIPAL_BLDG)
        muni_snapshot = ctx.source_snapshots.get("SRC_MUNICIPAL_BLDG")
        if muni_snapshot and isinstance(muni_snapshot.record_data, dict):
            raw_date = muni_snapshot.record_data.get("building_completion_date")
            if raw_date:
                try:
                    cc_issue_date = datetime.strptime(
                        str(raw_date)[:10], "%Y-%m-%d"
                    ).date()
                except ValueError:
                    pass

        # b) Check applicant declared field: completion_certificate_issue_date
        if not cc_issue_date and ctx.revision:
            for fv in ctx.revision.field_values:
                if (
                    fv.field_definition
                    and fv.field_definition.field_code
                    == "completion_certificate_issue_date"
                ):
                    val = fv.value_json
                    raw_str = None
                    if isinstance(val, str):
                        raw_str = val
                    elif isinstance(val, dict):
                        raw_str = val.get("date") or val.get("value")
                    if raw_str:
                        try:
                            cc_issue_date = datetime.strptime(
                                str(raw_str)[:10], "%Y-%m-%d"
                            ).date()
                        except ValueError:
                            pass

        if not cc_issue_date:
            # Completion Certificate issue date cannot be established
            findings.append(
                FindingDraft(
                    category=FindingCategory.REGULATORY_GAP,
                    severity=FindingSeverity.HIGH,
                    title="Completion Certificate Issue Date Missing for Building Age Evaluation",
                    internal_reason=(
                        "AICTE APH Annexure 2.1 Item iv mandates a Structural Stability Certificate when "
                        "the building is more than 30 years from the issue of its Completion Certificate. "
                        "The Completion Certificate issue date could not be established from municipal records "
                        "or self-disclosures."
                    ),
                    recommended_action="Declare the official Completion Certificate issue date with supporting municipal records.",
                    is_internal_only=False,
                )
            )
            return RuleEvaluationOutcome(
                status="UNABLE_TO_DETERMINE",
                expected_value={"completion_certificate_issue_date_known": True},
                observed_value={"completion_certificate_issue_date_known": False},
                explanation="Building age cannot be determined because Completion Certificate issue date is missing.",
                findings=findings,
            )

        # 2. Strict Calendar-Based 30-Year Anniversary Calculation
        thirty_year_anniversary = _add_calendar_years(cc_issue_date, 30)
        is_greater_than_30 = assessment_date > thirty_year_anniversary

        observed: dict[str, Any] = {
            "completion_certificate_issue_date": cc_issue_date.isoformat(),
            "thirty_year_anniversary": thirty_year_anniversary.isoformat(),
            "assessment_reference_date": assessment_date.isoformat(),
            "is_greater_than_30_years": is_greater_than_30,
        }

        # 3. Branch: If age <= 30.0 years, certificate is NOT_APPLICABLE
        if not is_greater_than_30:
            return RuleEvaluationOutcome(
                status="NOT_APPLICABLE",
                expected_value={"building_age_gt_30": False},
                observed_value=observed,
                explanation=(
                    f"Building has not exceeded 30 years from Completion Certificate issue date "
                    f"({cc_issue_date.isoformat()}). 30-year anniversary is {thirty_year_anniversary.isoformat()}, "
                    f"which is on or after the assessment date {assessment_date.isoformat()}. "
                    "Structural Stability Certificate is NOT_APPLICABLE under Annexure 2.1 Item iv."
                ),
                findings=findings,
            )

        # 4. Building is strictly > 30 years old: Certificate is APPLICABLE and MANDATORY
        if not ctx.document_version:
            findings.append(
                FindingDraft(
                    category=FindingCategory.MISSING_DOCUMENT,
                    severity=FindingSeverity.HIGH,
                    title="Mandatory Structural Stability Certificate Missing (>30-Year Building)",
                    internal_reason=(
                        f"Building is more than 30 years old from its Completion Certificate issue date "
                        f"({cc_issue_date.isoformat()} > 30-year anniversary {thirty_year_anniversary.isoformat()}). "
                        "APH Annexure 2.1 Item iv requires a valid Structural Stability Certificate."
                    ),
                    recommended_action="Upload a valid Structural Stability Certificate from a registered structural engineer.",
                    is_internal_only=False,
                )
            )
            return RuleEvaluationOutcome(
                status="DEFICIENT",
                expected_value={"document_uploaded": True, "building_age_gt_30": True},
                observed_value=observed,
                explanation="Building exceeds 30 years from Completion Certificate issue date, but structural stability certificate is missing.",
                findings=findings,
            )

        # 5. Check for Disputed Fields
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
                explanation="Structural stability certificate candidate fields contain contradictory review decisions.",
                findings=findings,
            )

        # 6. Check for Empty Extractions
        if not ctx.fields:
            findings.append(
                FindingDraft(
                    category=FindingCategory.INCOMPLETE_DOCUMENT,
                    severity=FindingSeverity.MEDIUM,
                    title="Structural Stability Certificate Content Unextracted",
                    internal_reason="Document uploaded but engineer credentials and certificate validity dates could not be parsed.",
                    recommended_action="Verify document legibility or conduct manual auditor verification.",
                    is_internal_only=True,
                )
            )
            return RuleEvaluationOutcome(
                status="UNABLE_TO_DETERMINE",
                expected_value={"stability_fields_extracted": True},
                observed_value={"stability_fields_extracted": False},
                explanation="Structural stability certificate details could not be parsed by automated extractor.",
                findings=findings,
            )

        # 7. Evaluate 5-Year Statutory Validity Period
        cert_issue_date_field = ctx.fields.get("issue_date")
        license_field = ctx.fields.get("engineer_license_no")
        soundness_field = ctx.fields.get("stability_certification_statement")
        observed["certification_statement"] = (
            soundness_field.raw_value if soundness_field else None
        )

        cert_date: date | None = None
        if cert_issue_date_field and isinstance(
            cert_issue_date_field.normalized_value, dict
        ):
            iso_d = cert_issue_date_field.normalized_value.get("iso_date")
            if iso_d:
                try:
                    cert_date = datetime.strptime(str(iso_d)[:10], "%Y-%m-%d").date()
                except ValueError:
                    pass

        is_deficient = False
        if not cert_date:
            is_deficient = True
            findings.append(
                FindingDraft(
                    category=FindingCategory.INCOMPLETE_DOCUMENT,
                    severity=FindingSeverity.HIGH,
                    title="Structural Stability Certificate Issue Date Unverified",
                    internal_reason="Certificate issue date could not be established to determine 5-year validity.",
                    recommended_action="Ensure the inspection and issue date is clearly visible.",
                    is_internal_only=False,
                )
            )
        else:
            five_year_limit = _add_calendar_years(cert_date, 5)
            observed["certificate_issue_date"] = cert_date.isoformat()
            observed["five_year_validity_limit"] = five_year_limit.isoformat()
            if assessment_date > five_year_limit:
                is_deficient = True
                findings.append(
                    FindingDraft(
                        category=FindingCategory.EXPIRED_DOCUMENT,
                        severity=FindingSeverity.HIGH,
                        title="Structural Stability Certificate Expired (>5-Year Validity Exceeded)",
                        internal_reason=(
                            f"Certificate issue date is {cert_date.isoformat()}. Under APH Annexure 2.1 Item iv, "
                            f"validity period is 5 years (expired on {five_year_limit.isoformat()})."
                        ),
                        recommended_action="Commission fresh structural stability inspection and submit new certificate.",
                        is_internal_only=False,
                    )
                )

        # 8. Engineer Registration Credentials
        eng_license = str(license_field.raw_value if license_field else "").strip()
        observed["engineer_license_no"] = eng_license
        if not eng_license or eng_license.upper() in ["NONE", "NULL", "UNEXTRACTED"]:
            is_deficient = True
            findings.append(
                FindingDraft(
                    category=FindingCategory.INCOMPLETE_DOCUMENT,
                    severity=FindingSeverity.HIGH,
                    title="Structural Engineer Registration Details Missing",
                    internal_reason="Certificate lacks structural engineer registration / license number.",
                    recommended_action="Certificate must be signed by a registered Structural Engineer with license number.",
                    is_internal_only=False,
                )
            )
        else:
            # Safeguard 2: Engineer registration number alone does not prove registration
            findings.append(
                FindingDraft(
                    category=FindingCategory.INFRASTRUCTURE_OBSERVATION,
                    severity=FindingSeverity.INFO,
                    title="Structural Engineer Professional Registration Unverified against External Registry",
                    internal_reason=(
                        f"Extracted engineer license number '{eng_license}'. An independent professional "
                        "registration registry check was not conducted. Stated number is accepted as candidate data only."
                    ),
                    recommended_action="Verify registration credentials with local municipal or engineers council registry if disputed.",
                    is_internal_only=True,
                )
            )

        status = "DEFICIENT" if is_deficient else "SATISFIED"
        explanation = (
            f"Structural stability certificate verified valid within 5-year statutory period (issued {cert_date})."
            if status == "SATISFIED"
            else "Structural stability certificate does not meet statutory 5-year validity or credential requirements."
        )

        return RuleEvaluationOutcome(
            status=status,
            expected_value={
                "statutory_validity_years": 5,
                "require_registered_engineer": True,
            },
            observed_value=observed,
            explanation=explanation,
            findings=findings,
        )

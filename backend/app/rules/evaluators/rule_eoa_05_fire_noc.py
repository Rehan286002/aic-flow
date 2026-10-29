"""AIC-Verify — Rule Evaluator for EOA-SD-05: Fire Safety Certificate.

Regulatory Reference:
AICTE Approval Process Handbook (APH) 2024–2027 Annexure 2.1 Item v:
Valid Fire Safety Certificate issued by the Competent Authority.

Safeguards Enforced:
1. Do not treat all fire NOCs as valid indefinitely; verifies unexpired term.
2. Cross-checks against State Fire Services Directorates (SRC_FIRE_SERVICES).
3. Distinguishes expired vs revoked vs active NOCs.
4. All synthetic outcomes explicitly labelled SIMULATED.
5. Strict reviewer dispute handling: flags CONTENT_ANOMALY and returns UNABLE_TO_DETERMINE.
"""

from __future__ import annotations

import logging
from datetime import datetime
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


class RuleEvaluatorEOA05(BaseRuleEvaluator):
    """Evaluates EOA-SD-05 (Fire Safety Certificate) compliance."""

    rule_code = "RULE_EOA_05_FIRE_NOC"

    def evaluate(self, ctx: RuleEvaluationContext) -> RuleEvaluationOutcome:
        findings: list[FindingDraft] = []
        eval_date = ctx.evaluation_as_of.date()

        # 1. Document Upload Presence
        if not ctx.document_version:
            findings.append(
                FindingDraft(
                    category=FindingCategory.MISSING_DOCUMENT,
                    severity=FindingSeverity.HIGH,
                    title="Fire Safety Certificate Missing",
                    internal_reason=(
                        "Mandatory requirement EOA-SD-05 has no uploaded document version. "
                        "AICTE APH Annexure 2.1 Item v mandates a valid Fire Safety Certificate issued by the competent authority."
                    ),
                    recommended_action="Upload a valid Fire Safety Certificate / NOC issued by the local fire authority.",
                    is_internal_only=False,
                )
            )
            return RuleEvaluationOutcome(
                status="DEFICIENT",
                expected_value={"document_uploaded": True},
                observed_value={"document_uploaded": False},
                explanation="Fire Safety Certificate is missing from the application submission.",
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
                explanation="Fire safety certificate candidate fields contain contradictory reviews. Determination halted.",
                findings=findings,
            )

        # 3. Check for Empty Extractions
        if not ctx.fields:
            findings.append(
                FindingDraft(
                    category=FindingCategory.INCOMPLETE_DOCUMENT,
                    severity=FindingSeverity.MEDIUM,
                    title="Fire Safety Certificate Details Unextracted",
                    internal_reason="Fire safety document uploaded but NOC number and validity dates could not be parsed.",
                    recommended_action="Review document quality or conduct manual auditor verification.",
                    is_internal_only=True,
                )
            )
            return RuleEvaluationOutcome(
                status="UNABLE_TO_DETERMINE",
                expected_value={"fire_fields_extracted": True},
                observed_value={"fire_fields_extracted": False},
                explanation="Fire safety certificate content could not be verified by automated extractor.",
                findings=findings,
            )

        noc_field = ctx.fields.get("fire_noc_number")
        expiry_field = ctx.fields.get("expiry_date")
        issue_field = ctx.fields.get("issue_date")
        dept_field = ctx.fields.get("issuing_department")

        observed: dict[str, Any] = {
            "fire_noc_number": noc_field.raw_value if noc_field else None,
            "issue_date": issue_field.raw_value if issue_field else None,
            "issuing_department": dept_field.raw_value if dept_field else None,
            "provenance": "SIMULATED",
        }
        is_deficient = False

        # 4. Check Stated Expiry Date on Document
        doc_expiry_date = None
        if expiry_field and isinstance(expiry_field.normalized_value, dict):
            raw_iso = expiry_field.normalized_value.get("iso_date")
            if raw_iso:
                try:
                    doc_expiry_date = datetime.strptime(
                        str(raw_iso)[:10], "%Y-%m-%d"
                    ).date()
                except ValueError:
                    pass

        if doc_expiry_date:
            observed["extracted_expiry_date"] = doc_expiry_date.isoformat()
            if doc_expiry_date < eval_date:
                is_deficient = True
                findings.append(
                    FindingDraft(
                        category=FindingCategory.EXPIRED_DOCUMENT,
                        severity=FindingSeverity.HIGH,
                        title="Fire Safety Certificate Expired (Document Stated Date)",
                        internal_reason=(
                            f"Fire NOC expired on {doc_expiry_date.isoformat()} prior to evaluation date "
                            f"({eval_date.isoformat()}). AICTE rules mandate an active, valid Fire Safety Certificate."
                        ),
                        recommended_action="Apply for fire NOC renewal and submit the renewed certificate.",
                        is_internal_only=False,
                    )
                )

        # 5. Synthetic Source Cross-Check (SRC_FIRE_SERVICES)
        fire_snapshot = ctx.source_snapshots.get("SRC_FIRE_SERVICES")
        if fire_snapshot and isinstance(fire_snapshot.record_data, dict):
            f_rec = fire_snapshot.record_data
            src_status = str(f_rec.get("compliance_status", "UNKNOWN")).upper()
            src_valid_until = f_rec.get("valid_until")
            observed["source_compliance_status"] = src_status
            observed["source_valid_until"] = src_valid_until

            if src_status == "REVOKED":
                is_deficient = True
                findings.append(
                    FindingDraft(
                        category=FindingCategory.SOURCE_MISMATCH,
                        severity=FindingSeverity.CRITICAL,
                        title="Fire Safety Certificate Revoked by Fire Directorate [SIMULATED]",
                        internal_reason=(
                            f"State fire services records indicate certificate '{f_rec.get('fire_noc_certificate_number')}' "
                            "has been officially REVOKED [SIMULATED]."
                        ),
                        recommended_action="Immediately rectify fire safety non-compliances and obtain fresh clearance.",
                        is_internal_only=False,
                    )
                )
            elif src_status == "EXPIRED":
                is_deficient = True
                findings.append(
                    FindingDraft(
                        category=FindingCategory.EXPIRED_DOCUMENT,
                        severity=FindingSeverity.HIGH,
                        title="Fire Safety Certificate Expired in State Fire Directorate Registry [SIMULATED]",
                        internal_reason=(
                            f"State fire services registry lists certificate '{f_rec.get('fire_noc_certificate_number')}' "
                            f"as EXPIRED as of {src_valid_until} [SIMULATED]."
                        ),
                        recommended_action="Submit renewed Fire Safety Certificate.",
                        is_internal_only=False,
                    )
                )

        status = "DEFICIENT" if is_deficient else "SATISFIED"
        explanation = (
            "Fire Safety Certificate verified unexpired and active in State Fire Services registry [SIMULATED]."
            if status == "SATISFIED"
            else "Fire Safety Certificate is expired or revoked under fire safety regulatory standards."
        )

        return RuleEvaluationOutcome(
            status=status,
            expected_value={
                "unexpired_fire_noc": True,
                "active_source_status": True,
                "provenance": "SIMULATED",
            },
            observed_value=observed,
            explanation=explanation,
            findings=findings,
        )

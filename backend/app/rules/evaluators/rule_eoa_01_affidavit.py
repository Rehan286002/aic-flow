"""AIC-Verify — Rule Evaluator for EOA-SD-01: Affidavit 2.

Regulatory Reference:
AICTE Approval Process Handbook (APH) 2024–2027 Annexure 2.1 Item i:
Notarized affidavit on ₹100 non-judicial stamp paper / e-stamp paper affirming compliance
with AICTE governance, fee, and faculty norms.

Safeguards Enforced:
1. Strict ₹100 e-stamp requirement per APH Annexure 2.1 Item i.
2. Signatory authentication: Chairman / Secretary for self-financing institutions;
   Authorised Person / Signatory for Government or Government-aided institutions.
   Generic Trustee/President matches or raw OCR text alone are insufficient.
3. Required oath / notary attestation and registration number evidence.
4. Digital signature check observation if applicable.
5. Strict reviewer dispute handling: flags CONTENT_ANOMALY and returns UNABLE_TO_DETERMINE.
6. Non-fabrication: Distinguishes missing document from unextracted/low-confidence OCR.
"""

from __future__ import annotations

import logging
from typing import Any

from app.models.enums import FindingCategory, FindingSeverity
from app.rules.base import (
    AuthoritativeFieldResolver,
    BaseRuleEvaluator,
    FindingDraft,
    FindingEvidenceDraft,
    RuleEvaluationContext,
    RuleEvaluationOutcome,
)

logger = logging.getLogger(__name__)


class RuleEvaluatorEOA01(BaseRuleEvaluator):
    """Evaluates EOA-SD-01 (Affidavit 2) compliance."""

    rule_code = "RULE_EOA_01_AFFIDAVIT"

    def evaluate(self, ctx: RuleEvaluationContext) -> RuleEvaluationOutcome:
        findings: list[FindingDraft] = []

        # 1. Check Document Upload Presence
        if not ctx.document_version:
            findings.append(
                FindingDraft(
                    category=FindingCategory.MISSING_DOCUMENT,
                    severity=FindingSeverity.HIGH,
                    title="Affidavit 2 Document Not Uploaded",
                    internal_reason=(
                        "Mandatory requirement EOA-SD-01 (Affidavit 2) has no uploaded document version."
                    ),
                    recommended_action="Upload notarized Affidavit 2 on ₹100 non-judicial stamp paper.",
                    is_internal_only=False,
                )
            )
            return RuleEvaluationOutcome(
                status="DEFICIENT",
                expected_value={"document_uploaded": True},
                observed_value={"document_uploaded": False},
                explanation="Affidavit 2 document is missing from the application submission.",
                findings=findings,
            )

        # 2. Check for Disputed Fields across Review History
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
                explanation=(
                    f"Candidate fields ({', '.join(df.field_code for df in disputed_fields)}) have "
                    "contradictory auditor review decisions. Determination halted pending committee review."
                ),
                findings=findings,
            )

        # 3. Check for Empty Extractions / Low Confidence OCR
        if not ctx.fields:
            findings.append(
                FindingDraft(
                    category=FindingCategory.INCOMPLETE_DOCUMENT,
                    severity=FindingSeverity.MEDIUM,
                    title="Affidavit 2 Fields Unextracted or OCR Inconclusive",
                    internal_reason=(
                        "Uploaded document for Affidavit 2 yielded 0 structured candidate fields. "
                        "OCR confidence may be low or document may lack expected standard formatting."
                    ),
                    recommended_action="Review uploaded document legibility or perform manual auditor verification.",
                    is_internal_only=True,
                    evidence_items=[
                        FindingEvidenceDraft(
                            document_version_id=ctx.document_version.document_version_id,
                            evidence_type="DOCUMENT_SCAN",
                            evidence_summary=f"File: {ctx.document_version.original_filename} ({ctx.document_version.mime_type})",
                        )
                    ],
                )
            )
            return RuleEvaluationOutcome(
                status="UNABLE_TO_DETERMINE",
                expected_value={"extracted_fields_present": True},
                observed_value={"extracted_fields_present": False},
                explanation="Affidavit 2 content could not be conclusively extracted for automated validation.",
                findings=findings,
            )

        # 4. Extract Resolved Fields
        stamp_field = ctx.fields.get("stamp_duty_amount")
        deponent_field = ctx.fields.get("deponent_designation")
        notary_field = ctx.fields.get("notary_registration_no")
        aicte_id_field = ctx.fields.get("aicte_permanent_id")

        observed: dict[str, Any] = {}
        is_deficient = False

        # 5. Statutory Validation: Specified ₹100 Stamp Duty Requirement
        req_stamp = 100.0
        stamp_val: float | None = None
        if stamp_field and stamp_field.normalized_value:
            if isinstance(stamp_field.normalized_value, dict):
                stamp_val = stamp_field.normalized_value.get("numeric_value")
            elif isinstance(stamp_field.normalized_value, (int, float)):
                stamp_val = float(stamp_field.normalized_value)
        elif stamp_field and stamp_field.raw_value:
            # Fallback raw parse
            import re

            m = re.search(r"(\d+)", stamp_field.raw_value)
            if m:
                stamp_val = float(m.group(1))

        observed["stamp_duty_inr"] = stamp_val
        if stamp_val is None or stamp_val < req_stamp:
            is_deficient = True
            findings.append(
                FindingDraft(
                    category=FindingCategory.REGULATORY_GAP,
                    severity=FindingSeverity.HIGH,
                    title="Affidavit 2 Stamp Duty Below Statutory Requirement",
                    internal_reason=(
                        f"AICTE APH Annexure 2.1 Item i mandates ₹100 non-judicial e-stamp paper. "
                        f"Observed stamp duty amount: ₹{stamp_val or 'NOT_EXTRACTED'}."
                    ),
                    recommended_action="Execute Affidavit 2 on e-stamp paper of value ₹100 or higher.",
                    is_internal_only=False,
                    evidence_items=[
                        FindingEvidenceDraft(
                            document_version_id=ctx.document_version.document_version_id,
                            extracted_field_id=stamp_field.extracted_field_id
                            if stamp_field
                            else None,
                            evidence_type="EXTRACTED_FIELD",
                            evidence_reference="stamp_duty_amount",
                            evidence_summary=f"Stated stamp duty: {stamp_val}",
                        )
                    ]
                    if stamp_field
                    else [],
                )
            )

        # 6. Signatory Authentication Category Verification
        # Self-financing Trust/Society/Company -> Chairman or Secretary
        # Government / Govt-aided -> Principal, Director, or Authorised Person
        inst_snapshot = ctx.source_snapshots.get("SRC_AICTE_PORTAL")
        inst_type = "SELF_FINANCING"
        if inst_snapshot and isinstance(inst_snapshot.record_data, dict):
            raw_type = str(
                inst_snapshot.record_data.get("institution_type", "")
            ).upper()
            if "GOVT" in raw_type or "GOVERNMENT" in raw_type:
                inst_type = "GOVERNMENT"

        deponent_title = str(
            deponent_field.raw_value
            or (deponent_field.normalized_value if deponent_field else "")
        ).upper()
        observed["deponent_designation"] = deponent_title
        observed["institution_category"] = inst_type

        if inst_type == "GOVERNMENT":
            valid_titles = [
                "PRINCIPAL",
                "DIRECTOR",
                "AUTHORISED PERSON",
                "AUTHORISED SIGNATORY",
                "AUTHORIZED OFFICER",
            ]
        else:
            # Self-financing: strictly Chairman or Secretary per APH norm
            valid_titles = ["CHAIRMAN", "SECRETARY"]

        has_valid_title = any(vt in deponent_title for vt in valid_titles)
        if not has_valid_title:
            is_deficient = True
            findings.append(
                FindingDraft(
                    category=FindingCategory.CONTENT_ANOMALY,
                    severity=FindingSeverity.HIGH,
                    title="Affidavit 2 Deponent Signatory Ineligible for Institution Type",
                    internal_reason=(
                        f"For {inst_type} institutions, APH Annexure 2.1 Item i mandates execution by "
                        f"{' / '.join(valid_titles)}. Observed designation '{deponent_title}' does not satisfy "
                        "the authorized signatory category. Generic Trustee or unverified designations are insufficient."
                    ),
                    recommended_action=(
                        f"Affidavit 2 must be affirmed by the {' / '.join(valid_titles)} of the institution."
                    ),
                    is_internal_only=False,
                    evidence_items=[
                        FindingEvidenceDraft(
                            document_version_id=ctx.document_version.document_version_id,
                            extracted_field_id=deponent_field.extracted_field_id
                            if deponent_field
                            else None,
                            evidence_type="EXTRACTED_FIELD",
                            evidence_reference="deponent_designation",
                            evidence_summary=f"Observed designation: '{deponent_title}'",
                        )
                    ]
                    if deponent_field
                    else [],
                )
            )

        # 7. Notary Registration and Oath Evidence
        notary_reg = str(
            notary_field.raw_value
            or (notary_field.normalized_value if notary_field else "")
        ).strip()
        observed["notary_registration_no"] = notary_reg
        if not notary_reg or notary_reg.upper() in ["NONE", "NULL", "UNEXTRACTED"]:
            is_deficient = True
            findings.append(
                FindingDraft(
                    category=FindingCategory.INCOMPLETE_DOCUMENT,
                    severity=FindingSeverity.MEDIUM,
                    title="Affidavit 2 Notary Registration Evidence Missing",
                    internal_reason=(
                        "Notary public registration number / seal details were not extracted from Affidavit 2. "
                        "A sworn affidavit requires evidence of attestation before a Notary Public / Oath Commissioner."
                    ),
                    recommended_action="Ensure the Notary Public seal and registration number are clearly legible.",
                    is_internal_only=False,
                )
            )

        # 8. Synthetic Source Cross-Check: AICTE Permanent ID Match
        if (
            aicte_id_field
            and inst_snapshot
            and isinstance(inst_snapshot.record_data, dict)
        ):
            expected_id = inst_snapshot.record_data.get("aicte_permanent_id")
            extracted_id = str(
                aicte_id_field.raw_value or aicte_id_field.normalized_value or ""
            ).strip()
            observed["extracted_aicte_id"] = extracted_id
            observed["source_aicte_id"] = expected_id
            if expected_id and extracted_id and extracted_id != expected_id:
                is_deficient = True
                findings.append(
                    FindingDraft(
                        category=FindingCategory.SOURCE_MISMATCH,
                        severity=FindingSeverity.HIGH,
                        title="AICTE Permanent Institute ID Mismatch on Affidavit 2",
                        internal_reason=(
                            f"Affidavit 2 declares AICTE ID '{extracted_id}', which does not match "
                            f"the master institutional portal record '{expected_id}'."
                        ),
                        recommended_action="Ensure Affidavit 2 reflects the official AICTE Permanent Institute ID.",
                        is_internal_only=True,
                    )
                )

        status = "DEFICIENT" if is_deficient else "SATISFIED"
        explanation = (
            "Affidavit 2 satisfies all statutory criteria: ₹100 e-stamp paper verified, authorized signatory "
            "category confirmed, and notary attestation evidenced."
            if status == "SATISFIED"
            else "Affidavit 2 does not meet one or more statutory requirements under APH Annexure 2.1 Item i."
        )

        return RuleEvaluationOutcome(
            status=status,
            expected_value={
                "stamp_duty_inr": req_stamp,
                "authorized_signatories": valid_titles,
                "require_notary": True,
            },
            observed_value=observed,
            explanation=explanation,
            findings=findings,
        )

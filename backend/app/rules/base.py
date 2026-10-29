"""AIC-Verify — Base Classes, Context & Authoritative Field Resolver for Rule Engine.

Enforces:
- Strict separation between extracted candidate fields, human reviews, and resolved values.
- Zero-tolerance prohibition on latest-wins or role-priority heuristics for conflicting reviews.
- Explainable finding and evidence draft generation.
"""

from __future__ import annotations

import json
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any
from uuid import UUID

from sqlalchemy.orm import Session

from app.models.application import Application
from app.models.application_requirements import ApplicationRequirement
from app.models.application_revision import ApplicationRevision
from app.models.checklist_item import ChecklistItem
from app.models.document_version import DocumentVersion
from app.models.enums import FindingCategory, FindingSeverity, FindingStatus
from app.models.extracted_field import ExtractedField
from app.models.extracted_field_review import ExtractedFieldReview
from app.models.institution import Institution
from app.models.institution_record_version import InstitutionRecordVersion
from app.models.validation_rule import ValidationRule
from app.models.validation_rule_version import ValidationRuleVersion


@dataclass
class FindingEvidenceDraft:
    """Draft evidence link to attach to a Finding."""

    document_version_id: UUID | None = None
    extracted_field_id: UUID | None = None
    verification_attempt_id: UUID | None = None
    page_number: int | None = None
    evidence_type: str = "EXTRACTED_FIELD"
    evidence_reference: str | None = None
    evidence_summary: str | None = None


@dataclass
class FindingDraft:
    """Draft regulatory finding produced by a rule evaluator."""

    category: FindingCategory
    severity: FindingSeverity
    title: str
    internal_reason: str
    recommended_action: str | None = None
    is_internal_only: bool = True
    status: FindingStatus = FindingStatus.OPEN
    evidence_items: list[FindingEvidenceDraft] = field(default_factory=list)


@dataclass
class ResolvedField:
    """Resolved candidate or human-verified field with provenance and review status."""

    field_code: str
    field_label: str | None
    raw_value: str | None
    normalized_value: Any | None
    confidence: float | None
    extracted_field_id: UUID | None
    document_version_id: UUID | None
    page_number: int | None
    is_reviewed: bool = False
    review_count: int = 0
    is_disputed: bool = False
    dispute_reason: str | None = None
    conflicting_reviews: list[ExtractedFieldReview] = field(default_factory=list)


@dataclass
class RuleEvaluationContext:
    """Execution context supplied to a rule evaluator."""

    db: Session
    institution: Institution
    application: Application
    revision: ApplicationRevision
    requirement: ApplicationRequirement
    checklist_item: ChecklistItem
    rule: ValidationRule
    rule_version: ValidationRuleVersion
    document_version: DocumentVersion | None
    fields: dict[str, ResolvedField]
    source_snapshots: dict[str, InstitutionRecordVersion]
    evaluation_as_of: datetime
    triggered_by: UUID | None = None


@dataclass
class RuleEvaluationOutcome:
    """Result of evaluating a single regulatory rule against an application requirement."""

    status: str  # 'SATISFIED', 'DEFICIENT', 'NOT_APPLICABLE', 'UNABLE_TO_DETERMINE', 'WARNING'
    expected_value: Any | None
    observed_value: Any | None
    explanation: str
    findings: list[FindingDraft] = field(default_factory=list)


class AuthoritativeFieldResolver:
    """Resolves authoritative field values from candidate extractions and review history.

    Guarantees:
    - If 0 reviews exist: uses automated candidate normalized_value.
    - If 1 review exists: uses review decision (accepted candidate or corrected value).
    - If >= 2 reviews exist:
      - If all reviews consensus-agree on the final value: uses the consensus value.
      - If ANY reviews disagree: flags an UNRESOLVED REVIEWER DISPUTE (is_disputed=True).
        Strictly prohibits silent resolution via latest-timestamp-wins or role priority!
    """

    @staticmethod
    def resolve_fields(
        extracted_fields: list[ExtractedField],
        reviews_by_field: dict[UUID, list[ExtractedFieldReview]],
        document_version_id: UUID | None = None,
    ) -> dict[str, ResolvedField]:
        resolved: dict[str, ResolvedField] = {}

        for f in extracted_fields:
            reviews = reviews_by_field.get(f.extracted_field_id, [])
            rf = AuthoritativeFieldResolver._resolve_single_field(
                f, reviews, document_version_id
            )
            resolved[f.field_code] = rf

        return resolved

    @staticmethod
    def _resolve_single_field(
        f: ExtractedField,
        reviews: list[ExtractedFieldReview],
        document_version_id: UUID | None,
    ) -> ResolvedField:
        if not reviews:
            return ResolvedField(
                field_code=f.field_code,
                field_label=f.field_label,
                raw_value=f.raw_value,
                normalized_value=f.normalized_value,
                confidence=float(f.confidence) if f.confidence is not None else None,
                extracted_field_id=f.extracted_field_id,
                document_version_id=document_version_id,
                page_number=f.page_number,
                is_reviewed=False,
                review_count=0,
                is_disputed=False,
            )

        if len(reviews) == 1:
            rev = reviews[0]
            val = (
                f.normalized_value if rev.accepted_as_extracted else rev.corrected_value
            )
            return ResolvedField(
                field_code=f.field_code,
                field_label=f.field_label,
                raw_value=f.raw_value,
                normalized_value=val,
                confidence=float(f.confidence) if f.confidence is not None else None,
                extracted_field_id=f.extracted_field_id,
                document_version_id=document_version_id,
                page_number=f.page_number,
                is_reviewed=True,
                review_count=1,
                is_disputed=False,
            )

        # Multiple reviews exist: check for consensus across all decisions
        distinct_decisions: list[Any] = []
        for r in reviews:
            decided = (
                f.normalized_value if r.accepted_as_extracted else r.corrected_value
            )
            # Use JSON canonical representation for robust deep comparison
            serialized = json.dumps(decided, sort_keys=True, default=str)
            if serialized not in [
                json.dumps(d, sort_keys=True, default=str) for d in distinct_decisions
            ]:
                distinct_decisions.append(decided)

        if len(distinct_decisions) == 1:
            # All reviews agree on identical value (consensus)
            return ResolvedField(
                field_code=f.field_code,
                field_label=f.field_label,
                raw_value=f.raw_value,
                normalized_value=distinct_decisions[0],
                confidence=float(f.confidence) if f.confidence is not None else None,
                extracted_field_id=f.extracted_field_id,
                document_version_id=document_version_id,
                page_number=f.page_number,
                is_reviewed=True,
                review_count=len(reviews),
                is_disputed=False,
            )

        # DIVERGENT DECISIONS: STRICT PROHIBITION ON LATEST-WINS OR ROLE-PRIORITY!
        dispute_msg = (
            f"Field '{f.field_code}' has {len(reviews)} divergent review decisions recorded "
            f"across review roles ({len(distinct_decisions)} distinct candidate values). "
            f"Under regulatory integrity rules, conflicting human reviews cannot be resolved by "
            f"timestamp or role hierarchy. Independent committee resolution is required."
        )
        return ResolvedField(
            field_code=f.field_code,
            field_label=f.field_label,
            raw_value=f.raw_value,
            normalized_value=None,  # Do not choose a winner
            confidence=float(f.confidence) if f.confidence is not None else None,
            extracted_field_id=f.extracted_field_id,
            document_version_id=document_version_id,
            page_number=f.page_number,
            is_reviewed=True,
            review_count=len(reviews),
            is_disputed=True,
            dispute_reason=dispute_msg,
            conflicting_reviews=reviews,
        )

    @staticmethod
    def build_dispute_finding(rf: ResolvedField) -> FindingDraft:
        """Constructs an open CONTENT_ANOMALY finding linking all conflicting reviews."""
        evidence_items = []
        for rev in rf.conflicting_reviews:
            evidence_items.append(
                FindingEvidenceDraft(
                    document_version_id=rf.document_version_id,
                    extracted_field_id=rf.extracted_field_id,
                    evidence_type="EXTRACTED_FIELD_REVIEW",
                    evidence_reference=str(rev.extracted_field_review_id),
                    evidence_summary=(
                        f"Reviewer: {rev.reviewer_role} | "
                        f"Decision: {'ACCEPTED' if rev.accepted_as_extracted else 'CORRECTED'} | "
                        f"Value: {json.dumps(rev.corrected_value if not rev.accepted_as_extracted else rf.raw_value, default=str)} | "
                        f"Note: {rev.review_note or 'None'}"
                    ),
                )
            )

        return FindingDraft(
            category=FindingCategory.CONTENT_ANOMALY,
            severity=FindingSeverity.HIGH,
            title=f"Unresolved Auditor Review Dispute on Field '{rf.field_code}'",
            internal_reason=rf.dispute_reason
            or f"Contradictory review decisions exist for field '{rf.field_code}'.",
            recommended_action=(
                "Convene Audit Committee or designated Review Team Lead to review contradictory "
                "evidence entries and enter an official dispute determination."
            ),
            is_internal_only=True,
            status=FindingStatus.OPEN,
            evidence_items=evidence_items,
        )


class BaseRuleEvaluator(ABC):
    """Abstract base class for all Annexure 2.1 regulatory rule evaluators."""

    rule_code: str

    @abstractmethod
    def evaluate(self, ctx: RuleEvaluationContext) -> RuleEvaluationOutcome:
        """Evaluate the regulatory rule within the supplied execution context."""
        raise NotImplementedError

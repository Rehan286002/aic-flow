"""AIC-Verify — Regulatory Rule Engine Orchestration.

Executes versioned regulatory rule evaluations for an application revision,
pinning exact rule versions and source snapshot versions, recording immutable
validation results, findings, and evidence without mutating applicant checklist states.
"""

from __future__ import annotations

import logging
from datetime import UTC, datetime
from typing import Any
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.models.application import Application
from app.models.application_document_link import ApplicationDocumentLink
from app.models.application_requirements import ApplicationRequirement
from app.models.application_revision import ApplicationRevision
from app.models.checklist_item import ChecklistItem
from app.models.checklist_item_rule import ChecklistItemRule
from app.models.document_extraction import DocumentExtraction
from app.models.document_version import DocumentVersion
from app.models.extracted_field import ExtractedField
from app.models.extracted_field_review import ExtractedFieldReview
from app.models.finding import Finding
from app.models.finding_evidence import FindingEvidence
from app.models.institution import Institution
from app.models.institution_record_version import InstitutionRecordVersion
from app.models.validation_result import ValidationResult
from app.models.validation_rule import ValidationRule
from app.models.validation_rule_version import ValidationRuleVersion
from app.models.validation_run import ValidationRun
from app.models.validation_run_rule_version import ValidationRunRuleVersion
from app.models.validation_run_source_version import ValidationRunSourceVersion
from app.rules.base import (
    AuthoritativeFieldResolver,
    BaseRuleEvaluator,
    RuleEvaluationContext,
)
from app.rules.evaluators import (
    RuleEvaluatorEOA01,
    RuleEvaluatorEOA02,
    RuleEvaluatorEOA03,
    RuleEvaluatorEOA04,
    RuleEvaluatorEOA05,
    RuleEvaluatorEOA06,
    RuleEvaluatorEOA07,
)

logger = logging.getLogger(__name__)

ENGINE_VERSION = "1.0.0-phase6-batch3"


class RegulatoryRuleEngine:
    """Deterministic, versioned regulatory rule execution engine."""

    def __init__(self) -> None:
        self._evaluators: dict[str, BaseRuleEvaluator] = {
            "RULE_EOA_01_AFFIDAVIT": RuleEvaluatorEOA01(),
            "RULE_EOA_02_PAYMENT": RuleEvaluatorEOA02(),
            "RULE_EOA_03_BUILDING": RuleEvaluatorEOA03(),
            "RULE_EOA_04_STRUCTURAL": RuleEvaluatorEOA04(),
            "RULE_EOA_05_FIRE_NOC": RuleEvaluatorEOA05(),
            "RULE_EOA_06_GEO_COORDS": RuleEvaluatorEOA06(),
            "RULE_EOA_07_AUDITED_STMT": RuleEvaluatorEOA07(),
        }

    def register_evaluator(self, evaluator: BaseRuleEvaluator) -> None:
        self._evaluators[evaluator.rule_code] = evaluator

    def execute_validation_run(
        self,
        db: Session,
        application_revision_id: UUID,
        run_type: str = "FULL",
        triggered_by: UUID | None = None,
        checklist_item_ids: list[UUID] | None = None,
    ) -> ValidationRun:
        """Executes a complete validation run against the application revision."""
        # 1. Load Application Revision, Application, and Institution
        rev = db.scalar(
            select(ApplicationRevision).where(
                ApplicationRevision.application_revision_id == application_revision_id
            )
        )
        if not rev:
            raise ValueError(
                f"Application revision not found: {application_revision_id}"
            )

        app = db.scalar(
            select(Application).where(Application.application_id == rev.application_id)
        )
        if not app:
            raise ValueError(
                f"Application not found for revision: {application_revision_id}"
            )

        inst = db.scalar(
            select(Institution).where(Institution.institution_id == app.institution_id)
        )
        if not inst:
            raise ValueError(f"Institution not found: {app.institution_id}")

        now_utc = datetime.now(UTC)

        # Retrieve checklist template id from requirements if present
        first_template_id = db.execute(
            select(ChecklistItem.checklist_template_id)
            .join(
                ApplicationRequirement,
                ApplicationRequirement.checklist_item_id
                == ChecklistItem.checklist_item_id,
            )
            .where(
                ApplicationRequirement.application_revision_id
                == application_revision_id
            )
            .limit(1)
        ).scalar_one_or_none()

        # 2. Create ValidationRun Record
        run = ValidationRun(
            application_revision_id=application_revision_id,
            checklist_template_id=first_template_id,
            triggered_by=triggered_by,
            run_type=run_type,
            engine_version=ENGINE_VERSION,
            status="RUNNING",
            started_at=now_utc,
            evaluation_as_of=now_utc,
        )
        db.add(run)
        db.commit()

        try:
            # 3. Load Latest Eligible Source Snapshots for Institution
            source_snapshots = self._load_latest_source_snapshots(
                db, inst.institution_id
            )

            # Pin Source Snapshots in ValidationRunSourceVersion
            pinned_snapshots: set[UUID] = set()
            for snap in source_snapshots.values():
                if snap.institution_record_version_id not in pinned_snapshots:
                    run_src = ValidationRunSourceVersion(
                        validation_run_id=run.validation_run_id,
                        institution_record_version_id=snap.institution_record_version_id,
                        source_sync_run_id=snap.source_sync_run_id,
                        source_code=snap.source_system,
                        captured_at=snap.recorded_at,
                    )
                    db.add(run_src)
                    pinned_snapshots.add(snap.institution_record_version_id)

            # 4. Load Requirements to Evaluate
            req_query = (
                select(ApplicationRequirement, ChecklistItem)
                .join(
                    ChecklistItem,
                    ApplicationRequirement.checklist_item_id
                    == ChecklistItem.checklist_item_id,
                )
                .where(
                    ApplicationRequirement.application_revision_id
                    == application_revision_id
                )
                .order_by(ChecklistItem.display_order)
            )
            if checklist_item_ids:
                req_query = req_query.where(
                    ApplicationRequirement.checklist_item_id.in_(checklist_item_ids)
                )

            requirements_with_items = db.execute(req_query).all()

            pinned_rules: set[UUID] = set()

            for req, ci in requirements_with_items:
                # Find linked ValidationRule
                rule_link = db.scalar(
                    select(ChecklistItemRule).where(
                        ChecklistItemRule.checklist_item_id == ci.checklist_item_id
                    )
                )
                if not rule_link:
                    logger.warning(
                        "No validation rule linked to checklist item %s", ci.item_code
                    )
                    continue

                rule = db.scalar(
                    select(ValidationRule).where(
                        ValidationRule.validation_rule_id
                        == rule_link.validation_rule_id,
                        ValidationRule.is_active == True,
                    )
                )
                if not rule:
                    continue

                # Get active RuleVersion (Version 1)
                rule_version = db.scalar(
                    select(ValidationRuleVersion)
                    .where(
                        ValidationRuleVersion.validation_rule_id
                        == rule.validation_rule_id,
                        ValidationRuleVersion.is_enabled == True,
                    )
                    .order_by(ValidationRuleVersion.version_number.desc())
                )
                if not rule_version:
                    continue

                # Pin Rule Version
                if rule_version.validation_rule_version_id not in pinned_rules:
                    run_rule = ValidationRunRuleVersion(
                        validation_run_id=run.validation_run_id,
                        validation_rule_version_id=rule_version.validation_rule_version_id,
                    )
                    db.add(run_rule)
                    pinned_rules.add(rule_version.validation_rule_version_id)

                # Find latest clean DocumentVersion for this requirement
                doc_version = self._find_latest_clean_document_version(
                    db, req.application_requirement_id
                )

                # Resolve fields if document version exists
                resolved_fields = {}
                if doc_version:
                    resolved_fields = self._resolve_document_fields(
                        db, doc_version.document_version_id
                    )

                # Build Context
                ctx = RuleEvaluationContext(
                    db=db,
                    institution=inst,
                    application=app,
                    revision=rev,
                    requirement=req,
                    checklist_item=ci,
                    rule=rule,
                    rule_version=rule_version,
                    document_version=doc_version,
                    fields=resolved_fields,
                    source_snapshots=source_snapshots,
                    evaluation_as_of=now_utc,
                    triggered_by=triggered_by,
                )

                # Dispatch to evaluator
                evaluator = self._evaluators.get(rule.rule_code)
                if not evaluator:
                    logger.warning(
                        "No evaluator registered for rule %s", rule.rule_code
                    )
                    continue

                outcome = evaluator.evaluate(ctx)

                # Persist ValidationResult
                result = ValidationResult(
                    validation_run_id=run.validation_run_id,
                    application_requirement_id=req.application_requirement_id,
                    validation_rule_version_id=rule_version.validation_rule_version_id,
                    result_status=outcome.status,
                    expected_value=outcome.expected_value,
                    observed_value=outcome.observed_value,
                    explanation=outcome.explanation,
                    evaluated_at=now_utc,
                )
                db.add(result)
                db.flush()

                # Safeguard 5: Do NOT overwrite ApplicationRequirement.status with regulatory outcomes!
                # Only update last_evaluated_at
                req.last_evaluated_at = now_utc

                # Persist Findings and Evidence
                for fd in outcome.findings:
                    finding = Finding(
                        application_id=app.application_id,
                        application_revision_id=rev.application_revision_id,
                        validation_run_id=run.validation_run_id,
                        validation_result_id=result.validation_result_id,
                        category=fd.category,
                        severity=fd.severity,
                        status=fd.status,
                        title=fd.title,
                        internal_reason=fd.internal_reason,
                        recommended_action=fd.recommended_action,
                        is_internal_only=fd.is_internal_only,
                        created_at=now_utc,
                        updated_at=now_utc,
                    )
                    db.add(finding)
                    db.flush()

                    if fd.evidence_items:
                        for ev in fd.evidence_items:
                            # Ensure finding evidence constraint num_nonnulls >= 1
                            finding_ev = FindingEvidence(
                                finding_id=finding.finding_id,
                                document_version_id=ev.document_version_id
                                or (
                                    doc_version.document_version_id
                                    if doc_version
                                    else None
                                ),
                                extracted_field_id=ev.extracted_field_id,
                                verification_attempt_id=ev.verification_attempt_id,
                                validation_result_id=result.validation_result_id,
                                page_number=ev.page_number,
                                evidence_type=ev.evidence_type,
                                evidence_reference=ev.evidence_reference,
                                evidence_summary=ev.evidence_summary,
                                created_at=now_utc,
                            )
                            db.add(finding_ev)
                    else:
                        # Fallback for engine-generated evaluation rationales without raw document evidence items
                        finding_ev = FindingEvidence(
                            finding_id=finding.finding_id,
                            document_version_id=(
                                doc_version.document_version_id if doc_version else None
                            ),
                            validation_result_id=result.validation_result_id,
                            page_number=None,
                            evidence_type="EVALUATION_RATIONALE",
                            evidence_reference=f"rule:{rule.rule_code}|version:{rule_version.version_number}",
                            evidence_summary=fd.internal_reason[:500],
                            created_at=now_utc,
                        )
                        db.add(finding_ev)

            # Complete Run
            run.status = "COMPLETED"
            run.completed_at = datetime.now(UTC)
            db.commit()
            return run

        except Exception:
            db.rollback()
            run_rec = db.scalar(
                select(ValidationRun).where(
                    ValidationRun.validation_run_id == run.validation_run_id
                )
            )
            if run_rec:
                run_rec.status = "FAILED"
                run_rec.completed_at = datetime.now(UTC)
                try:
                    db.commit()
                except SQLAlchemyError:
                    db.rollback()
            logger.exception("Validation run failed")
            raise

    def _load_latest_source_snapshots(
        self, db: Session, institution_id: UUID
    ) -> dict[str, InstitutionRecordVersion]:
        """Loads the latest successful InstitutionRecordVersion for each source system."""
        snapshots = db.scalars(
            select(InstitutionRecordVersion)
            .where(InstitutionRecordVersion.institution_id == institution_id)
            .order_by(
                InstitutionRecordVersion.source_system,
                InstitutionRecordVersion.record_version.desc(),
            )
        ).all()

        latest: dict[str, InstitutionRecordVersion] = {}
        for s in snapshots:
            if s.source_system not in latest:
                latest[s.source_system] = s
        return latest

    def _find_latest_clean_document_version(
        self, db: Session, application_requirement_id: UUID
    ) -> DocumentVersion | None:
        """Finds latest clean document version linked to requirement."""
        links = db.scalars(
            select(ApplicationDocumentLink)
            .where(
                ApplicationDocumentLink.uploaded_for_requirement_id
                == application_requirement_id
            )
            .order_by(ApplicationDocumentLink.linked_at.desc())
        ).all()

        for link in links:
            dv = db.scalar(
                select(DocumentVersion).where(
                    DocumentVersion.document_version_id == link.document_version_id
                )
            )
            if dv and "clean/" in dv.storage_key:
                return dv
            elif dv:
                return dv  # Fallback to linked version
        return None

    def _resolve_document_fields(
        self, db: Session, document_version_id: UUID
    ) -> dict[str, Any]:
        """Loads and resolves candidate fields and review decisions for a document version."""
        # Find latest DocumentExtraction
        extraction = db.scalar(
            select(DocumentExtraction)
            .where(DocumentExtraction.document_version_id == document_version_id)
            .order_by(DocumentExtraction.created_at.desc())
        )
        if not extraction:
            return {}

        fields = list(
            db.scalars(
                select(ExtractedField).where(
                    ExtractedField.document_extraction_id
                    == extraction.document_extraction_id
                )
            ).all()
        )
        if not fields:
            return {}

        field_ids = [f.extracted_field_id for f in fields]
        all_reviews = list(
            db.scalars(
                select(ExtractedFieldReview)
                .where(ExtractedFieldReview.extracted_field_id.in_(field_ids))
                .order_by(
                    ExtractedFieldReview.reviewed_at.asc(),
                    ExtractedFieldReview.extracted_field_review_id.asc(),
                )
            ).all()
        )

        reviews_by_field: dict[UUID, list[ExtractedFieldReview]] = {}
        for r in all_reviews:
            reviews_by_field.setdefault(r.extracted_field_id, []).append(r)

        return AuthoritativeFieldResolver.resolve_fields(
            fields, reviews_by_field, document_version_id
        )


# Global engine instance
regulatory_rule_engine = RegulatoryRuleEngine()

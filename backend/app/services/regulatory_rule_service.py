"""AIC-Verify — Regulatory Rule Service.

High-level business service orchestrating validation runs, result retrieval,
finding externalization/sanitization, and audit logging.
"""

from __future__ import annotations

import logging
from datetime import UTC, datetime
from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy import desc, select
from sqlalchemy.orm import Session

from app.models.application import Application
from app.models.application_revision import ApplicationRevision
from app.models.enums import FindingCategory, FindingSeverity, FindingStatus
from app.models.finding import Finding
from app.models.finding_evidence import FindingEvidence
from app.models.user import User
from app.models.validation_result import ValidationResult
from app.models.validation_run import ValidationRun
from app.rules.engine import regulatory_rule_engine
from app.schemas.validation import (
    FindingEvidenceRead,
    FindingRead,
    FindingStatusUpdate,
    ValidationResultRead,
    ValidationRunCreate,
    ValidationRunRead,
    ValidationRunSummary,
)

logger = logging.getLogger(__name__)

# Permitted state transitions for auditor finding reviews
PERMITTED_FINDING_TRANSITIONS: dict[FindingStatus, set[FindingStatus]] = {
    FindingStatus.OPEN: {
        FindingStatus.ACCEPTED,
        FindingStatus.DISMISSED,
        FindingStatus.CLARIFICATION_REQUESTED,
        FindingStatus.ESCALATED,
    },
    FindingStatus.CLARIFICATION_REQUESTED: {
        FindingStatus.RESOLVED,
        FindingStatus.ACCEPTED,
        FindingStatus.DISMISSED,
        FindingStatus.ESCALATED,
    },
    FindingStatus.ESCALATED: {
        FindingStatus.ACCEPTED,
        FindingStatus.DISMISSED,
        FindingStatus.RESOLVED,
    },
    FindingStatus.ACCEPTED: {
        FindingStatus.RESOLVED,
        FindingStatus.ESCALATED,
    },
    FindingStatus.DISMISSED: {
        FindingStatus.OPEN,
    },
    FindingStatus.RESOLVED: {
        FindingStatus.OPEN,
        FindingStatus.ESCALATED,
    },
    FindingStatus.SUPERSEDED: set(),
}


class RegulatoryRuleService:
    """Service providing high-level validation execution and query workflows."""

    def __init__(self, engine=None) -> None:
        self.engine = engine or regulatory_rule_engine

    def trigger_validation_run(
        self,
        db: Session,
        institution_id: UUID,
        application_id: UUID,
        payload: ValidationRunCreate,
        current_user_id: UUID | None = None,
        is_internal_auditor: bool = False,
    ) -> ValidationRunRead:
        """Trigger a deterministic regulatory validation run on the active application revision."""
        app = db.scalar(
            select(Application).where(
                Application.application_id == application_id,
                Application.institution_id == institution_id,
            )
        )
        if not app:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Application {application_id} not found for institution {institution_id}",
            )

        # Get active revision (latest revision number)
        rev = db.scalar(
            select(ApplicationRevision)
            .where(ApplicationRevision.application_id == application_id)
            .order_by(desc(ApplicationRevision.revision_number))
        )
        if not rev:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Application has no active revision to validate",
            )

        run = self.engine.execute_validation_run(
            db=db,
            application_revision_id=rev.application_revision_id,
            run_type=payload.run_type,
            triggered_by=current_user_id,
            checklist_item_ids=payload.checklist_item_ids,
        )

        return self.get_validation_run(
            db=db,
            validation_run_id=run.validation_run_id,
            is_internal_auditor=is_internal_auditor,
        )

    def get_validation_run(
        self,
        db: Session,
        validation_run_id: UUID,
        is_internal_auditor: bool = False,
    ) -> ValidationRunRead:
        """Retrieve full details of a validation run, sanitizing internal observations for institution users."""
        run = db.scalar(
            select(ValidationRun).where(
                ValidationRun.validation_run_id == validation_run_id
            )
        )
        if not run:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Validation run {validation_run_id} not found",
            )

        # Load results
        results = list(
            db.scalars(
                select(ValidationResult)
                .where(ValidationResult.validation_run_id == validation_run_id)
                .order_by(ValidationResult.evaluated_at.asc())
            ).all()
        )

        # Load findings for this run
        findings = list(
            db.scalars(
                select(Finding)
                .where(Finding.validation_run_id == validation_run_id)
                .order_by(Finding.created_at.asc())
            ).all()
        )

        # Map findings by validation_result_id
        findings_by_result: dict[UUID, list[FindingRead]] = {}
        findings_by_sev: dict[str, int] = {}

        for f in findings:
            sev_str = f.severity.value
            findings_by_sev[sev_str] = findings_by_sev.get(sev_str, 0) + 1

            # Sanitize internal findings if user is an institution user
            if not is_internal_auditor and f.is_internal_only:
                continue

            # Load evidence
            evidence_rows = list(
                db.scalars(
                    select(FindingEvidence)
                    .where(FindingEvidence.finding_id == f.finding_id)
                    .order_by(FindingEvidence.created_at.asc())
                ).all()
            )
            evidence_reads = [
                FindingEvidenceRead.model_validate(ev) for ev in evidence_rows
            ]

            f_read = FindingRead(
                finding_id=f.finding_id,
                application_id=f.application_id,
                application_revision_id=f.application_revision_id,
                validation_run_id=f.validation_run_id,
                validation_result_id=f.validation_result_id,
                category=f.category,
                severity=f.severity,
                status=f.status,
                title=f.title,
                internal_reason=f.internal_reason if is_internal_auditor else None,
                recommended_action=f.recommended_action,
                is_internal_only=f.is_internal_only,
                created_at=f.created_at,
                updated_at=f.updated_at,
                evidence=evidence_reads,
            )

            if f.validation_result_id:
                findings_by_result.setdefault(f.validation_result_id, []).append(f_read)

        result_reads: list[ValidationResultRead] = []
        satisfied_count = 0
        deficient_count = 0
        not_applicable_count = 0
        unable_count = 0
        warning_count = 0

        for r in results:
            if r.result_status == "SATISFIED":
                satisfied_count += 1
            elif r.result_status == "DEFICIENT":
                deficient_count += 1
            elif r.result_status == "NOT_APPLICABLE":
                not_applicable_count += 1
            elif r.result_status == "UNABLE_TO_DETERMINE":
                unable_count += 1
            elif r.result_status == "WARNING":
                warning_count += 1

            r_findings = findings_by_result.get(r.validation_result_id, [])
            result_reads.append(
                ValidationResultRead(
                    validation_result_id=r.validation_result_id,
                    validation_run_id=r.validation_run_id,
                    application_requirement_id=r.application_requirement_id,
                    validation_rule_version_id=r.validation_rule_version_id,
                    result_status=r.result_status,
                    expected_value=r.expected_value,
                    observed_value=r.observed_value,
                    explanation=r.explanation,
                    evaluated_at=r.evaluated_at,
                    findings=r_findings,
                )
            )

        summary = ValidationRunSummary(
            validation_run_id=run.validation_run_id,
            status=run.status,
            run_type=run.run_type,
            engine_version=run.engine_version,
            started_at=run.started_at,
            completed_at=run.completed_at,
            total_results=len(result_reads),
            satisfied_count=satisfied_count,
            deficient_count=deficient_count,
            not_applicable_count=not_applicable_count,
            unable_to_determine_count=unable_count,
            warning_count=warning_count,
            findings_by_severity=findings_by_sev,
        )

        return ValidationRunRead(
            validation_run_id=run.validation_run_id,
            application_revision_id=run.application_revision_id,
            checklist_template_id=run.checklist_template_id,
            run_type=run.run_type,
            engine_version=run.engine_version,
            status=run.status,
            started_at=run.started_at,
            completed_at=run.completed_at,
            evaluation_as_of=run.evaluation_as_of,
            results=result_reads,
            summary=summary,
        )

    def list_application_validation_runs(
        self,
        db: Session,
        application_id: UUID,
    ) -> list[ValidationRunSummary]:
        """List summary history of validation runs for an application."""
        rev_ids = list(
            db.scalars(
                select(ApplicationRevision.application_revision_id).where(
                    ApplicationRevision.application_id == application_id
                )
            ).all()
        )
        if not rev_ids:
            return []

        runs = list(
            db.scalars(
                select(ValidationRun)
                .where(ValidationRun.application_revision_id.in_(rev_ids))
                .order_by(desc(ValidationRun.started_at))
            ).all()
        )

        summaries: list[ValidationRunSummary] = []
        for run in runs:
            # Query counts
            results = list(
                db.scalars(
                    select(ValidationResult).where(
                        ValidationResult.validation_run_id == run.validation_run_id
                    )
                ).all()
            )
            sat = sum(1 for r in results if r.result_status == "SATISFIED")
            defi = sum(1 for r in results if r.result_status == "DEFICIENT")
            na = sum(1 for r in results if r.result_status == "NOT_APPLICABLE")
            un = sum(1 for r in results if r.result_status == "UNABLE_TO_DETERMINE")
            warn = sum(1 for r in results if r.result_status == "WARNING")

            summaries.append(
                ValidationRunSummary(
                    validation_run_id=run.validation_run_id,
                    status=run.status,
                    run_type=run.run_type,
                    engine_version=run.engine_version,
                    started_at=run.started_at,
                    completed_at=run.completed_at,
                    total_results=len(results),
                    satisfied_count=sat,
                    deficient_count=defi,
                    not_applicable_count=na,
                    unable_to_determine_count=un,
                    warning_count=warn,
                )
            )

        return summaries

    def update_finding_status(
        self,
        db: Session,
        application_id: UUID,
        finding_id: UUID,
        payload: FindingStatusUpdate,
        current_user: User,
        reviewer_role: str,
    ) -> FindingRead:
        """Updates a finding status with mandatory auditor rationale and audit evidence recording."""
        finding = db.scalar(
            select(Finding).where(
                Finding.finding_id == finding_id,
                Finding.application_id == application_id,
            )
        )
        if not finding:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Finding {finding_id} not found for application {application_id}",
            )

        current_status = finding.status
        target_status = payload.status

        if current_status != target_status:
            permitted = PERMITTED_FINDING_TRANSITIONS.get(current_status, set())
            if target_status not in permitted:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=(
                        f"Invalid finding status transition from '{current_status.value}' to '{target_status.value}'. "
                        f"Permitted transitions from '{current_status.value}': {[s.value for s in permitted]}"
                    ),
                )

        now_utc = datetime.now(UTC)
        previous_status_val = finding.status.value
        finding.status = target_status
        finding.updated_at = now_utc

        # Append audit trail to internal_reason
        audit_note = (
            f"\n\n[AUDIT ACTION {now_utc.isoformat()}] Status changed from {previous_status_val} "
            f"to {target_status.value} by {current_user.email} ({reviewer_role}). Note: {payload.review_note}"
        )
        finding.internal_reason = (finding.internal_reason or "") + audit_note

        # Create audit FindingEvidence row
        audit_ev = FindingEvidence(
            finding_id=finding.finding_id,
            validation_result_id=finding.validation_result_id,
            document_version_id=None,
            page_number=None,
            evidence_type="AUDITOR_REVIEW_ACTION",
            evidence_reference=f"actor:{current_user.user_id}|role:{reviewer_role}|from:{previous_status_val}|to:{target_status.value}",
            evidence_summary=payload.review_note,
            created_at=now_utc,
        )
        db.add(audit_ev)
        db.commit()

        # Load all evidence for response
        evidence_rows = list(
            db.scalars(
                select(FindingEvidence)
                .where(FindingEvidence.finding_id == finding.finding_id)
                .order_by(FindingEvidence.created_at.asc())
            ).all()
        )
        evidence_reads = [
            FindingEvidenceRead.model_validate(ev) for ev in evidence_rows
        ]

        return FindingRead(
            finding_id=finding.finding_id,
            application_id=finding.application_id,
            application_revision_id=finding.application_revision_id,
            validation_run_id=finding.validation_run_id,
            validation_result_id=finding.validation_result_id,
            category=finding.category,
            severity=finding.severity,
            status=finding.status,
            title=finding.title,
            internal_reason=finding.internal_reason,  # Auditor sees full internal reason
            recommended_action=finding.recommended_action,
            is_internal_only=finding.is_internal_only,
            created_at=finding.created_at,
            updated_at=finding.updated_at,
            evidence=evidence_reads,
        )

    def list_application_findings(
        self,
        db: Session,
        application_id: UUID,
        is_internal_auditor: bool = False,
        validation_run_id: UUID | None = None,
        category: FindingCategory | None = None,
        severity: FindingSeverity | None = None,
        status_filter: FindingStatus | None = None,
        latest_run_only: bool = False,
    ) -> list[FindingRead]:
        """List findings for an application with role-based internal observation sanitization and query filters."""
        query = select(Finding).where(Finding.application_id == application_id)
        if not is_internal_auditor:
            query = query.where(Finding.is_internal_only == False)

        if validation_run_id:
            query = query.where(Finding.validation_run_id == validation_run_id)
        elif latest_run_only:
            latest_run_id = db.scalar(
                select(ValidationRun.validation_run_id)
                .join(
                    ApplicationRevision,
                    ValidationRun.application_revision_id
                    == ApplicationRevision.application_revision_id,
                )
                .where(
                    ApplicationRevision.application_id == application_id,
                    ValidationRun.status == "COMPLETED",
                )
                .order_by(desc(ValidationRun.started_at))
                .limit(1)
            )
            if latest_run_id:
                query = query.where(Finding.validation_run_id == latest_run_id)
            else:
                return []

        if category:
            query = query.where(Finding.category == category)
        if severity:
            query = query.where(Finding.severity == severity)
        if status_filter:
            query = query.where(Finding.status == status_filter)

        query = query.order_by(desc(Finding.created_at))

        findings = list(db.scalars(query).all())
        finding_reads: list[FindingRead] = []

        for f in findings:
            evidence_rows = list(
                db.scalars(
                    select(FindingEvidence)
                    .where(FindingEvidence.finding_id == f.finding_id)
                    .order_by(FindingEvidence.created_at.asc())
                ).all()
            )
            evidence_reads = [
                FindingEvidenceRead.model_validate(ev) for ev in evidence_rows
            ]

            finding_reads.append(
                FindingRead(
                    finding_id=f.finding_id,
                    application_id=f.application_id,
                    application_revision_id=f.application_revision_id,
                    validation_run_id=f.validation_run_id,
                    validation_result_id=f.validation_result_id,
                    category=f.category,
                    severity=f.severity,
                    status=f.status,
                    title=f.title,
                    internal_reason=f.internal_reason if is_internal_auditor else None,
                    recommended_action=f.recommended_action,
                    is_internal_only=f.is_internal_only,
                    created_at=f.created_at,
                    updated_at=f.updated_at,
                    evidence=evidence_reads,
                )
            )

        return finding_reads


regulatory_rule_service = RegulatoryRuleService()

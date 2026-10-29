"""AIC-Verify — Validation API Routes.

Provides endpoints to trigger and query regulatory rule validation runs,
results, and findings with strict Phase 2 RBAC case isolation:
- INSTITUTION_USER: Can view validation runs and externalized findings for their institution.
- AUDITOR / LEAD_AUDITOR: Can trigger validation runs and view full internal findings and evidence.
- ADMIN: Platform maintainer; strictly denied access to confidential institutional cases (HTTP 403).
"""

from __future__ import annotations

import logging
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import (
    get_active_role_assignments,
    get_current_user,
    get_db,
    verify_csrf,
)
from app.models.application import Application
from app.models.enums import FindingCategory, FindingSeverity, FindingStatus
from app.models.user import User
from app.schemas.validation import (
    FindingRead,
    FindingStatusUpdate,
    ValidationRunCreate,
    ValidationRunRead,
    ValidationRunSummary,
)
from app.services.regulatory_rule_service import regulatory_rule_service

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/institutions/{institution_id}/applications/{application_id}/validation",
    tags=["validation"],
)


def _check_case_access(
    institution_id: UUID,
    application_id: UUID,
    current_user: User,
    db: Session,
    require_auditor_to_execute: bool = False,
) -> bool:
    """Verifies that the current user has authorized access to this specific institutional case.

    Returns:
        is_internal_auditor (bool): True if user is accessing with AUDITOR / LEAD_AUDITOR scope.

    Raises:
        HTTPException(403): If user has no active assignment for this case (including ADMIN).
        HTTPException(404): If application does not exist for institution.
    """
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

    assignments = get_active_role_assignments(current_user, db)

    # 1. Check if user is an authorized Auditor / Lead Auditor
    auditor_assignment = next(
        (
            a
            for a in assignments
            if a.role_code in ["AUDITOR", "LEAD_AUDITOR"]
            and (
                app.review_team_id is None
                or a.review_team_id == app.review_team_id
                or a.review_team_id is not None
            )
        ),
        None,
    )
    if auditor_assignment:
        return True

    # 2. Check if user is the authorized Institution User
    inst_assignment = next(
        (
            a
            for a in assignments
            if a.role_code == "INSTITUTION_USER" and a.institution_id == institution_id
        ),
        None,
    )
    if inst_assignment:
        if require_auditor_to_execute:
            # If endpoint is restricted to auditors only
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Forbidden: Triggering regulatory audit validations requires AUDITOR or LEAD_AUDITOR role.",
            )
        return False

    # 3. Admins and unassigned users are strictly forbidden from case access
    raise HTTPException(
        status_code=status.HTTP_403_FORBIDDEN,
        detail="Forbidden: Case confidentiality rules deny access to unauthorized users and platform administrators.",
    )


@router.post(
    "/runs",
    response_model=ValidationRunRead,
    status_code=status.HTTP_201_CREATED,
    summary="Trigger regulatory validation run",
    description="Executes deterministic validation rules for the active application revision.",
)
def trigger_validation_run_endpoint(
    institution_id: UUID,
    application_id: UUID,
    payload: ValidationRunCreate,
    current_user: Annotated[User, Depends(get_current_user)],
    _csrf: Annotated[str, Depends(verify_csrf)],
    db: Annotated[Session, Depends(get_db)],
) -> ValidationRunRead:
    is_internal = _check_case_access(
        institution_id=institution_id,
        application_id=application_id,
        current_user=current_user,
        db=db,
        require_auditor_to_execute=False,  # Allow institution user pre-submission validation as well
    )

    return regulatory_rule_service.trigger_validation_run(
        db=db,
        institution_id=institution_id,
        application_id=application_id,
        payload=payload,
        current_user_id=current_user.user_id,
        is_internal_auditor=is_internal,
    )


@router.get(
    "/runs",
    response_model=list[ValidationRunSummary],
    status_code=status.HTTP_200_OK,
    summary="List validation runs",
    description="Returns chronological summary of all validation runs executed for the application.",
)
def list_validation_runs_endpoint(
    institution_id: UUID,
    application_id: UUID,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
) -> list[ValidationRunSummary]:
    _check_case_access(
        institution_id=institution_id,
        application_id=application_id,
        current_user=current_user,
        db=db,
    )

    return regulatory_rule_service.list_application_validation_runs(
        db=db,
        application_id=application_id,
    )


@router.get(
    "/runs/{validation_run_id}",
    response_model=ValidationRunRead,
    status_code=status.HTTP_200_OK,
    summary="Get validation run details",
    description="Returns full results, rules evaluated, and findings for a specific validation run.",
)
def get_validation_run_endpoint(
    institution_id: UUID,
    application_id: UUID,
    validation_run_id: UUID,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
) -> ValidationRunRead:
    is_internal = _check_case_access(
        institution_id=institution_id,
        application_id=application_id,
        current_user=current_user,
        db=db,
    )

    return regulatory_rule_service.get_validation_run(
        db=db,
        validation_run_id=validation_run_id,
        is_internal_auditor=is_internal,
    )


@router.get(
    "/findings",
    response_model=list[FindingRead],
    status_code=status.HTTP_200_OK,
    summary="List application findings",
    description="Returns findings for the active application with optional filters, sanitizing internal observations for institution users.",
)
def list_application_findings_endpoint(
    institution_id: UUID,
    application_id: UUID,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
    validation_run_id: UUID | None = None,
    category: FindingCategory | None = None,
    severity: FindingSeverity | None = None,
    finding_status: Annotated[FindingStatus | None, Query(alias="status")] = None,
    latest_run_only: bool = False,
) -> list[FindingRead]:
    is_internal = _check_case_access(
        institution_id=institution_id,
        application_id=application_id,
        current_user=current_user,
        db=db,
    )

    return regulatory_rule_service.list_application_findings(
        db=db,
        application_id=application_id,
        is_internal_auditor=is_internal,
        validation_run_id=validation_run_id,
        category=category,
        severity=severity,
        status_filter=finding_status,
        latest_run_only=latest_run_only,
    )


@router.patch(
    "/findings/{finding_id}",
    response_model=FindingRead,
    status_code=status.HTTP_200_OK,
    summary="Update finding review status",
    description="Allows authorized auditors to review, accept, dismiss, or escalate compliance findings with mandatory audit rationale.",
)
def update_finding_status_endpoint(
    institution_id: UUID,
    application_id: UUID,
    finding_id: UUID,
    payload: FindingStatusUpdate,
    current_user: Annotated[User, Depends(get_current_user)],
    _csrf: Annotated[str, Depends(verify_csrf)],
    db: Annotated[Session, Depends(get_db)],
) -> FindingRead:
    # Strictly enforce auditor role: Institution User and Admin forbidden (HTTP 403)
    _check_case_access(
        institution_id=institution_id,
        application_id=application_id,
        current_user=current_user,
        db=db,
        require_auditor_to_execute=True,
    )

    assignments = get_active_role_assignments(current_user, db)
    role_code = next(
        (
            a.role_code
            for a in assignments
            if a.role_code in ["AUDITOR", "LEAD_AUDITOR"]
        ),
        "AUDITOR",
    )

    return regulatory_rule_service.update_finding_status(
        db=db,
        application_id=application_id,
        finding_id=finding_id,
        payload=payload,
        current_user=current_user,
        reviewer_role=role_code,
    )

import uuid
from datetime import UTC, datetime
from typing import Annotated, Any

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import and_, false, or_, select
from sqlalchemy.orm import Session

from app.api.deps import get_active_role_assignments, get_current_user, get_db, verify_csrf
from app.models.application import Application
from app.models.application_document_link import ApplicationDocumentLink
from app.models.application_revision import ApplicationRevision
from app.models.document import Document
from app.models.document_security_scan import DocumentSecurityScan
from app.models.document_version import DocumentVersion
from app.models.compliance_obligation import ComplianceObligation
from app.models.in_app_notification import InAppNotification
from app.models.institution import Institution
from app.models.user import User
from app.models.review_team import ReviewTeam
from app.models.review_team_member import ReviewTeamMember
from app.models.enums import TeamRole
from app.models.workflow_case import WorkflowCase
from app.models.workflow_event import WorkflowEvent
from app.schemas.workflow import (
    ComplianceObligationActionRequest,
    ComplianceObligationCreateRequest,
    ComplianceObligationResponse,
    NotificationResponse,
    WorkflowCaseDetailResponse,
    WorkflowCaseListResponse,
    WorkflowEventCreateRequest,
    WorkflowEventResponse,
    WorkflowTransitionRequest,
    WorkflowTeamAssignmentRequest,
)
from app.services.application_service import get_application_detail
from app.services.workflow_service import (
    EVENT_ROLE_ALLOWLIST,
    add_workflow_event,
    case_access_context,
    institution_timeline_projection,
    create_obligation,
    list_case_obligations,
    transition_case,
    validate_operational_event,
)

router = APIRouter(prefix="/workflow", tags=["approval-workflow"])


def _contexts(user: User, db: Session) -> list[Any]:
    return get_active_role_assignments(user, db)


def _get_case(db: Session, workflow_case_id: uuid.UUID) -> tuple[WorkflowCase, Application]:
    case = db.get(WorkflowCase, workflow_case_id)
    if case is None:
        raise HTTPException(status_code=404, detail="Workflow case not found.")
    application = db.get(Application, case.application_id)
    if application is None:
        raise HTTPException(status_code=404, detail="Application record not found.")
    return case, application


def _require_case_access(db: Session, application: Application, user: User) -> Any:
    contexts = _contexts(user, db)
    case = db.scalar(select(WorkflowCase).where(WorkflowCase.application_id == application.application_id))
    return case_access_context(db, application, contexts, case=case, user_id=user.user_id)


def _to_list_item(db: Session, case: WorkflowCase, application: Application) -> WorkflowCaseListResponse:
    institution = db.get(Institution, application.institution_id)
    review_team = db.get(ReviewTeam, application.review_team_id) if application.review_team_id else None
    return WorkflowCaseListResponse(
        workflow_case_id=case.workflow_case_id,
        application_id=application.application_id,
        application_number=application.application_number,
        institution_id=application.institution_id,
        institution_name=institution.institution_name if institution else "Institution record unavailable",
        review_team_id=application.review_team_id,
        review_team_name=review_team.team_name if review_team else None,
        academic_year=application.academic_year,
        process_type=case.process_type,
        route_code=case.route_code,
        regulatory_version=case.regulatory_version,
        route_snapshot=case.route_snapshot or {},
        current_stage=case.current_stage,
        assigned_role_code=case.assigned_role_code,
        assigned_user_id=case.assigned_user_id,
        due_at=case.due_at,
        stage_entered_at=case.stage_entered_at,
        updated_at=case.updated_at,
    )



@router.get("/cases", response_model=list[WorkflowCaseListResponse])
def list_workflow_cases(
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
) -> list[WorkflowCaseListResponse]:
    contexts = _contexts(current_user, db)
    institution_ids = {c.institution_id for c in contexts if c.role_code == "INSTITUTION_USER" and c.institution_id}
    operational_contexts = [c for c in contexts if c.review_team_id]
    can_view_unassigned_intake = any(c.role_code == "INTAKE_OFFICER" for c in contexts)
    if not institution_ids and not operational_contexts and not can_view_unassigned_intake:
        raise HTTPException(status_code=403, detail="This account has no case-scoped workflow permission.")

    stmt = select(WorkflowCase, Application).join(Application, Application.application_id == WorkflowCase.application_id)
    scope_clauses = []
    if institution_ids:
        scope_clauses.append(Application.institution_id.in_(institution_ids))
    for context in operational_contexts:
        team_scope = Application.review_team_id == context.review_team_id
        is_supervisor = context.role_code in {"BUREAU_SUPERVISOR", "REGIONAL_OFFICER", "LEAD_AUDITOR"}
        if not is_supervisor:
            if context.role_code == "AUDITOR":
                stage_role_scope = WorkflowCase.assigned_role_code.in_(["INTAKE_OFFICER", "SCRUTINY_OFFICER"])
            elif context.role_code == "COMMITTEE_SECRETARIAT":
                stage_role_scope = or_(
                    WorkflowCase.assigned_role_code == context.role_code,
                    and_(
                        WorkflowCase.current_stage == "EVC_COMPLETED",
                        WorkflowCase.route_snapshot["requires_committee"].astext == "true",
                    ),
                )
            elif context.role_code == "EVC_COORDINATOR":
                stage_role_scope = or_(
                    WorkflowCase.assigned_role_code == context.role_code,
                    and_(
                        WorkflowCase.current_stage == "EVC_COMPLETED",
                        WorkflowCase.route_snapshot["requires_committee"].astext == "false",
                    ),
                    and_(
                        WorkflowCase.current_stage == "EVC_SCHEDULED",
                        WorkflowCase.route_snapshot["requires_evc"].astext == "true",
                    ),
                )
            else:
                stage_role_scope = WorkflowCase.assigned_role_code == context.role_code
            handoff_scope = false()
            if context.role_code == "COMMITTEE_SECRETARIAT":
                handoff_scope = and_(
                    WorkflowCase.current_stage == "EVC_COMPLETED",
                    WorkflowCase.route_snapshot["requires_committee"].astext == "true",
                )
            elif context.role_code == "EVC_COORDINATOR":
                handoff_scope = or_(
                    and_(
                        WorkflowCase.current_stage == "EVC_COMPLETED",
                        WorkflowCase.route_snapshot["requires_committee"].astext == "false",
                    ),
                    and_(
                        WorkflowCase.current_stage == "EVC_SCHEDULED",
                        WorkflowCase.route_snapshot["requires_evc"].astext == "true",
                    ),
                )
            team_scope = and_(
                team_scope,
                stage_role_scope,
                or_(
                    WorkflowCase.assigned_user_id.is_(None),
                    WorkflowCase.assigned_user_id == current_user.user_id,
                    handoff_scope,
                ),
            )
        scope_clauses.append(team_scope)
    if can_view_unassigned_intake:
        scope_clauses.append(and_(
            Application.review_team_id.is_(None),
            WorkflowCase.assigned_role_code == "INTAKE_OFFICER",
            or_(WorkflowCase.assigned_user_id.is_(None), WorkflowCase.assigned_user_id == current_user.user_id),
        ))
    stmt = stmt.where(or_(*scope_clauses)).order_by(WorkflowCase.updated_at.desc())
    rows = db.execute(stmt).all()
    responses: list[WorkflowCaseListResponse] = []
    for case, application in rows:
        response = _to_list_item(db, case, application)
        if application.institution_id in institution_ids:
            response = response.model_copy(update={
                "assigned_role_code": None,
                "assigned_user_id": None,
            })
        responses.append(response)
    return responses


@router.get("/cases/{workflow_case_id}", response_model=WorkflowCaseDetailResponse)
def get_workflow_case(
    workflow_case_id: uuid.UUID,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
) -> WorkflowCaseDetailResponse:
    case, application = _get_case(db, workflow_case_id)
    context = _require_case_access(db, application, current_user)
    base = _to_list_item(db, case, application)
    if context.role_code == "INSTITUTION_USER":
        base = base.model_copy(update={
            "assigned_role_code": None,
            "assigned_user_id": None,
        })
    events = list(db.scalars(select(WorkflowEvent).where(
        WorkflowEvent.workflow_case_id == case.workflow_case_id
    ).order_by(WorkflowEvent.occurred_at.asc())).all())
    if context.role_code == "INSTITUTION_USER":
        event_responses: list[WorkflowEventResponse] = []
        for event in events:
            projection = institution_timeline_projection(event)
            if projection is None:
                continue
            event_responses.append(WorkflowEventResponse(
                workflow_event_id=event.workflow_event_id,
                workflow_case_id=event.workflow_case_id,
                application_id=event.application_id,
                event_type=projection["event_type"],
                from_stage=projection["from_stage"],
                to_stage=projection["to_stage"],
                summary=projection["summary"],
                event_payload={},
                actor_user_id=None,
                occurred_at=event.occurred_at,
            ))
    else:
        event_responses = [WorkflowEventResponse.model_validate(item) for item in events]

    raw_obligations = list_case_obligations(db, case.workflow_case_id)
    if context.role_code == "INSTITUTION_USER":
        obligation_responses = [
            ComplianceObligationResponse.model_validate(item).model_copy(update={
                "verification_note": item.verification_note if item.status == "RETURNED" else None,
                "verified_by": None,
            })
            for item in raw_obligations
        ]
    else:
        obligation_responses = [ComplianceObligationResponse.model_validate(item) for item in raw_obligations]

    application_detail = get_application_detail(db, application.institution_id, application.application_id)
    return WorkflowCaseDetailResponse(
        **base.model_dump(),
        requirements=application_detail.requirements,
        events=event_responses,
        obligations=obligation_responses,
    )


@router.post("/cases/{workflow_case_id}/assign", response_model=WorkflowCaseDetailResponse)
def assign_workflow_case(
    workflow_case_id: uuid.UUID,
    payload: WorkflowTeamAssignmentRequest,
    current_user: Annotated[User, Depends(get_current_user)],
    _csrf: Annotated[str, Depends(verify_csrf)],
    db: Annotated[Session, Depends(get_db)],
) -> WorkflowCaseDetailResponse:
    case, application = _get_case(db, workflow_case_id)
    contexts = _contexts(current_user, db)
    intake_context = next((c for c in contexts if c.role_code in {"INTAKE_OFFICER", "AUDITOR", "BUREAU_SUPERVISOR"} and (c.review_team_id is not None or application.review_team_id is None)), None)
    if intake_context is None or (application.review_team_id is not None and intake_context.review_team_id != application.review_team_id):
        raise HTTPException(status_code=403, detail="Only an authorised intake or supervisory role may assign this case.")
    team = db.get(ReviewTeam, payload.review_team_id)
    if team is None or not team.is_active:
        raise HTTPException(status_code=404, detail="Active review team not found.")
    if intake_context.review_team_id and intake_context.review_team_id != payload.review_team_id and intake_context.role_code != "BUREAU_SUPERVISOR":
        raise HTTPException(status_code=403, detail="You may assign cases only to your authorised review team.")
    if payload.assigned_user_id:
        membership = db.scalar(select(ReviewTeamMember).where(
            ReviewTeamMember.review_team_id == payload.review_team_id,
            ReviewTeamMember.user_id == payload.assigned_user_id,
            ReviewTeamMember.is_active.is_(True),
            ReviewTeamMember.team_role == TeamRole(payload.assigned_role_code),
        ))
        if membership is None:
            raise HTTPException(status_code=422, detail="The selected officer is not an active member of this team with the requested role.")
    application.review_team_id = payload.review_team_id
    case.assigned_role_code = payload.assigned_role_code
    case.assigned_user_id = payload.assigned_user_id
    add_workflow_event(
        db, case, current_user.user_id, event_type="CASE_ASSIGNED",
        summary=payload.note, event_payload={
            "review_team_id": str(payload.review_team_id),
            "assigned_role_code": payload.assigned_role_code,
            "assigned_user_id": str(payload.assigned_user_id) if payload.assigned_user_id else None,
        },
    )
    db.commit()
    db.refresh(case)
    return get_workflow_case(workflow_case_id, current_user, db)


@router.post("/cases/{workflow_case_id}/transition", response_model=WorkflowCaseDetailResponse)
def transition_workflow_case(
    workflow_case_id: uuid.UUID,
    payload: WorkflowTransitionRequest,
    current_user: Annotated[User, Depends(get_current_user)],
    _csrf: Annotated[str, Depends(verify_csrf)],
    db: Annotated[Session, Depends(get_db)],
) -> WorkflowCaseDetailResponse:
    case, application = _get_case(db, workflow_case_id)
    context = _require_case_access(db, application, current_user)
    if payload.to_stage == "EVC_SCHEDULED":
        schedule_event = db.scalar(select(WorkflowEvent).where(
            WorkflowEvent.workflow_case_id == case.workflow_case_id,
            WorkflowEvent.event_type == "EVC_VISIT_SCHEDULED",
        ).limit(1))
        if schedule_event is None:
            raise HTTPException(status_code=409, detail="Record the EVC visit schedule before moving the case to the scheduled stage.")
    if payload.to_stage == "EVC_COMPLETED":
        report_event = db.scalar(select(WorkflowEvent).where(
            WorkflowEvent.workflow_case_id == case.workflow_case_id,
            WorkflowEvent.event_type == "EVC_REPORT_RECORDED",
        ).limit(1))
        if report_event is None:
            raise HTTPException(status_code=409, detail="Record the EVC visit report before completing the EVC stage.")
    if payload.to_stage == "AWAITING_AUTHORITY" and case.current_stage == "COMMITTEE_PROCEEDINGS":
        minutes_event = db.scalar(select(WorkflowEvent).where(
            WorkflowEvent.workflow_case_id == case.workflow_case_id,
            WorkflowEvent.event_type == "COMMITTEE_MINUTES_RECORDED",
        ).limit(1))
        if minutes_event is None:
            raise HTTPException(status_code=409, detail="Record the committee minutes before routing the case to the competent authority.")
    if payload.to_stage == "OBLIGATION_TRACKING" and case.current_stage == "APPROVED_WITH_CONDITIONS":
        first_condition = db.scalar(select(ComplianceObligation).where(
            ComplianceObligation.workflow_case_id == case.workflow_case_id,
        ).limit(1))
        if first_condition is None:
            raise HTTPException(status_code=409, detail="Record at least one binding approval condition before starting obligation tracking.")
    if payload.to_stage == "CLOSED" and case.current_stage == "OBLIGATION_TRACKING":
        open_obligations = db.scalar(select(ComplianceObligation).where(
            ComplianceObligation.workflow_case_id == case.workflow_case_id,
            ComplianceObligation.status != "CLOSED",
        ).limit(1))
        if open_obligations is not None:
            raise HTTPException(status_code=409, detail="All approval conditions must be verified and closed before the case can close.")
    if payload.to_stage in {"APPROVED", "APPROVED_WITH_CONDITIONS", "REJECTED", "ON_HOLD"}:
        decision_event = db.scalar(
            select(WorkflowEvent)
            .where(
                WorkflowEvent.workflow_case_id == case.workflow_case_id,
                WorkflowEvent.event_type == "DECISION_RECORDED",
            )
            .order_by(WorkflowEvent.occurred_at.desc())
            .limit(1)
        )
        if decision_event is None or (decision_event.event_payload or {}).get("outcome") != payload.to_stage:
            raise HTTPException(
                status_code=409,
                detail="Record the matching authorised decision, official order reference and date before changing the statutory outcome.",
            )
    transition_case(
        db,
        case,
        current_user.user_id,
        context.role_code,
        payload.to_stage,
        payload.reason,
        payload.due_at,
    )
    db.commit()
    db.refresh(case)
    return get_workflow_case(workflow_case_id, current_user, db)


@router.post("/cases/{workflow_case_id}/events", response_model=WorkflowEventResponse, status_code=status.HTTP_201_CREATED)
def create_case_event(
    workflow_case_id: uuid.UUID,
    payload: WorkflowEventCreateRequest,
    current_user: Annotated[User, Depends(get_current_user)],
    _csrf: Annotated[str, Depends(verify_csrf)],
    db: Annotated[Session, Depends(get_db)],
) -> WorkflowEventResponse:
    case, application = _get_case(db, workflow_case_id)
    context = _require_case_access(db, application, current_user)
    allowed_roles = EVENT_ROLE_ALLOWLIST.get(payload.event_type, set())
    if context.role_code not in allowed_roles:
        raise HTTPException(status_code=403, detail="This role cannot record the selected operational event.")
    validate_operational_event(case, payload.event_type)
    if payload.event_type == "COMMITTEE_MINUTES_RECORDED":
        convened_event = db.scalar(select(WorkflowEvent).where(
            WorkflowEvent.workflow_case_id == case.workflow_case_id,
            WorkflowEvent.event_type == "COMMITTEE_CONVENED",
        ).limit(1))
        if convened_event is None:
            raise HTTPException(status_code=409, detail="Record that the committee convened before recording its minutes.")
    if payload.event_type == "DECISION_RECORDED":
        decision = payload.event_payload
        if decision.get("outcome") not in {"APPROVED", "APPROVED_WITH_CONDITIONS", "REJECTED", "ON_HOLD"}:
            raise HTTPException(status_code=422, detail="A valid competent-authority outcome is required.")
        if not str(decision.get("official_order_reference", "")).strip() or not str(decision.get("decision_date", "")).strip():
            raise HTTPException(status_code=422, detail="The official order reference and decision date are required.")
    if payload.event_type in {"DOCUMENT_VALIDITY_RECORDED", "DOCUMENT_RENEWAL_SUBMITTED", "DOCUMENT_VALIDITY_CONFIRMED"}:
        document_data = payload.event_payload
        if not str(document_data.get("document_reference", "")).strip() or not str(document_data.get("valid_until", "")).strip():
            raise HTTPException(status_code=422, detail="A supporting document reference and valid-until date are required.")
        if not str(document_data.get("document_type", "")).strip():
            raise HTTPException(status_code=422, detail="A document type is required.")
    event = add_workflow_event(
        db,
        case,
        current_user.user_id,
        event_type=payload.event_type,
        summary=payload.summary,
        event_payload=payload.event_payload,
    )
    db.commit()
    db.refresh(event)
    return WorkflowEventResponse.model_validate(event)


@router.post("/cases/{workflow_case_id}/obligations", response_model=ComplianceObligationResponse, status_code=status.HTTP_201_CREATED)
def add_case_obligation(
    workflow_case_id: uuid.UUID,
    payload: ComplianceObligationCreateRequest,
    current_user: Annotated[User, Depends(get_current_user)],
    _csrf: Annotated[str, Depends(verify_csrf)],
    db: Annotated[Session, Depends(get_db)],
) -> ComplianceObligationResponse:
    case, application = _get_case(db, workflow_case_id)
    context = _require_case_access(db, application, current_user)
    if context.role_code != "COMPETENT_AUTHORITY":
        raise HTTPException(status_code=403, detail="Only the competent authority may register binding approval conditions.")
    obligation = create_obligation(
        db,
        case,
        current_user.user_id,
        title=payload.title,
        description=payload.description,
        source_condition=payload.source_condition,
        due_at=payload.due_at,
        condition_code=payload.condition_code,
    )
    db.commit()
    db.refresh(obligation)
    return ComplianceObligationResponse.model_validate(obligation)


@router.patch("/obligations/{obligation_id}", response_model=ComplianceObligationResponse)
def update_obligation(
    obligation_id: uuid.UUID,
    payload: ComplianceObligationActionRequest,
    current_user: Annotated[User, Depends(get_current_user)],
    _csrf: Annotated[str, Depends(verify_csrf)],
    db: Annotated[Session, Depends(get_db)],
) -> ComplianceObligationResponse:
    obligation = db.get(ComplianceObligation, obligation_id)
    if obligation is None:
        raise HTTPException(status_code=404, detail="Compliance obligation not found.")
    case, application = _get_case(db, obligation.workflow_case_id)
    context = _require_case_access(db, application, current_user)
    role = context.role_code
    now = datetime.now(UTC)

    if payload.action == "EVIDENCE_SUBMITTED":
        if role != "INSTITUTION_USER" or obligation.status not in {"OPEN", "RETURNED"}:
            raise HTTPException(status_code=403, detail="Only the institution may submit evidence for an open or returned condition.")
        if not payload.evidence_document_id and not payload.evidence_reference:
            raise HTTPException(status_code=422, detail="Provide an uploaded document or an evidence reference.")
        if payload.evidence_document_id:
            if application.current_revision_id is None:
                raise HTTPException(status_code=409, detail="The application has no current revision to associate submitted evidence with.")
            verified_link = db.scalar(
                select(DocumentVersion.document_version_id)
                .join(Document, Document.document_id == DocumentVersion.document_id)
                .join(ApplicationDocumentLink, ApplicationDocumentLink.document_version_id == DocumentVersion.document_version_id)
                .join(ApplicationRevision, ApplicationRevision.application_revision_id == ApplicationDocumentLink.application_revision_id)
                .join(DocumentSecurityScan, DocumentSecurityScan.document_version_id == DocumentVersion.document_version_id)
                .where(
                    Document.document_id == payload.evidence_document_id,
                    Document.institution_id == application.institution_id,
                    ApplicationRevision.application_id == application.application_id,
                    ApplicationRevision.application_revision_id == application.current_revision_id,
                    DocumentSecurityScan.scan_status == "CLEAN",
                )
                .limit(1)
            )
            if verified_link is None:
                raise HTTPException(
                    status_code=422,
                    detail="Evidence must be a clean-scanned document linked to this institution's current application revision.",
                )
        obligation.status = "EVIDENCE_SUBMITTED"
        obligation.evidence_document_id = payload.evidence_document_id
        obligation.evidence_reference = payload.evidence_reference
        obligation.submitted_at = now
        obligation.verification_note = payload.note
    elif payload.action == "START_VERIFICATION":
        if role not in {"SCRUTINY_OFFICER", "AUDITOR"} or obligation.status != "EVIDENCE_SUBMITTED":
            raise HTTPException(status_code=403, detail="Only an assigned scrutiny officer may start evidence verification.")
        obligation.status = "UNDER_VERIFICATION"
    elif payload.action == "VERIFY":
        if role not in {"SCRUTINY_OFFICER", "AUDITOR", "BUREAU_SUPERVISOR", "LEAD_AUDITOR"} or obligation.status not in {"EVIDENCE_SUBMITTED", "UNDER_VERIFICATION"}:
            raise HTTPException(status_code=403, detail="This role cannot verify the submitted condition evidence.")
        obligation.status = "VERIFIED"
        obligation.verified_by = current_user.user_id
        obligation.verified_at = now
        obligation.verification_note = payload.note
    elif payload.action == "RETURN":
        if role not in {"SCRUTINY_OFFICER", "AUDITOR", "BUREAU_SUPERVISOR", "LEAD_AUDITOR"} or obligation.status not in {"EVIDENCE_SUBMITTED", "UNDER_VERIFICATION"}:
            raise HTTPException(status_code=403, detail="This role cannot return the submitted condition evidence.")
        obligation.status = "RETURNED"
        obligation.verification_note = payload.note
    elif payload.action == "CLOSE":
        if role not in {"BUREAU_SUPERVISOR", "REGIONAL_OFFICER", "LEAD_AUDITOR"} or obligation.status != "VERIFIED":
            raise HTTPException(status_code=403, detail="Only supervisory roles may close a verified condition.")
        obligation.status = "CLOSED"
        obligation.verification_note = payload.note
    else:
        raise HTTPException(status_code=422, detail="Unsupported obligation action.")

    obligation.updated_at = now
    add_workflow_event(
        db,
        case,
        current_user.user_id,
        event_type=f"OBLIGATION_{payload.action}",
        summary=payload.note,
        event_payload={"obligation_id": str(obligation.obligation_id), "status": obligation.status},
    )
    db.commit()
    db.refresh(obligation)
    return ComplianceObligationResponse.model_validate(obligation)


@router.get("/obligations", response_model=list[ComplianceObligationResponse])
def list_obligations(
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
) -> list[ComplianceObligationResponse]:
    contexts = _contexts(current_user, db)
    institution_ids = {c.institution_id for c in contexts if c.role_code == "INSTITUTION_USER" and c.institution_id}
    operational_contexts = [c for c in contexts if c.review_team_id]
    if not institution_ids and not operational_contexts:
        raise HTTPException(status_code=403, detail="This account has no case-scoped compliance permission.")

    stmt = (
        select(ComplianceObligation, Application)
        .join(Application, Application.application_id == ComplianceObligation.application_id)
        .join(WorkflowCase, WorkflowCase.workflow_case_id == ComplianceObligation.workflow_case_id)
    )
    scope = []
    if institution_ids:
        scope.append(Application.institution_id.in_(institution_ids))
    for context in operational_contexts:
        team_scope = Application.review_team_id == context.review_team_id
        is_supervisor = context.role_code in {"BUREAU_SUPERVISOR", "REGIONAL_OFFICER", "LEAD_AUDITOR"}
        if not is_supervisor:
            role_match = (
                WorkflowCase.assigned_role_code.in_(["INTAKE_OFFICER", "SCRUTINY_OFFICER"])
                if context.role_code == "AUDITOR"
                else WorkflowCase.assigned_role_code == context.role_code
            )
            team_scope = and_(
                team_scope,
                role_match,
                or_(WorkflowCase.assigned_user_id.is_(None), WorkflowCase.assigned_user_id == current_user.user_id),
            )
        scope.append(team_scope)

    rows = db.execute(stmt.where(or_(*scope)).order_by(ComplianceObligation.due_at.asc())).all()
    institution_scope_ids = {context.institution_id for context in contexts if context.role_code == "INSTITUTION_USER" and context.institution_id}
    responses: list[ComplianceObligationResponse] = []
    for item, application in rows:
        response = ComplianceObligationResponse.model_validate(item)
        if application.institution_id in institution_scope_ids:
            response = response.model_copy(update={
                "verification_note": item.verification_note if item.status == "RETURNED" else None,
                "verified_by": None,
            })
        responses.append(response)
    return responses


@router.get("/notifications", response_model=list[NotificationResponse])
def list_notifications(
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
) -> list[NotificationResponse]:
    notifications = db.scalars(
        select(InAppNotification)
        .where(InAppNotification.recipient_user_id == current_user.user_id)
        .order_by(InAppNotification.created_at.desc())
        .limit(100)
    ).all()
    return [NotificationResponse.model_validate(item) for item in notifications]


@router.patch("/notifications/{notification_id}/read", response_model=NotificationResponse)
def mark_notification_read(
    notification_id: uuid.UUID,
    current_user: Annotated[User, Depends(get_current_user)],
    _csrf: Annotated[str, Depends(verify_csrf)],
    db: Annotated[Session, Depends(get_db)],
) -> NotificationResponse:
    notification = db.scalar(select(InAppNotification).where(
        InAppNotification.notification_id == notification_id,
        InAppNotification.recipient_user_id == current_user.user_id,
    ))
    if notification is None:
        raise HTTPException(status_code=404, detail="Notification not found.")
    if notification.read_at is None:
        notification.read_at = datetime.now(UTC)
        db.commit()
        db.refresh(notification)
    return NotificationResponse.model_validate(notification)

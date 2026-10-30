import uuid
from datetime import UTC, datetime
from typing import Annotated, Any

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, status
from fastapi.responses import FileResponse
from sqlalchemy import and_, func, or_, select
from sqlalchemy.orm import Session

from app.api.deps import get_active_role_assignments, get_current_user, get_db, verify_csrf
from app.models.application import Application
from app.models.application_requirements import ApplicationRequirement
from app.models.application_document_link import ApplicationDocumentLink
from app.models.application_revision import ApplicationRevision
from app.models.document import Document
from app.models.document_security_scan import DocumentSecurityScan
from app.models.document_version import DocumentVersion
from app.models.document_validity import DocumentValidityRecord
from app.models.compliance_obligation import ComplianceObligation
from app.models.evc_visit import EVCVisit
from app.models.executive_committee_decision import ExecutiveCommitteeDecision
from app.models.shc_proceeding import SHCProceeding
from app.models.sac_appeal import SACAppeal
from app.models.in_app_notification import InAppNotification
from app.models.institution import Institution
from app.models.user import User
from app.models.review_team import ReviewTeam
from app.models.review_team_member import ReviewTeamMember
from app.models.enums import TeamRole
from app.models.workflow_case import WorkflowCase
from app.models.workflow_event import WorkflowEvent
from app.models.workflow_reminder import WorkflowReminderPolicy
from app.schemas.document import DocumentUploadResponse
from app.schemas.workflow import (
    ComplianceObligationActionRequest,
    EVCVisitCancelRequest,
    EVCVisitReportRequest,
    EVCVisitResponse,
    EVCVisitScheduleRequest,
    ExecutiveCommitteeDecisionRequest,
    ExecutiveCommitteeDecisionResponse,
    SHCComplianceSubmissionRequest,
    SHCHearingRecordRequest,
    SHCHearingScheduleRequest,
    SHCProceedingResponse,
    SHCRecommendationRequest,
    SACAppealFileRequest,
    SACAppealResponse,
    SACHearingScheduleRequest,
    SACBureauObservationsRequest,
    SACHearingRecordRequest,
    SACRecommendationRequest,
    CouncilDecisionRequest,
    ComplianceObligationCreateRequest,
    ComplianceObligationResponse,
    NotificationResponse,
    WorkflowCaseDetailResponse,
    WorkflowCaseListResponse,
    WorkflowEventCreateRequest,
    WorkflowEventResponse,
    WorkflowTransitionRequest,
    WorkflowTeamAssignmentRequest,
    WorkflowReminderPolicyResponse,
    WorkflowReminderPolicyUpdateRequest,
    DocumentValidityResponse,
    DocumentValiditySubmitRequest,
    DocumentValidityReviewRequest,
)
from app.services.application_service import get_application_detail
from app.services.document_upload_service import document_upload_service
from app.services.document_validity_service import submit_document_validity, review_document_validity
from app.services.workflow_service import (
    EVENT_ROLE_ALLOWLIST,
    add_workflow_event,
    case_access_context,
    cancel_evc_visit,
    create_obligation,
    list_case_obligations,
    record_evc_visit_report,
    record_executive_committee_decision,
    schedule_evc_visit,
    record_shc_hearing,
    record_shc_recommendation,
    schedule_shc_hearing,
    submit_shc_compliance_reference,
    file_sac_appeal,
    schedule_sac_hearing,
    record_sac_bureau_observations,
    record_sac_hearing,
    record_sac_recommendation,
    record_council_appeal_decision,
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
    return WorkflowCaseListResponse(
        workflow_case_id=case.workflow_case_id,
        application_id=application.application_id,
        application_number=application.application_number,
        institution_id=application.institution_id,
        institution_name=institution.institution_name if institution else "Institution record unavailable",
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
            team_scope = and_(
                team_scope,
                or_(WorkflowCase.assigned_user_id.is_(None), WorkflowCase.assigned_user_id == current_user.user_id),
            )
        scope_clauses.append(team_scope)
    if can_view_unassigned_intake:
        scope_clauses.append(and_(Application.review_team_id.is_(None), or_(WorkflowCase.assigned_user_id.is_(None), WorkflowCase.assigned_user_id == current_user.user_id)))
    stmt = stmt.where(or_(*scope_clauses)).order_by(WorkflowCase.updated_at.desc())
    rows = db.execute(stmt).all()
    return [_to_list_item(db, case, application) for case, application in rows]


@router.get("/cases/{workflow_case_id}", response_model=WorkflowCaseDetailResponse)
def get_workflow_case(
    workflow_case_id: uuid.UUID,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
) -> WorkflowCaseDetailResponse:
    case, application = _get_case(db, workflow_case_id)
    _require_case_access(db, application, current_user)
    base = _to_list_item(db, case, application)
    events = list(db.scalars(select(WorkflowEvent).where(
        WorkflowEvent.workflow_case_id == case.workflow_case_id
    ).order_by(WorkflowEvent.occurred_at.asc())).all())
    obligations = list_case_obligations(db, case.workflow_case_id)
    evc_visit = db.scalar(select(EVCVisit).where(EVCVisit.workflow_case_id == case.workflow_case_id))
    shc_proceeding = db.scalar(select(SHCProceeding).where(SHCProceeding.workflow_case_id == case.workflow_case_id))
    ec_decision = db.scalar(select(ExecutiveCommitteeDecision).where(ExecutiveCommitteeDecision.workflow_case_id == case.workflow_case_id))
    sac_appeal = db.scalar(select(SACAppeal).where(SACAppeal.workflow_case_id == case.workflow_case_id))
    document_validity_records = list(db.scalars(
        select(DocumentValidityRecord)
        .where(DocumentValidityRecord.workflow_case_id == case.workflow_case_id)
        .order_by(DocumentValidityRecord.created_at.desc())
    ).all())
    application_detail = get_application_detail(db, application.institution_id, application.application_id)
    return WorkflowCaseDetailResponse(
        **base.model_dump(),
        requirements=application_detail.requirements,
        events=[WorkflowEventResponse.model_validate(item) for item in events],
        obligations=[ComplianceObligationResponse.model_validate(item) for item in obligations],
        evc_visit=EVCVisitResponse.model_validate(evc_visit) if evc_visit else None,
        shc_proceeding=SHCProceedingResponse.model_validate(shc_proceeding) if shc_proceeding else None,
        executive_committee_decision=ExecutiveCommitteeDecisionResponse.model_validate(ec_decision) if ec_decision else None,
        sac_appeal=SACAppealResponse.model_validate(sac_appeal) if sac_appeal else None,
        document_validity_records=[DocumentValidityResponse.model_validate(item) for item in document_validity_records],
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
    if case.current_stage == "AWAITING_AUTHORITY" and payload.to_stage in {"APPROVED", "APPROVED_WITH_CONDITIONS", "REJECTED"}:
        raise HTTPException(status_code=409, detail="Record the Executive Committee decision and Speaking Order before changing the statutory outcome.")
    if payload.to_stage == "EVC_SCHEDULED":
        evc_visit = db.scalar(select(EVCVisit).where(
            EVCVisit.workflow_case_id == case.workflow_case_id,
        ))
        if evc_visit is None or evc_visit.status != "SCHEDULED":
            raise HTTPException(status_code=409, detail="Enter the structured EVC visit schedule before moving the case to the scheduled stage.")
    if payload.to_stage == "EVC_COMPLETED":
        evc_visit = db.scalar(select(EVCVisit).where(
            EVCVisit.workflow_case_id == case.workflow_case_id,
        ))
        if evc_visit is None or evc_visit.status != "COMPLETED":
            raise HTTPException(status_code=409, detail="Record the EVC visit report before completing the EVC stage.")
    if payload.to_stage == "AWAITING_AUTHORITY" and case.current_stage == "COMMITTEE_PROCEEDINGS":
        shc_proceeding = db.scalar(select(SHCProceeding).where(
            SHCProceeding.workflow_case_id == case.workflow_case_id,
        ))
        if shc_proceeding is None or shc_proceeding.status != "RECOMMENDATION_RECORDED":
            raise HTTPException(status_code=409, detail="Record the SHC hearing and recommendation before routing the case to the Executive Committee decision stage.")
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


@router.post("/cases/{workflow_case_id}/executive-committee-decision", response_model=WorkflowCaseDetailResponse)
def record_executive_committee_decision_endpoint(
    workflow_case_id: uuid.UUID,
    payload: ExecutiveCommitteeDecisionRequest,
    current_user: Annotated[User, Depends(get_current_user)],
    _csrf: Annotated[str, Depends(verify_csrf)],
    db: Annotated[Session, Depends(get_db)],
) -> WorkflowCaseDetailResponse:
    case, application = _get_case(db, workflow_case_id)
    context = _require_case_access(db, application, current_user)
    if context.role_code != "COMPETENT_AUTHORITY":
        raise HTTPException(status_code=403, detail="Only the authorised Competent Authority may record this decision.")
    record_executive_committee_decision(
        db,
        case,
        current_user.user_id,
        context.role_code,
        outcome_code=payload.outcome_code,
        decision_reference=payload.decision_reference,
        decision_reasons=payload.decision_reasons,
        speaking_order_reference=payload.speaking_order_reference,
        speaking_order_uploaded_at=payload.speaking_order_uploaded_at,
    )
    db.commit()
    db.refresh(case)
    return get_workflow_case(workflow_case_id, current_user, db)


@router.post("/cases/{workflow_case_id}/sac-appeal", response_model=SACAppealResponse, status_code=status.HTTP_201_CREATED)
def file_sac_appeal_endpoint(
    workflow_case_id: uuid.UUID,
    payload: SACAppealFileRequest,
    current_user: Annotated[User, Depends(get_current_user)],
    _csrf: Annotated[str, Depends(verify_csrf)],
    db: Annotated[Session, Depends(get_db)],
) -> SACAppealResponse:
    case, application = _get_case(db, workflow_case_id)
    context = _require_case_access(db, application, current_user)
    if context.role_code != "INSTITUTION_USER":
        raise HTTPException(status_code=403, detail="Only the institution applicant may file an appeal against its Executive Committee decision.")
    appeal = file_sac_appeal(
        db,
        case,
        current_user.user_id,
        appeal_reference=payload.appeal_reference,
        appeal_grounds=payload.appeal_grounds,
        supporting_material_reference=payload.supporting_material_reference,
    )
    db.commit()
    db.refresh(appeal)
    return SACAppealResponse.model_validate(appeal)


@router.post("/sac-appeals/{sac_appeal_id}/schedule", response_model=SACAppealResponse)
def schedule_sac_appeal_hearing_endpoint(
    sac_appeal_id: uuid.UUID,
    payload: SACHearingScheduleRequest,
    current_user: Annotated[User, Depends(get_current_user)],
    _csrf: Annotated[str, Depends(verify_csrf)],
    db: Annotated[Session, Depends(get_db)],
) -> SACAppealResponse:
    appeal = db.get(SACAppeal, sac_appeal_id)
    if appeal is None:
        raise HTTPException(status_code=404, detail="SAC appeal record not found.")
    case, application = _get_case(db, appeal.workflow_case_id)
    context = _require_case_access(db, application, current_user)
    updated = schedule_sac_hearing(
        db, case, appeal, current_user.user_id, context.role_code,
        hearing_mode=payload.hearing_mode,
        hearing_scheduled_at=payload.hearing_scheduled_at,
        hearing_details=payload.hearing_details,
        official_schedule_reference=payload.official_schedule_reference,
    )
    db.commit()
    db.refresh(updated)
    return SACAppealResponse.model_validate(updated)


@router.post("/sac-appeals/{sac_appeal_id}/bureau-observations", response_model=SACAppealResponse)
def record_sac_bureau_observations_endpoint(
    sac_appeal_id: uuid.UUID,
    payload: SACBureauObservationsRequest,
    current_user: Annotated[User, Depends(get_current_user)],
    _csrf: Annotated[str, Depends(verify_csrf)],
    db: Annotated[Session, Depends(get_db)],
) -> SACAppealResponse:
    appeal = db.get(SACAppeal, sac_appeal_id)
    if appeal is None:
        raise HTTPException(status_code=404, detail="SAC appeal record not found.")
    case, application = _get_case(db, appeal.workflow_case_id)
    context = _require_case_access(db, application, current_user)
    updated = record_sac_bureau_observations(
        db, case, appeal, current_user.user_id, context.role_code,
        observation_reference=payload.observation_reference,
        observations=payload.observations,
    )
    db.commit()
    db.refresh(updated)
    return SACAppealResponse.model_validate(updated)


@router.post("/sac-appeals/{sac_appeal_id}/hearing", response_model=SACAppealResponse)
def record_sac_hearing_endpoint(
    sac_appeal_id: uuid.UUID,
    payload: SACHearingRecordRequest,
    current_user: Annotated[User, Depends(get_current_user)],
    _csrf: Annotated[str, Depends(verify_csrf)],
    db: Annotated[Session, Depends(get_db)],
) -> SACAppealResponse:
    appeal = db.get(SACAppeal, sac_appeal_id)
    if appeal is None:
        raise HTTPException(status_code=404, detail="SAC appeal record not found.")
    case, application = _get_case(db, appeal.workflow_case_id)
    context = _require_case_access(db, application, current_user)
    updated = record_sac_hearing(
        db, case, appeal, current_user.user_id, context.role_code,
        representative_one_name=payload.representative_one_name,
        representative_one_designation=payload.representative_one_designation,
        representative_one_id_reference=payload.representative_one_id_reference,
        representative_two_name=payload.representative_two_name,
        representative_two_designation=payload.representative_two_designation,
        representative_two_id_reference=payload.representative_two_id_reference,
        hearing_summary=payload.hearing_summary,
    )
    db.commit()
    db.refresh(updated)
    return SACAppealResponse.model_validate(updated)


@router.post("/sac-appeals/{sac_appeal_id}/recommendation", response_model=SACAppealResponse)
def record_sac_recommendation_endpoint(
    sac_appeal_id: uuid.UUID,
    payload: SACRecommendationRequest,
    current_user: Annotated[User, Depends(get_current_user)],
    _csrf: Annotated[str, Depends(verify_csrf)],
    db: Annotated[Session, Depends(get_db)],
) -> SACAppealResponse:
    appeal = db.get(SACAppeal, sac_appeal_id)
    if appeal is None:
        raise HTTPException(status_code=404, detail="SAC appeal record not found.")
    case, application = _get_case(db, appeal.workflow_case_id)
    context = _require_case_access(db, application, current_user)
    updated = record_sac_recommendation(
        db, case, appeal, current_user.user_id, context.role_code,
        recommendation_code=payload.recommendation_code,
        recommendation_text=payload.recommendation_text,
        recommendation_reference=payload.recommendation_reference,
    )
    db.commit()
    db.refresh(updated)
    return SACAppealResponse.model_validate(updated)


@router.post("/sac-appeals/{sac_appeal_id}/council-decision", response_model=SACAppealResponse)
def record_council_appeal_decision_endpoint(
    sac_appeal_id: uuid.UUID,
    payload: CouncilDecisionRequest,
    current_user: Annotated[User, Depends(get_current_user)],
    _csrf: Annotated[str, Depends(verify_csrf)],
    db: Annotated[Session, Depends(get_db)],
) -> SACAppealResponse:
    appeal = db.get(SACAppeal, sac_appeal_id)
    if appeal is None:
        raise HTTPException(status_code=404, detail="SAC appeal record not found.")
    case, application = _get_case(db, appeal.workflow_case_id)
    context = _require_case_access(db, application, current_user)
    updated = record_council_appeal_decision(
        db, case, appeal, current_user.user_id, context.role_code,
        outcome_code=payload.outcome_code,
        decision_reference=payload.decision_reference,
        decision_text=payload.decision_text,
        decision_uploaded_at=payload.decision_uploaded_at,
    )
    db.commit()
    db.refresh(updated)
    return SACAppealResponse.model_validate(updated)


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


@router.post("/cases/{workflow_case_id}/evc-visit", response_model=EVCVisitResponse)
def schedule_or_reschedule_evc_visit(
    workflow_case_id: uuid.UUID,
    payload: EVCVisitScheduleRequest,
    current_user: Annotated[User, Depends(get_current_user)],
    _csrf: Annotated[str, Depends(verify_csrf)],
    db: Annotated[Session, Depends(get_db)],
) -> EVCVisitResponse:
    case, application = _get_case(db, workflow_case_id)
    context = _require_case_access(db, application, current_user)
    if context.role_code not in {"EVC_COORDINATOR", "REGIONAL_OFFICER", "LEAD_AUDITOR"}:
        raise HTTPException(status_code=403, detail="Only authorised EVC coordination or supervisory roles may schedule this visit.")
    visit = schedule_evc_visit(
        db,
        case,
        current_user.user_id,
        visit_mode=payload.visit_mode,
        scheduled_start_at=payload.scheduled_start_at,
        scheduled_end_at=payload.scheduled_end_at,
        venue_or_meeting_details=payload.venue_or_meeting_details,
        official_schedule_reference=payload.official_schedule_reference,
        institution_contact_name=payload.institution_contact_name,
        institution_contact_email=payload.institution_contact_email,
        coordination_note=payload.coordination_note,
    )
    db.commit()
    db.refresh(visit)
    return EVCVisitResponse.model_validate(visit)


@router.post("/evc-visits/{evc_visit_id}/report", response_model=EVCVisitResponse)
def submit_evc_visit_report(
    evc_visit_id: uuid.UUID,
    payload: EVCVisitReportRequest,
    current_user: Annotated[User, Depends(get_current_user)],
    _csrf: Annotated[str, Depends(verify_csrf)],
    db: Annotated[Session, Depends(get_db)],
) -> EVCVisitResponse:
    visit = db.get(EVCVisit, evc_visit_id)
    if visit is None:
        raise HTTPException(status_code=404, detail="EVC visit record not found.")
    case, application = _get_case(db, visit.workflow_case_id)
    context = _require_case_access(db, application, current_user)
    if context.role_code not in {"EVC_COORDINATOR", "EVC_MEMBER"}:
        raise HTTPException(status_code=403, detail="Only an authorised EVC participant may record the visit report.")
    updated = record_evc_visit_report(
        db,
        case,
        visit,
        current_user.user_id,
        report_reference=payload.report_reference,
        report_summary=payload.report_summary,
        report_outcome=payload.report_outcome,
        note=payload.note,
    )
    db.commit()
    db.refresh(updated)
    return EVCVisitResponse.model_validate(updated)


@router.post("/evc-visits/{evc_visit_id}/cancel", response_model=EVCVisitResponse)
def cancel_scheduled_evc_visit(
    evc_visit_id: uuid.UUID,
    payload: EVCVisitCancelRequest,
    current_user: Annotated[User, Depends(get_current_user)],
    _csrf: Annotated[str, Depends(verify_csrf)],
    db: Annotated[Session, Depends(get_db)],
) -> EVCVisitResponse:
    visit = db.get(EVCVisit, evc_visit_id)
    if visit is None:
        raise HTTPException(status_code=404, detail="EVC visit record not found.")
    case, application = _get_case(db, visit.workflow_case_id)
    context = _require_case_access(db, application, current_user)
    if context.role_code not in {"EVC_COORDINATOR", "REGIONAL_OFFICER", "LEAD_AUDITOR"}:
        raise HTTPException(status_code=403, detail="Only authorised EVC coordination or supervisory roles may cancel this visit.")
    updated = cancel_evc_visit(db, case, visit, current_user.user_id, payload.reason)
    db.commit()
    db.refresh(updated)
    return EVCVisitResponse.model_validate(updated)


@router.post("/cases/{workflow_case_id}/shc-proceeding/schedule", response_model=SHCProceedingResponse)
def schedule_shc_hearing_endpoint(
    workflow_case_id: uuid.UUID,
    payload: SHCHearingScheduleRequest,
    current_user: Annotated[User, Depends(get_current_user)],
    _csrf: Annotated[str, Depends(verify_csrf)],
    db: Annotated[Session, Depends(get_db)],
) -> SHCProceedingResponse:
    case, application = _get_case(db, workflow_case_id)
    context = _require_case_access(db, application, current_user)
    if context.role_code != "COMMITTEE_SECRETARIAT":
        raise HTTPException(status_code=403, detail="Only the authorised SHC secretariat may record hearing schedule details.")
    proceeding = schedule_shc_hearing(
        db,
        case,
        current_user.user_id,
        hearing_mode=payload.hearing_mode,
        hearing_scheduled_at=payload.hearing_scheduled_at,
        hearing_details=payload.hearing_details,
        notice_reference=payload.notice_reference,
        official_schedule_reference=payload.official_schedule_reference,
    )
    db.commit()
    db.refresh(proceeding)
    return SHCProceedingResponse.model_validate(proceeding)


@router.post("/shc-proceedings/{shc_proceeding_id}/compliance-submission", response_model=SHCProceedingResponse)
def submit_shc_compliance_endpoint(
    shc_proceeding_id: uuid.UUID,
    payload: SHCComplianceSubmissionRequest,
    current_user: Annotated[User, Depends(get_current_user)],
    _csrf: Annotated[str, Depends(verify_csrf)],
    db: Annotated[Session, Depends(get_db)],
) -> SHCProceedingResponse:
    proceeding = db.get(SHCProceeding, shc_proceeding_id)
    if proceeding is None:
        raise HTTPException(status_code=404, detail="SHC proceeding record not found.")
    case, application = _get_case(db, proceeding.workflow_case_id)
    context = _require_case_access(db, application, current_user)
    if context.role_code != "INSTITUTION_USER":
        raise HTTPException(status_code=403, detail="Only the institution may submit compliance material for its SHC hearing.")
    updated = submit_shc_compliance_reference(
        db,
        case,
        proceeding,
        current_user.user_id,
        submission_reference=payload.submission_reference,
        note=payload.note,
    )
    db.commit()
    db.refresh(updated)
    return SHCProceedingResponse.model_validate(updated)


@router.post("/shc-proceedings/{shc_proceeding_id}/hearing", response_model=SHCProceedingResponse)
def record_shc_hearing_endpoint(
    shc_proceeding_id: uuid.UUID,
    payload: SHCHearingRecordRequest,
    current_user: Annotated[User, Depends(get_current_user)],
    _csrf: Annotated[str, Depends(verify_csrf)],
    db: Annotated[Session, Depends(get_db)],
) -> SHCProceedingResponse:
    proceeding = db.get(SHCProceeding, shc_proceeding_id)
    if proceeding is None:
        raise HTTPException(status_code=404, detail="SHC proceeding record not found.")
    case, application = _get_case(db, proceeding.workflow_case_id)
    context = _require_case_access(db, application, current_user)
    if context.role_code != "COMMITTEE_SECRETARIAT":
        raise HTTPException(status_code=403, detail="Only the authorised SHC secretariat may record the hearing.")
    updated = record_shc_hearing(
        db,
        case,
        proceeding,
        current_user.user_id,
        representative_one_name=payload.representative_one_name,
        representative_one_designation=payload.representative_one_designation,
        representative_two_name=payload.representative_two_name,
        representative_two_designation=payload.representative_two_designation,
        hearing_summary=payload.hearing_summary,
        note=payload.note,
    )
    db.commit()
    db.refresh(updated)
    return SHCProceedingResponse.model_validate(updated)


@router.post("/shc-proceedings/{shc_proceeding_id}/recommendation", response_model=SHCProceedingResponse)
def record_shc_recommendation_endpoint(
    shc_proceeding_id: uuid.UUID,
    payload: SHCRecommendationRequest,
    current_user: Annotated[User, Depends(get_current_user)],
    _csrf: Annotated[str, Depends(verify_csrf)],
    db: Annotated[Session, Depends(get_db)],
) -> SHCProceedingResponse:
    proceeding = db.get(SHCProceeding, shc_proceeding_id)
    if proceeding is None:
        raise HTTPException(status_code=404, detail="SHC proceeding record not found.")
    case, application = _get_case(db, proceeding.workflow_case_id)
    context = _require_case_access(db, application, current_user)
    if context.role_code != "COMMITTEE_SECRETARIAT":
        raise HTTPException(status_code=403, detail="Only the authorised SHC secretariat may record its recommendation.")
    updated = record_shc_recommendation(
        db,
        case,
        proceeding,
        current_user.user_id,
        recommendation_code=payload.recommendation_code,
        recommendation_text=payload.recommendation_text,
        recommendation_reference=payload.recommendation_reference,
    )
    db.commit()
    db.refresh(updated)
    return SHCProceedingResponse.model_validate(updated)


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
        if not payload.evidence_document_version_id and not payload.evidence_document_id and not payload.evidence_reference:
            raise HTTPException(status_code=422, detail="Provide an uploaded document or an evidence reference.")
        if payload.evidence_document_version_id:
            if application.current_revision_id is None:
                raise HTTPException(status_code=409, detail="The application has no current revision to associate submitted evidence with.")
            latest_scan_status = (
                select(DocumentSecurityScan.scan_status)
                .where(DocumentSecurityScan.document_version_id == DocumentVersion.document_version_id)
                .order_by(DocumentSecurityScan.scanned_at.desc())
                .limit(1)
                .scalar_subquery()
            )
            latest_version_number = (
                select(func.max(DocumentVersion.version_number))
                .where(DocumentVersion.document_id == Document.document_id)
                .scalar_subquery()
            )
            verified_link = db.execute(
                select(
                    DocumentVersion.document_id,
                    DocumentVersion.document_version_id,
                    ApplicationDocumentLink.uploaded_for_requirement_id,
                )
                .join(Document, Document.document_id == DocumentVersion.document_id)
                .join(ApplicationDocumentLink, ApplicationDocumentLink.document_version_id == DocumentVersion.document_version_id)
                .join(ApplicationRevision, ApplicationRevision.application_revision_id == ApplicationDocumentLink.application_revision_id)
                .where(
                    DocumentVersion.document_version_id == payload.evidence_document_version_id,
                    Document.institution_id == application.institution_id,
                    ApplicationRevision.application_id == application.application_id,
                    ApplicationRevision.application_revision_id == application.current_revision_id,
                    DocumentVersion.version_number == latest_version_number,
                    latest_scan_status == "CLEAN",
                )
                .limit(1)
            ).first()
            if verified_link is None or verified_link.uploaded_for_requirement_id is None:
                raise HTTPException(
                    status_code=422,
                    detail="Evidence must be the latest clean-scanned version linked to a requirement on this institution's current application revision.",
                )
            obligation.evidence_document_id = verified_link.document_id
            obligation.evidence_document_version_id = verified_link.document_version_id
            obligation.evidence_requirement_id = verified_link.uploaded_for_requirement_id
        elif payload.evidence_document_id:
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
            obligation.evidence_document_id = payload.evidence_document_id
            obligation.evidence_document_version_id = None
            obligation.evidence_requirement_id = None
        else:
            obligation.evidence_document_id = None
            obligation.evidence_document_version_id = None
            obligation.evidence_requirement_id = None
        obligation.status = "EVIDENCE_SUBMITTED"
        obligation.evidence_reference = payload.evidence_reference
        obligation.submitted_at = now
        obligation.verification_note = payload.note
    elif payload.action == "START_VERIFICATION":
        if role not in {"SCRUTINY_OFFICER", "AUDITOR"} or obligation.status != "EVIDENCE_SUBMITTED":
            raise HTTPException(status_code=403, detail="Only an assigned scrutiny officer may start evidence verification.")
        obligation.status = "UNDER_VERIFICATION"
        obligation.verification_note = payload.note
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
        event_payload={
            "obligation_id": str(obligation.obligation_id),
            "status": obligation.status,
            "evidence_document_id": str(obligation.evidence_document_id) if obligation.evidence_document_id else None,
            "evidence_document_version_id": str(obligation.evidence_document_version_id) if obligation.evidence_document_version_id else None,
            "evidence_requirement_id": str(obligation.evidence_requirement_id) if obligation.evidence_requirement_id else None,
        },
    )
    db.commit()
    db.refresh(obligation)
    return ComplianceObligationResponse.model_validate(obligation)


@router.post("/obligations/{obligation_id}/evidence/{requirement_id}", response_model=DocumentUploadResponse)
async def upload_compliance_obligation_evidence(
    obligation_id: uuid.UUID,
    requirement_id: uuid.UUID,
    file: Annotated[UploadFile, File(...)],
    note: Annotated[str, Form(min_length=5, max_length=2000)],
    current_user: Annotated[User, Depends(get_current_user)],
    _csrf: Annotated[str, Depends(verify_csrf)],
    db: Annotated[Session, Depends(get_db)],
) -> DocumentUploadResponse:
    obligation = db.get(ComplianceObligation, obligation_id)
    if obligation is None:
        raise HTTPException(status_code=404, detail="Compliance obligation not found.")
    case, application = _get_case(db, obligation.workflow_case_id)
    context = _require_case_access(db, application, current_user)
    if context.role_code != "INSTITUTION_USER" or obligation.status not in {"OPEN", "RETURNED"}:
        raise HTTPException(status_code=403, detail="Only the institution may upload evidence for an open or returned condition.")
    requirement = db.get(ApplicationRequirement, requirement_id)
    if (
        requirement is None
        or requirement.application_revision_id != application.current_revision_id
        or requirement.applicability_status != "APPLICABLE"
    ):
        raise HTTPException(status_code=422, detail="Choose an applicable document requirement from this application's current revision.")

    upload_response = await document_upload_service.upload_document(
        db=db,
        application_requirement_id=requirement_id,
        user=current_user,
        upload_file=file,
        update_requirement_status=False,
    )
    if upload_response.document_version.is_clean:
        obligation = db.scalar(
            select(ComplianceObligation)
            .where(ComplianceObligation.obligation_id == obligation_id)
            .with_for_update()
        )
        if obligation is None or obligation.status not in {"OPEN", "RETURNED"}:
            raise HTTPException(status_code=409, detail="The condition status changed while the document was being uploaded. Review the case before retrying.")
        now = datetime.now(UTC)
        obligation.status = "EVIDENCE_SUBMITTED"
        obligation.evidence_document_id = upload_response.document_version.document_id
        obligation.evidence_document_version_id = upload_response.document_version.document_version_id
        obligation.evidence_requirement_id = requirement_id
        obligation.evidence_reference = upload_response.document_version.original_filename
        obligation.submitted_at = now
        obligation.verification_note = note.strip()
        obligation.updated_at = now
        add_workflow_event(
            db,
            case,
            current_user.user_id,
            event_type="OBLIGATION_EVIDENCE_UPLOADED",
            summary=note.strip(),
            event_payload={
                "obligation_id": str(obligation_id),
                "document_id": str(upload_response.document_version.document_id),
                "document_version_id": str(upload_response.document_version.document_version_id),
                "requirement_id": str(requirement_id),
                "filename": upload_response.document_version.original_filename,
                "version_number": upload_response.document_version.version_number,
            },
        )
        db.commit()
    return upload_response


@router.get("/obligations/{obligation_id}/evidence/download")
def download_compliance_obligation_evidence(
    obligation_id: uuid.UUID,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
) -> FileResponse:
    obligation = db.get(ComplianceObligation, obligation_id)
    if obligation is None or obligation.evidence_document_version_id is None or obligation.evidence_requirement_id is None:
        raise HTTPException(status_code=404, detail="No uploaded evidence document is attached to this condition.")
    _case, application = _get_case(db, obligation.workflow_case_id)
    _require_case_access(db, application, current_user)
    file_path, filename, mime_type = document_upload_service.get_document_for_download(
        db=db,
        application_requirement_id=obligation.evidence_requirement_id,
        document_version_id=obligation.evidence_document_version_id,
        user=current_user,
    )
    return FileResponse(
        path=file_path,
        media_type=mime_type,
        filename=filename,
        content_disposition_type="attachment",
        headers={
            "X-Content-Type-Options": "nosniff",
            "Cache-Control": "private, no-cache, no-store, must-revalidate",
        },
    )


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
            team_scope = and_(
                team_scope,
                or_(WorkflowCase.assigned_user_id.is_(None), WorkflowCase.assigned_user_id == current_user.user_id),
            )
        scope.append(team_scope)

    rows = db.execute(stmt.where(or_(*scope)).order_by(ComplianceObligation.due_at.asc())).all()
    return [ComplianceObligationResponse.model_validate(item) for item, _application in rows]


@router.post("/cases/{workflow_case_id}/document-validity/upload/{requirement_id}", response_model=DocumentUploadResponse)
async def upload_document_validity_source(
    workflow_case_id: uuid.UUID,
    requirement_id: uuid.UUID,
    file: Annotated[UploadFile, File(...)],
    current_user: Annotated[User, Depends(get_current_user)],
    _csrf: Annotated[str, Depends(verify_csrf)],
    db: Annotated[Session, Depends(get_db)],
) -> DocumentUploadResponse:
    case, application = _get_case(db, workflow_case_id)
    context = _require_case_access(db, application, current_user)
    if context.role_code != "INSTITUTION_USER":
        raise HTTPException(status_code=403, detail="Only the institution may upload a renewed lease or regulatory certificate.")
    requirement = db.get(ApplicationRequirement, requirement_id)
    if (
        requirement is None
        or requirement.application_revision_id != application.current_revision_id
        or requirement.applicability_status != "APPLICABLE"
    ):
        raise HTTPException(status_code=422, detail="Choose an applicable document requirement from this application's current revision.")

    upload_response = await document_upload_service.upload_document(
        db=db,
        application_requirement_id=requirement_id,
        user=current_user,
        upload_file=file,
        update_requirement_status=False,
    )
    if upload_response.document_version.is_clean:
        add_workflow_event(
            db,
            case,
            current_user.user_id,
            event_type="DOCUMENT_VALIDITY_REPLACEMENT_UPLOADED",
            summary="A renewed lease or regulatory document version was uploaded for validity review.",
            event_payload={
                "application_requirement_id": str(requirement_id),
                "document_id": str(upload_response.document_version.document_id),
                "document_version_id": str(upload_response.document_version.document_version_id),
                "filename": upload_response.document_version.original_filename,
                "version_number": upload_response.document_version.version_number,
                "sha256_hex": upload_response.document_version.sha256_hex,
            },
        )
        db.commit()
    return upload_response


@router.post("/cases/{workflow_case_id}/document-validity", response_model=DocumentValidityResponse, status_code=status.HTTP_201_CREATED)
def submit_case_document_validity(
    workflow_case_id: uuid.UUID,
    payload: DocumentValiditySubmitRequest,
    current_user: Annotated[User, Depends(get_current_user)],
    _csrf: Annotated[str, Depends(verify_csrf)],
    db: Annotated[Session, Depends(get_db)],
) -> DocumentValidityResponse:
    case, application = _get_case(db, workflow_case_id)
    context = _require_case_access(db, application, current_user)
    if context.role_code != "INSTITUTION_USER":
        raise HTTPException(status_code=403, detail="Only the institution may submit document validity details.")
    requirement = db.get(ApplicationRequirement, payload.application_requirement_id)
    if requirement is None:
        raise HTTPException(status_code=404, detail="Application requirement not found.")
    record = submit_document_validity(
        db,
        case,
        application,
        requirement,
        current_user.user_id,
        document_version_id=payload.document_version_id,
        validity_type=payload.validity_type,
        issue_date=payload.issue_date,
        valid_from=payload.valid_from,
        valid_until=payload.valid_until,
        lease_start_date=payload.lease_start_date,
        lease_end_date=payload.lease_end_date,
        maximum_course_duration_years=payload.maximum_course_duration_years,
        validity_basis_reference=payload.validity_basis_reference,
    )
    db.commit()
    db.refresh(record)
    return DocumentValidityResponse.model_validate(record)


@router.post("/document-validity/{document_validity_record_id}/review", response_model=DocumentValidityResponse)
def review_case_document_validity(
    document_validity_record_id: uuid.UUID,
    payload: DocumentValidityReviewRequest,
    current_user: Annotated[User, Depends(get_current_user)],
    _csrf: Annotated[str, Depends(verify_csrf)],
    db: Annotated[Session, Depends(get_db)],
) -> DocumentValidityResponse:
    record = db.scalar(
        select(DocumentValidityRecord)
        .where(DocumentValidityRecord.document_validity_record_id == document_validity_record_id)
        .with_for_update()
    )
    if record is None:
        raise HTTPException(status_code=404, detail="Document validity record not found.")
    case, application = _get_case(db, record.workflow_case_id)
    context = _require_case_access(db, application, current_user)
    updated = review_document_validity(
        db,
        record,
        case,
        current_user.user_id,
        context.role_code,
        action=payload.action,
        note=payload.note,
    )
    db.commit()
    db.refresh(updated)
    return DocumentValidityResponse.model_validate(updated)


@router.get("/reminder-policies", response_model=list[WorkflowReminderPolicyResponse])
def list_workflow_reminder_policies(
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
) -> list[WorkflowReminderPolicyResponse]:
    role_codes = {context.role_code for context in _contexts(current_user, db)}
    if not role_codes.intersection({"REGULATORY_POLICY_PUBLISHER", "ADMIN"}):
        raise HTTPException(status_code=403, detail="Regulatory policy access is required to view reminder schedules.")
    policies = db.scalars(
        select(WorkflowReminderPolicy).order_by(
            WorkflowReminderPolicy.target_type,
            WorkflowReminderPolicy.days_from_due,
            WorkflowReminderPolicy.policy_code,
        )
    ).all()
    return [WorkflowReminderPolicyResponse.model_validate(policy) for policy in policies]


@router.patch("/reminder-policies/{reminder_policy_id}", response_model=WorkflowReminderPolicyResponse)
def update_workflow_reminder_policy(
    reminder_policy_id: uuid.UUID,
    payload: WorkflowReminderPolicyUpdateRequest,
    current_user: Annotated[User, Depends(get_current_user)],
    _csrf: Annotated[str, Depends(verify_csrf)],
    db: Annotated[Session, Depends(get_db)],
) -> WorkflowReminderPolicyResponse:
    role_codes = {context.role_code for context in _contexts(current_user, db)}
    if "REGULATORY_POLICY_PUBLISHER" not in role_codes:
        raise HTTPException(status_code=403, detail="Only the Regulatory Policy Publisher may change reminder schedules.")
    policy = db.scalar(
        select(WorkflowReminderPolicy)
        .where(WorkflowReminderPolicy.reminder_policy_id == reminder_policy_id)
        .with_for_update()
    )
    if policy is None:
        raise HTTPException(status_code=404, detail="Reminder policy not found.")

    next_days = payload.days_from_due if payload.days_from_due is not None else policy.days_from_due
    next_group = payload.recipient_group if payload.recipient_group is not None else policy.recipient_group
    conflict = db.scalar(
        select(WorkflowReminderPolicy.reminder_policy_id).where(
            WorkflowReminderPolicy.reminder_policy_id != reminder_policy_id,
            WorkflowReminderPolicy.target_type == policy.target_type,
            WorkflowReminderPolicy.days_from_due == next_days,
            WorkflowReminderPolicy.recipient_group == next_group,
        )
    )
    if conflict is not None:
        raise HTTPException(status_code=409, detail="Another reminder policy already uses this target, offset and recipient group.")

    if payload.days_from_due is not None:
        policy.days_from_due = payload.days_from_due
    if payload.recipient_group is not None:
        policy.recipient_group = payload.recipient_group
    if payload.severity is not None:
        policy.severity = payload.severity
    if payload.is_enabled is not None:
        policy.is_enabled = payload.is_enabled
    policy.updated_at = datetime.now(UTC)
    db.commit()
    db.refresh(policy)
    return WorkflowReminderPolicyResponse.model_validate(policy)


@router.get("/reminder-policies", response_model=list[WorkflowReminderPolicyResponse])
def list_workflow_reminder_policies(
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
) -> list[WorkflowReminderPolicyResponse]:
    role_codes = {context.role_code for context in _contexts(current_user, db)}
    if not role_codes.intersection({"REGULATORY_POLICY_PUBLISHER", "ADMIN"}):
        raise HTTPException(status_code=403, detail="Regulatory policy access is required to view reminder schedules.")
    policies = db.scalars(
        select(WorkflowReminderPolicy).order_by(
            WorkflowReminderPolicy.target_type,
            WorkflowReminderPolicy.days_from_due,
            WorkflowReminderPolicy.policy_code,
        )
    ).all()
    return [WorkflowReminderPolicyResponse.model_validate(policy) for policy in policies]


@router.patch("/reminder-policies/{reminder_policy_id}", response_model=WorkflowReminderPolicyResponse)
def update_workflow_reminder_policy(
    reminder_policy_id: uuid.UUID,
    payload: WorkflowReminderPolicyUpdateRequest,
    current_user: Annotated[User, Depends(get_current_user)],
    _csrf: Annotated[str, Depends(verify_csrf)],
    db: Annotated[Session, Depends(get_db)],
) -> WorkflowReminderPolicyResponse:
    role_codes = {context.role_code for context in _contexts(current_user, db)}
    if "REGULATORY_POLICY_PUBLISHER" not in role_codes:
        raise HTTPException(status_code=403, detail="Only the Regulatory Policy Publisher may change reminder schedules.")
    policy = db.scalar(
        select(WorkflowReminderPolicy)
        .where(WorkflowReminderPolicy.reminder_policy_id == reminder_policy_id)
        .with_for_update()
    )
    if policy is None:
        raise HTTPException(status_code=404, detail="Reminder policy not found.")

    next_days = payload.days_from_due if payload.days_from_due is not None else policy.days_from_due
    next_group = payload.recipient_group if payload.recipient_group is not None else policy.recipient_group
    conflict = db.scalar(
        select(WorkflowReminderPolicy.reminder_policy_id).where(
            WorkflowReminderPolicy.reminder_policy_id != reminder_policy_id,
            WorkflowReminderPolicy.target_type == policy.target_type,
            WorkflowReminderPolicy.days_from_due == next_days,
            WorkflowReminderPolicy.recipient_group == next_group,
        )
    )
    if conflict is not None:
        raise HTTPException(status_code=409, detail="Another reminder policy already uses this target, offset and recipient group.")

    if payload.days_from_due is not None:
        policy.days_from_due = payload.days_from_due
    if payload.recipient_group is not None:
        policy.recipient_group = payload.recipient_group
    if payload.severity is not None:
        policy.severity = payload.severity
    if payload.is_enabled is not None:
        policy.is_enabled = payload.is_enabled
    policy.updated_at = datetime.now(UTC)
    db.commit()
    db.refresh(policy)
    return WorkflowReminderPolicyResponse.model_validate(policy)


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

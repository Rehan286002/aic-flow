"""Institutional document validity API.

Records are linked to a clean-scanned, versioned document and remain pending
until an authorised reviewer confirms the declared validity values.
"""
import uuid
from datetime import UTC, datetime
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import and_, or_, select
from sqlalchemy.orm import Session

from app.api.deps import get_active_role_assignments, get_current_user, get_db, verify_csrf
from app.models.application import Application
from app.models.application_document_link import ApplicationDocumentLink
from app.models.application_revision import ApplicationRevision
from app.models.compliance_obligation import ComplianceObligation
from app.models.document import Document
from app.models.document_security_scan import DocumentSecurityScan
from app.models.document_validity_record import DocumentValidityRecord
from app.models.document_version import DocumentVersion
from app.models.workflow_case import WorkflowCase
from app.models.user import User
from app.schemas.workflow import (
    DocumentValidityActionRequest,
    DocumentValidityCreateRequest,
    DocumentValidityResponse,
)
from app.services.workflow_service import add_workflow_event, case_access_context

router = APIRouter(prefix="/document-validity", tags=["document-validity"])
SUPERVISORS = {"BUREAU_SUPERVISOR", "REGIONAL_OFFICER", "LEAD_AUDITOR"}
REVIEWERS = {"SCRUTINY_OFFICER", "AUDITOR", "REGIONAL_OFFICER", "BUREAU_SUPERVISOR", "LEAD_AUDITOR"}


def contexts_for(user: User, db: Session):
    return get_active_role_assignments(user, db)


def get_case(db: Session, case_id: uuid.UUID):
    case = db.get(WorkflowCase, case_id)
    if case is None:
        raise HTTPException(status_code=404, detail="Workflow case not found.")
    application = db.get(Application, case.application_id)
    if application is None:
        raise HTTPException(status_code=404, detail="Application not found.")
    return case, application


def check_access(db: Session, case: WorkflowCase, application: Application, user: User):
    return case_access_context(
        db, application, contexts_for(user, db), case=case, user_id=user.user_id
    )


@router.get("", response_model=list[DocumentValidityResponse])
def list_document_validity(
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
):
    contexts = contexts_for(current_user, db)
    institution_ids = {
        item.institution_id for item in contexts
        if item.role_code == "INSTITUTION_USER" and item.institution_id
    }
    scoped = [item for item in contexts if item.review_team_id]
    if not institution_ids and not scoped:
        raise HTTPException(status_code=403, detail="No document-validity access is assigned to this account.")

    query = (
        select(DocumentValidityRecord)
        .join(WorkflowCase, WorkflowCase.workflow_case_id == DocumentValidityRecord.workflow_case_id)
        .join(Application, Application.application_id == DocumentValidityRecord.application_id)
    )
    scope = []
    if institution_ids:
        scope.append(Application.institution_id.in_(institution_ids))
    for item in scoped:
        clause = Application.review_team_id == item.review_team_id
        if item.role_code not in SUPERVISORS:
            if item.role_code == "AUDITOR":
                role_scope = WorkflowCase.assigned_role_code.in_(["INTAKE_OFFICER", "SCRUTINY_OFFICER"])
            else:
                role_scope = WorkflowCase.assigned_role_code == item.role_code
            clause = and_(
                clause,
                role_scope,
                or_(WorkflowCase.assigned_user_id.is_(None), WorkflowCase.assigned_user_id == current_user.user_id),
            )
        scope.append(clause)

    records = db.scalars(
        query.where(or_(*scope)).order_by(DocumentValidityRecord.valid_until.asc()).limit(500)
    ).all()
    visible = []
    for record in records:
        case, application = get_case(db, record.workflow_case_id)
        try:
            check_access(db, case, application, current_user)
        except HTTPException:
            continue
        visible.append(DocumentValidityResponse.model_validate(record))
    return visible


@router.post("/cases/{workflow_case_id}", response_model=DocumentValidityResponse, status_code=201)
def create_document_validity(
    workflow_case_id: uuid.UUID,
    payload: DocumentValidityCreateRequest,
    current_user: Annotated[User, Depends(get_current_user)],
    _csrf: Annotated[str, Depends(verify_csrf)],
    db: Annotated[Session, Depends(get_db)],
):
    case, application = get_case(db, workflow_case_id)
    context = check_access(db, case, application, current_user)
    if context.role_code != "INSTITUTION_USER":
        raise HTTPException(status_code=403, detail="Only the institution representative may submit document-validity evidence.")
    if payload.valid_from and payload.valid_until < payload.valid_from:
        raise HTTPException(status_code=422, detail="Valid-until cannot precede valid-from.")
    if application.current_revision_id is None:
        raise HTTPException(status_code=409, detail="The application has no current revision.")

    matching_version = db.scalar(
        select(DocumentVersion)
        .join(Document, Document.document_id == DocumentVersion.document_id)
        .join(ApplicationDocumentLink, ApplicationDocumentLink.document_version_id == DocumentVersion.document_version_id)
        .join(ApplicationRevision, ApplicationRevision.application_revision_id == ApplicationDocumentLink.application_revision_id)
        .join(DocumentSecurityScan, DocumentSecurityScan.document_version_id == DocumentVersion.document_version_id)
        .where(
            Document.document_id == payload.document_id,
            DocumentVersion.document_version_id == payload.document_version_id,
            Document.institution_id == application.institution_id,
            ApplicationRevision.application_id == application.application_id,
            ApplicationRevision.application_revision_id == application.current_revision_id,
            DocumentSecurityScan.scan_status == "CLEAN",
        )
    )
    if matching_version is None:
        raise HTTPException(status_code=422, detail="The selected document version must be clean-scanned and linked to this institution's current application revision.")

    previous_record_id = None
    if matching_version.replaces_document_version_id:
        previous_record_id = db.scalar(
            select(DocumentValidityRecord.document_validity_id).where(
                DocumentValidityRecord.document_version_id == matching_version.replaces_document_version_id
            )
        )

    record = DocumentValidityRecord(
        workflow_case_id=case.workflow_case_id,
        application_id=application.application_id,
        institution_id=application.institution_id,
        document_id=payload.document_id,
        document_version_id=payload.document_version_id,
        document_type=payload.document_type.strip(),
        issuer=payload.issuer.strip(),
        valid_from=payload.valid_from,
        valid_until=payload.valid_until,
        document_reference=payload.document_reference.strip(),
        replacement_of_id=previous_record_id,
        created_by=current_user.user_id,
    )
    db.add(record)
    db.flush()
    add_workflow_event(
        db, case, current_user.user_id,
        event_type="DOCUMENT_RENEWAL_SUBMITTED" if previous_record_id else "DOCUMENT_VALIDITY_RECORDED",
        summary="Institution submitted a version-linked document validity record for officer verification.",
        event_payload={
            "document_validity_id": str(record.document_validity_id),
            "document_version_id": str(record.document_version_id),
            "document_type": record.document_type,
            "valid_until": record.valid_until.isoformat(),
            "verification_status": record.verification_status,
        },
    )
    db.commit()
    db.refresh(record)
    return DocumentValidityResponse.model_validate(record)


@router.patch("/{document_validity_id}", response_model=DocumentValidityResponse)
def review_document_validity(
    document_validity_id: uuid.UUID,
    payload: DocumentValidityActionRequest,
    current_user: Annotated[User, Depends(get_current_user)],
    _csrf: Annotated[str, Depends(verify_csrf)],
    db: Annotated[Session, Depends(get_db)],
):
    record = db.get(DocumentValidityRecord, document_validity_id)
    if record is None:
        raise HTTPException(status_code=404, detail="Document-validity record not found.")
    case, application = get_case(db, record.workflow_case_id)
    context = check_access(db, case, application, current_user)
    if context.role_code not in REVIEWERS:
        raise HTTPException(status_code=403, detail="This role cannot verify document-validity evidence.")

    now = datetime.now(UTC)
    if payload.action == "VERIFY":
        if record.verification_status not in {"PENDING_VERIFICATION", "RETURNED", "DISPUTED"}:
            raise HTTPException(status_code=409, detail="Only pending or returned records can be verified.")
        record.verification_status = "VERIFIED"
        record.verified_by = current_user.user_id
        record.verified_at = now
        record.verification_note = payload.note
        if record.replacement_of_id:
            previous = db.get(DocumentValidityRecord, record.replacement_of_id)
            if previous:
                previous.verification_status = "SUPERSEDED"
                previous.verification_note = "Superseded by verified replacement " + str(record.document_validity_id)
    else:
        if record.verification_status not in {"PENDING_VERIFICATION", "DISPUTED"}:
            raise HTTPException(status_code=409, detail="Only pending or disputed records can be returned.")
        record.verification_status = "RETURNED"
        record.verification_note = payload.note
        record.verified_by = current_user.user_id
        record.verified_at = now

    add_workflow_event(
        db, case, current_user.user_id,
        event_type="DOCUMENT_VALIDITY_CONFIRMED",
        summary="Document validity " + payload.action.lower() + ": " + payload.note,
        event_payload={
            "document_validity_id": str(record.document_validity_id),
            "action": payload.action,
            "verification_status": record.verification_status,
        },
    )
    db.commit()
    db.refresh(record)
    return DocumentValidityResponse.model_validate(record)

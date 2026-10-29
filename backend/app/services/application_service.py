import uuid
from datetime import date
from typing import Any

from fastapi import HTTPException, status
from sqlalchemy import func, select, text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.models.application import Application
from app.models.application_field_definition import ApplicationFieldDefinition
from app.models.application_field_value import ApplicationFieldValue
from app.models.application_document_link import ApplicationDocumentLink
from app.models.application_requirements import ApplicationRequirement
from app.models.application_revision import ApplicationRevision
from app.models.application_status_history import ApplicationStatusHistory
from app.models.checklist_item import ChecklistItem
from app.models.enums import ApplicationStatus, RequirementStatus, RevisionStatus
from app.schemas.application import (
    ApplicationCreateRequest,
    ApplicationDetailResponse,
    ApplicationListItemResponse,
    ApplicationRevisionResponse,
    ApplicationStatusHistoryResponse,
    ApplicationUpdateRequest,
)
from app.schemas.checklist import ApplicationRequirementResponse
from app.services.workflow_service import create_workflow_case
from app.services.checklist_service import (
    evaluate_item_applicability,
    get_published_template_for_application,
    initialize_revision_requirements,
)


def generate_application_number(db: Session, academic_year: str, process_type: str = "EOA_SELF_DISCLOSURE") -> str:
    """Generate a concurrency-safe unique application number using PostgreSQL sequence.

    Format: APP-<year_start>-EOA-<seq:04d> (e.g. APP-2026-EOA-0001)
    """
    seq_val = db.scalar(text("SELECT nextval('application_number_seq')"))
    year_prefix = (
        academic_year.split("-")[0] if "-" in academic_year else academic_year[:4]
    )
    category = "INCR" if process_type == "INCREASE_INTAKE" else "EOA" if process_type == "EOA_SELF_DISCLOSURE" else "AICTE"
    return f"APP-{year_prefix}-{category}-{seq_val:04d}"


def get_revision_declarations(db: Session, revision_id: uuid.UUID) -> dict[str, Any]:
    """Load dynamic self-disclosure field values for an application revision."""
    stmt = (
        select(
            ApplicationFieldDefinition.field_code,
            ApplicationFieldValue.value_json,
        )
        .join(
            ApplicationFieldDefinition,
            ApplicationFieldValue.field_definition_id
            == ApplicationFieldDefinition.field_definition_id,
        )
        .where(ApplicationFieldValue.application_revision_id == revision_id)
    )
    rows = db.execute(stmt).all()
    declarations: dict[str, Any] = {}
    for code, val in rows:
        if isinstance(val, dict) and "value" in val:
            declarations[code] = val["value"]
        else:
            declarations[code] = val
    return declarations


def save_revision_declarations(
    db: Session,
    revision_id: uuid.UUID,
    user_id: uuid.UUID,
    declarations: dict[str, Any],
) -> None:
    """Persist or update self-disclosure values in application_field_values."""
    field_defs = {
        fd.field_code: fd for fd in db.scalars(select(ApplicationFieldDefinition)).all()
    }

    for code, raw_val in declarations.items():
        if raw_val is None:
            continue
        field_def = field_defs.get(code)
        if not field_def:
            continue

        # Format appropriately into JSONB
        val_to_store = raw_val.isoformat() if isinstance(raw_val, date) else raw_val
        val_payload = {"value": val_to_store}

        existing_val = db.scalar(
            select(ApplicationFieldValue).where(
                ApplicationFieldValue.application_revision_id == revision_id,
                ApplicationFieldValue.field_definition_id
                == field_def.field_definition_id,
            )
        )
        if existing_val:
            existing_val.value_json = val_payload
            existing_val.entered_by = user_id
        else:
            db.add(
                ApplicationFieldValue(
                    application_revision_id=revision_id,
                    field_definition_id=field_def.field_definition_id,
                    value_json=val_payload,
                    entered_by=user_id,
                )
            )

    db.flush()


def create_application_draft(
    db: Session,
    institution_id: uuid.UUID,
    current_user_id: uuid.UUID,
    payload: ApplicationCreateRequest,
) -> ApplicationDetailResponse:
    """Create an atomic draft application, Revision #1, status history, and 7 requirements.

    Enforces one application per institution, academic year, application family and process category.
    """
    # 1. Enforce single application per institution, AY, and family
    existing_app = db.scalar(
        select(Application).where(
            Application.institution_id == institution_id,
            Application.academic_year == payload.academic_year,
            Application.application_family == payload.application_family,
            Application.process_type == payload.process_type,
        )
    )
    if existing_app:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=(
                f"An application for academic year {payload.academic_year} "
                f"and family {payload.application_family.value} already exists "
                f"for institution {institution_id} (Application No: {existing_app.application_number})."
            ),
        )

    # 2. Check for published template
    template = None
    if payload.process_type == "EOA_SELF_DISCLOSURE":
        template = get_published_template_for_application(
            db, payload.academic_year, payload.application_family
        )
        if not template:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"No published checklist template found for academic year {payload.academic_year}.",
            )

    # 3. Allocate sequence-based application number
    app_number = generate_application_number(db, payload.academic_year, payload.process_type)

    try:
        # 4. Create parent application
        app_record = Application(
            application_number=app_number,
            institution_id=institution_id,
            application_family=payload.application_family,
            process_type=payload.process_type,
            academic_year=payload.academic_year,
            status=ApplicationStatus.DRAFT,
            created_by=current_user_id,
        )
        db.add(app_record)
        db.flush()

        # 5. Create Revision #1
        revision_record = ApplicationRevision(
            application_id=app_record.application_id,
            revision_number=1,
            status=RevisionStatus.DRAFT,
            created_by=current_user_id,
        )
        db.add(revision_record)
        db.flush()

        # Link application to Revision #1
        app_record.current_revision_id = revision_record.application_revision_id

        # 6. Record status history
        status_entry = ApplicationStatusHistory(
            application_id=app_record.application_id,
            from_status=None,
            to_status=ApplicationStatus.DRAFT,
            changed_by=current_user_id,
            change_reason="Initial approval application draft created.",
        )
        db.add(status_entry)

        # 7. Persist dynamic declarations
        declarations: dict[str, Any] = {
            "completion_certificate_issue_date": payload.completion_certificate_issue_date,
            "payment_applicable": payload.payment_applicable,
            "application_remarks": payload.application_remarks,
        }
        if payload.process_type == "EOA_SELF_DISCLOSURE":
            save_revision_declarations(
                db,
                revision_record.application_revision_id,
                current_user_id,
                declarations,
            )

        # 8. Initialize 7 requirements with service-derived applicability
        if template is not None:
            initialize_revision_requirements(
                db,
                revision_record.application_revision_id,
                template.checklist_template_id,
                declarations,
            )

        # Create a separate approval-workflow case; validation records remain a distinct evidence subsystem.
        create_workflow_case(db, app_record, current_user_id, payload.process_type)

        db.commit()
    except IntegrityError as exc:
        db.rollback()
        err_msg = str(exc).lower()
        if "uq_applications_institution_ay_family_process" in err_msg or "uq_applications_institution_ay_family" in err_msg:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=(
                    f"An application for academic year {payload.academic_year} "
                    f"and family {payload.application_family.value} already exists "
                    f"for institution {institution_id}."
                ),
            ) from exc
        # Re-raise any unrelated database integrity error without misclassifying it
        raise
    except Exception:
        db.rollback()
        raise

    db.refresh(app_record)

    return get_application_detail(db, institution_id, app_record.application_id)


def list_institution_applications(
    db: Session, institution_id: uuid.UUID
) -> list[ApplicationListItemResponse]:
    """List all applications for an authorized institution."""
    stmt = (
        select(Application, ApplicationRevision.revision_number)
        .outerjoin(
            ApplicationRevision,
            Application.current_revision_id
            == ApplicationRevision.application_revision_id,
        )
        .where(Application.institution_id == institution_id)
        .order_by(Application.created_at.desc())
    )
    rows = db.execute(stmt).all()

    items: list[ApplicationListItemResponse] = []
    for app_record, rev_number in rows:
        items.append(
            ApplicationListItemResponse(
                application_id=app_record.application_id,
                application_number=app_record.application_number,
                institution_id=app_record.institution_id,
                application_family=app_record.application_family,
                process_type=app_record.process_type,
                academic_year=app_record.academic_year,
                status=app_record.status,
                current_revision_id=app_record.current_revision_id,
                current_revision_number=rev_number,
                created_at=app_record.created_at,
                updated_at=app_record.updated_at,
            )
        )
    return items


def get_application_detail(
    db: Session, institution_id: uuid.UUID, application_id: uuid.UUID
) -> ApplicationDetailResponse:
    """Retrieve full application detail with current revision, requirements, and status history."""
    app_record = db.scalar(
        select(Application).where(
            Application.application_id == application_id,
            Application.institution_id == institution_id,
        )
    )
    if not app_record:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Application not found for this institution.",
        )

    current_revision = None
    if app_record.current_revision_id:
        current_revision = db.get(ApplicationRevision, app_record.current_revision_id)

    declarations: dict[str, Any] = {}
    if current_revision:
        declarations = get_revision_declarations(
            db, current_revision.application_revision_id
        )

    # Status history ordered chronologically descending
    history_records = db.scalars(
        select(ApplicationStatusHistory)
        .where(ApplicationStatusHistory.application_id == application_id)
        .order_by(ApplicationStatusHistory.changed_at.desc())
    ).all()
    history_responses = [
        ApplicationStatusHistoryResponse(
            application_status_history_id=h.application_status_history_id,
            application_id=h.application_id,
            from_status=h.from_status,
            to_status=h.to_status,
            changed_by=h.changed_by,
            change_reason=h.change_reason,
            changed_at=h.changed_at,
        )
        for h in history_records
    ]

    # Requirements for current revision
    req_responses: list[ApplicationRequirementResponse] = []
    if current_revision:
        req_stmt = (
            select(ApplicationRequirement, ChecklistItem)
            .join(
                ChecklistItem,
                ApplicationRequirement.checklist_item_id
                == ChecklistItem.checklist_item_id,
            )
            .where(
                ApplicationRequirement.application_revision_id
                == current_revision.application_revision_id
            )
            .order_by(ChecklistItem.display_order.asc())
        )
        for req, item in db.execute(req_stmt).all():
            req_responses.append(
                ApplicationRequirementResponse(
                    application_requirement_id=req.application_requirement_id,
                    application_revision_id=req.application_revision_id,
                    checklist_item_id=req.checklist_item_id,
                    item_code=item.item_code,
                    title=item.title,
                    description=item.description,
                    expected_document_type_code=item.expected_document_type_code,
                    applicability_status=req.applicability_status,
                    status=req.status.value,
                    determination_reason=req.determination_reason,
                    last_evaluated_at=req.last_evaluated_at,
                    display_order=item.display_order,
                )
            )

    # Calculate summary metrics
    total_reqs = len(req_responses)
    applicable_reqs = sum(
        1 for r in req_responses if r.applicability_status == "APPLICABLE"
    )
    not_applicable_reqs = sum(
        1 for r in req_responses if r.applicability_status == "NOT_APPLICABLE"
    )
    pending_reqs = sum(
        1
        for r in req_responses
        if r.applicability_status == "PENDING_DETERMINATION" or r.status == "PENDING"
    )
    satisfied_reqs = sum(1 for r in req_responses if r.status == "SATISFIED")

    revision_response = (
        ApplicationRevisionResponse(
            application_revision_id=current_revision.application_revision_id,
            application_id=current_revision.application_id,
            revision_number=current_revision.revision_number,
            status=current_revision.status,
            created_at=current_revision.created_at,
            submitted_at=current_revision.submitted_at,
            declarations=declarations,
        )
        if current_revision
        else ApplicationRevisionResponse(
            application_revision_id=uuid.uuid4(),
            application_id=application_id,
            revision_number=1,
            status=RevisionStatus.DRAFT,
            created_at=app_record.created_at,
            declarations={},
        )
    )

    return ApplicationDetailResponse(
        application_id=app_record.application_id,
        application_number=app_record.application_number,
        institution_id=app_record.institution_id,
        application_family=app_record.application_family,
        process_type=app_record.process_type,
        academic_year=app_record.academic_year,
        status=app_record.status,
        current_revision=revision_response,
        status_history=history_responses,
        requirements=req_responses,
        total_requirements=total_reqs,
        applicable_requirements=applicable_reqs,
        not_applicable_requirements=not_applicable_reqs,
        pending_requirements=pending_reqs,
        satisfied_requirements=satisfied_reqs,
        created_at=app_record.created_at,
        updated_at=app_record.updated_at,
    )


def update_application_draft(
    db: Session,
    institution_id: uuid.UUID,
    application_id: uuid.UUID,
    current_user_id: uuid.UUID,
    payload: ApplicationUpdateRequest,
) -> ApplicationDetailResponse:
    """Update editable draft application declarations and recalculate requirement applicability."""
    app_record = db.scalar(
        select(Application).where(
            Application.application_id == application_id,
            Application.institution_id == institution_id,
        )
    )
    if not app_record:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Application not found for this institution.",
        )

    if app_record.status not in {ApplicationStatus.DRAFT, ApplicationStatus.RECTIFICATION_REQUESTED}:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Only draft applications or applications with an open clarification may be modified.",
        )

    current_revision = db.get(ApplicationRevision, app_record.current_revision_id)
    if not current_revision:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Active application revision not found.",
        )

    # A clarification response starts a fresh immutable revision the first time
    # the institution edits the returned application. Earlier evidence remains linked
    # to the earlier revision and is not overwritten.
    if app_record.status == ApplicationStatus.RECTIFICATION_REQUESTED and current_revision.status != RevisionStatus.DRAFT:
        previous_revision = current_revision
        previous_revision.status = RevisionStatus.SUPERSEDED
        latest_number = db.scalar(
            select(func.max(ApplicationRevision.revision_number)).where(
                ApplicationRevision.application_id == application_id
            )
        ) or previous_revision.revision_number
        current_revision = ApplicationRevision(
            application_id=application_id,
            revision_number=latest_number + 1,
            status=RevisionStatus.DRAFT,
            supersedes_revision_id=previous_revision.application_revision_id,
            created_by=current_user_id,
        )
        db.add(current_revision)
        db.flush()

        previous_declarations = get_revision_declarations(db, previous_revision.application_revision_id)
        save_revision_declarations(
            db, current_revision.application_revision_id, current_user_id, previous_declarations
        )

        old_requirements = db.scalars(
            select(ApplicationRequirement).where(
                ApplicationRequirement.application_revision_id == previous_revision.application_revision_id
            )
        ).all()
        requirement_id_map: dict[uuid.UUID, uuid.UUID] = {}
        for old_requirement in old_requirements:
            new_requirement = ApplicationRequirement(
                application_revision_id=current_revision.application_revision_id,
                checklist_item_id=old_requirement.checklist_item_id,
                applicability_status=old_requirement.applicability_status,
                status=old_requirement.status,
                determination_reason=old_requirement.determination_reason,
                last_evaluated_at=old_requirement.last_evaluated_at,
            )
            db.add(new_requirement)
            db.flush()
            requirement_id_map[old_requirement.application_requirement_id] = new_requirement.application_requirement_id

        old_links = db.scalars(
            select(ApplicationDocumentLink).where(
                ApplicationDocumentLink.application_revision_id == previous_revision.application_revision_id
            )
        ).all()
        for old_link in old_links:
            db.add(ApplicationDocumentLink(
                application_revision_id=current_revision.application_revision_id,
                uploaded_for_requirement_id=requirement_id_map.get(old_link.uploaded_for_requirement_id),
                document_version_id=old_link.document_version_id,
            ))
        app_record.current_revision_id = current_revision.application_revision_id
        db.flush()

    # 1. Update persisted declarations
    declarations_to_update: dict[str, Any] = {}
    if payload.completion_certificate_issue_date is not None:
        declarations_to_update["completion_certificate_issue_date"] = (
            payload.completion_certificate_issue_date
        )
    if payload.payment_applicable is not None:
        declarations_to_update["payment_applicable"] = payload.payment_applicable
    if payload.application_remarks is not None:
        declarations_to_update["application_remarks"] = payload.application_remarks

    save_revision_declarations(
        db,
        current_revision.application_revision_id,
        current_user_id,
        declarations_to_update,
    )

    # 2. Load all active declarations for this revision
    full_declarations = get_revision_declarations(
        db, current_revision.application_revision_id
    )

    # 3. Recalculate applicability on requirements
    req_stmt = (
        select(ApplicationRequirement, ChecklistItem)
        .join(
            ChecklistItem,
            ApplicationRequirement.checklist_item_id == ChecklistItem.checklist_item_id,
        )
        .where(
            ApplicationRequirement.application_revision_id
            == current_revision.application_revision_id
        )
    )
    for req, item in db.execute(req_stmt).all():
        app_status, reason = evaluate_item_applicability(item, full_declarations)
        req.applicability_status = app_status
        req.determination_reason = reason
        if app_status == "NOT_APPLICABLE":
            req.status = RequirementStatus.NOT_APPLICABLE
        elif (
            req.status == RequirementStatus.NOT_APPLICABLE
            and app_status == "APPLICABLE"
        ):
            req.status = RequirementStatus.PENDING
        req.last_evaluated_at = func.now()

    app_record.updated_at = func.now()
    db.commit()

    return get_application_detail(db, institution_id, application_id)

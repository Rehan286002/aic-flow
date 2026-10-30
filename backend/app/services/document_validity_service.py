import calendar
import uuid
from datetime import UTC, date, datetime

from fastapi import HTTPException
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.application import Application
from app.models.application_document_link import ApplicationDocumentLink
from app.models.application_requirements import ApplicationRequirement
from app.models.application_revision import ApplicationRevision
from app.models.checklist_item import ChecklistItem
from app.models.document import Document
from app.models.document_security_scan import DocumentSecurityScan
from app.models.document_validity import DocumentValidityRecord
from app.models.document_version import DocumentVersion
from app.models.workflow_case import WorkflowCase
from app.services.workflow_service import add_workflow_event


VALIDITY_TYPES = {
    "LEASE_DEED",
    "STRUCTURAL_STABILITY_CERTIFICATE",
    "FIRE_SAFETY_CERTIFICATE",
    "BUILDING_COMPLETION_CERTIFICATE",
    "ISSUER_DATED_DOCUMENT",
}
VALIDITY_REVIEW_ROLES = {
    "SCRUTINY_OFFICER",
    "AUDITOR",
    "LEAD_AUDITOR",
    "BUREAU_SUPERVISOR",
    "REGIONAL_OFFICER",
}


def add_calendar_years(value: date, years: int) -> date:
    """Add whole calendar years, using the last day of February for leap-day anniversaries."""
    try:
        return value.replace(year=value.year + years)
    except ValueError:
        return value.replace(year=value.year + years, month=2, day=calendar.monthrange(value.year + years, 2)[1])


def calculate_document_validity(
    *,
    validity_type: str,
    issue_date: date | None,
    valid_from: date | None,
    valid_until: date | None,
    lease_start_date: date | None,
    lease_end_date: date | None,
    maximum_course_duration_years: int | None,
    application_submitted_at: datetime | None,
    validity_basis_reference: str,
) -> dict:
    """Calculate handbook-derived dates while leaving issuer-specific findings to human review."""
    if validity_type not in VALIDITY_TYPES:
        raise HTTPException(status_code=422, detail="Select a recognised document validity category.")
    if not validity_basis_reference.strip():
        raise HTTPException(status_code=422, detail="Record the source or regulatory basis for the validity dates.")

    result = {
        "issue_date": issue_date,
        "valid_from": valid_from,
        "valid_until": valid_until,
        "review_due_at": None,
        "lease_start_date": lease_start_date,
        "lease_end_date": lease_end_date,
        "maximum_course_duration_years": maximum_course_duration_years,
        "lease_minimum_term_met": None,
        "lease_live_term_met_at_submission": None,
        "lease_eoa_cutoff_year_triggered": None,
        "lease_assessed_on": None,
    }

    if validity_type == "STRUCTURAL_STABILITY_CERTIFICATE":
        if issue_date is None:
            raise HTTPException(status_code=422, detail="Enter the Structural Stability Certificate issue date.")
        derived_expiry = add_calendar_years(issue_date, 5)
        if valid_until is not None and valid_until != derived_expiry:
            raise HTTPException(
                status_code=422,
                detail="Under APH 2024-27 Clause 6.17(h), the Structural Stability Certificate is valid for five years from issue.",
            )
        result["valid_from"] = issue_date
        result["valid_until"] = derived_expiry
        result["review_due_at"] = derived_expiry

    elif validity_type == "BUILDING_COMPLETION_CERTIFICATE":
        if issue_date is None:
            raise HTTPException(status_code=422, detail="Enter the Completion Certificate issue date.")
        if valid_until is not None:
            raise HTTPException(status_code=422, detail="A Completion Certificate does not use the five-year Structural Stability Certificate expiry rule.")
        # APH 2024-27 Clause 6.17(h): a Structural Stability Certificate becomes
        # necessary after thirty years from the Completion Certificate issue date.
        result["valid_from"] = issue_date
        result["review_due_at"] = add_calendar_years(issue_date, 30)

    elif validity_type == "FIRE_SAFETY_CERTIFICATE":
        if issue_date is None or valid_until is None:
            raise HTTPException(status_code=422, detail="Enter the Fire Safety Certificate issue date and the expiry date printed by its issuing authority.")
        if valid_until < issue_date:
            raise HTTPException(status_code=422, detail="The Fire Safety Certificate expiry date cannot precede its issue date.")
        result["valid_from"] = valid_from or issue_date
        result["review_due_at"] = valid_until

    elif validity_type == "LEASE_DEED":
        if (
            lease_start_date is None
            or lease_end_date is None
            or maximum_course_duration_years is None
            or maximum_course_duration_years < 1
        ):
            raise HTTPException(
                status_code=422,
                detail="Enter the lease start and end dates and the maximum duration of the institution's longest programme.",
            )
        if lease_end_date <= lease_start_date:
            raise HTTPException(status_code=422, detail="Lease end date must be later than its start date.")
        minimum_term_met = lease_end_date >= add_calendar_years(lease_start_date, 30)
        result["valid_from"] = lease_start_date
        result["valid_until"] = lease_end_date
        result["review_due_at"] = lease_end_date
        result["lease_minimum_term_met"] = minimum_term_met
        if application_submitted_at is not None:
            if application_submitted_at.tzinfo is None or application_submitted_at.utcoffset() is None:
                raise HTTPException(status_code=422, detail="Application submission timestamp must include a timezone.")
            assessed_on = application_submitted_at.astimezone(UTC).date()
            result["lease_assessed_on"] = assessed_on
            course_duration_anniversary = add_calendar_years(assessed_on, maximum_course_duration_years)
            result["lease_live_term_met_at_submission"] = lease_end_date >= course_duration_anniversary
            result["lease_eoa_cutoff_year_triggered"] = lease_end_date == course_duration_anniversary

    else:  # ISSUER_DATED_DOCUMENT
        if issue_date is None or valid_until is None:
            raise HTTPException(status_code=422, detail="Enter the issue date and the validity end date specified by the issuing authority.")
        if valid_until < issue_date:
            raise HTTPException(status_code=422, detail="Validity end date cannot precede the issue date.")
        result["valid_from"] = valid_from or issue_date
        result["review_due_at"] = valid_until

    return result


def _latest_clean_document_version(
    db: Session,
    application: Application,
    requirement: ApplicationRequirement,
    document_version_id: uuid.UUID,
) -> tuple[DocumentVersion, Document]:
    if requirement.application_revision_id != application.current_revision_id:
        raise HTTPException(status_code=409, detail="Select a requirement from the application's current revision.")
    if requirement.applicability_status != "APPLICABLE":
        raise HTTPException(status_code=422, detail="Document validity can be registered only against an applicable requirement.")

    latest_scan = (
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
    row = db.execute(
        select(DocumentVersion, Document)
        .join(Document, Document.document_id == DocumentVersion.document_id)
        .join(
            ApplicationDocumentLink,
            ApplicationDocumentLink.document_version_id == DocumentVersion.document_version_id,
        )
        .join(
            ApplicationRevision,
            ApplicationRevision.application_revision_id == ApplicationDocumentLink.application_revision_id,
        )
        .where(
            DocumentVersion.document_version_id == document_version_id,
            Document.institution_id == application.institution_id,
            ApplicationDocumentLink.uploaded_for_requirement_id == requirement.application_requirement_id,
            ApplicationRevision.application_id == application.application_id,
            ApplicationRevision.application_revision_id == application.current_revision_id,
            DocumentVersion.version_number == latest_version_number,
            latest_scan == "CLEAN",
        )
        .limit(1)
    ).first()
    if row is None:
        raise HTTPException(
            status_code=422,
            detail="Choose the latest clean-scanned document version linked to this requirement and institution.",
        )
    return row[0], row[1]


def submit_document_validity(
    db: Session,
    case: WorkflowCase,
    application: Application,
    requirement: ApplicationRequirement,
    actor_user_id: uuid.UUID,
    *,
    document_version_id: uuid.UUID,
    validity_type: str,
    issue_date: date | None,
    valid_from: date | None,
    valid_until: date | None,
    lease_start_date: date | None,
    lease_end_date: date | None,
    maximum_course_duration_years: int | None,
    validity_basis_reference: str,
) -> DocumentValidityRecord:
    document_version, document = _latest_clean_document_version(
        db, application, requirement, document_version_id
    )
    checklist_item = db.get(ChecklistItem, requirement.checklist_item_id)
    if checklist_item is None:
        raise HTTPException(status_code=409, detail="The selected document requirement is no longer available.")
    item_code = checklist_item.item_code
    expected_type = checklist_item.expected_document_type_code
    if validity_type in {"LEASE_DEED", "BUILDING_COMPLETION_CERTIFICATE"} and item_code != "EOA-SD-03":
        raise HTTPException(status_code=422, detail="Land, lease and Completion Certificate validity must be linked to the Land / Building document requirement.")
    if validity_type == "STRUCTURAL_STABILITY_CERTIFICATE" and item_code != "EOA-SD-04" and expected_type != "STRUCTURAL_STABILITY_CERTIFICATE":
        raise HTTPException(status_code=422, detail="Structural Stability Certificate validity must be linked to its dedicated requirement.")
    if validity_type == "FIRE_SAFETY_CERTIFICATE" and item_code != "EOA-SD-05" and expected_type != "FIRE_SAFETY_CERTIFICATE":
        raise HTTPException(status_code=422, detail="Fire Safety Certificate validity must be linked to its dedicated requirement.")
    calculated = calculate_document_validity(
        validity_type=validity_type,
        issue_date=issue_date,
        valid_from=valid_from,
        valid_until=valid_until,
        lease_start_date=lease_start_date,
        lease_end_date=lease_end_date,
        maximum_course_duration_years=maximum_course_duration_years,
        application_submitted_at=application.submitted_at,
        validity_basis_reference=validity_basis_reference,
    )
    existing = db.scalar(
        select(DocumentValidityRecord)
        .where(DocumentValidityRecord.document_version_id == document_version_id)
        .with_for_update()
    )
    now = datetime.now(UTC)
    if existing is not None and existing.status != "RETURNED":
        raise HTTPException(status_code=409, detail="Validity details already exist for this document version. Upload a replacement version to register renewed validity.")
    if existing is None:
        record = DocumentValidityRecord(
            workflow_case_id=case.workflow_case_id,
            application_id=application.application_id,
            application_requirement_id=requirement.application_requirement_id,
            document_id=document.document_id,
            document_version_id=document_version.document_version_id,
            validity_type=validity_type,
            submitted_by=actor_user_id,
            submitted_at=now,
            validity_basis_reference=validity_basis_reference.strip(),
            status="PENDING_REVIEW",
            **calculated,
        )
        db.add(record)
        db.flush()
        event_type = "DOCUMENT_VALIDITY_SUBMITTED"
    else:
        record = existing
        for field, value in calculated.items():
            setattr(record, field, value)
        record.validity_type = validity_type
        record.validity_basis_reference = validity_basis_reference.strip()
        record.status = "PENDING_REVIEW"
        record.submitted_by = actor_user_id
        record.submitted_at = now
        record.reviewed_by = None
        record.reviewed_at = None
        record.review_note = None
        record.updated_at = now
        event_type = "DOCUMENT_VALIDITY_RESUBMITTED"

    add_workflow_event(
        db,
        case,
        actor_user_id,
        event_type=event_type,
        summary=f"{validity_type.replace('_', ' ').title()} validity dates submitted for officer review.",
        event_payload={
            "document_validity_record_id": str(record.document_validity_record_id),
            "document_id": str(record.document_id),
            "document_version_id": str(record.document_version_id),
            "requirement_id": str(record.application_requirement_id),
            "validity_type": validity_type,
            "issue_date": issue_date.isoformat() if issue_date else None,
            "valid_from": calculated["valid_from"].isoformat() if calculated["valid_from"] else None,
            "valid_until": calculated["valid_until"].isoformat() if calculated["valid_until"] else None,
            "review_due_at": calculated["review_due_at"].isoformat() if calculated["review_due_at"] else None,
            "lease_minimum_term_met": calculated["lease_minimum_term_met"],
            "lease_live_term_met_at_submission": calculated["lease_live_term_met_at_submission"],
            "lease_eoa_cutoff_year_triggered": calculated["lease_eoa_cutoff_year_triggered"],
            "validity_basis_reference": validity_basis_reference.strip(),
        },
    )
    return record


def review_document_validity(
    db: Session,
    record: DocumentValidityRecord,
    case: WorkflowCase,
    actor_user_id: uuid.UUID,
    role_code: str,
    *,
    action: str,
    note: str,
) -> DocumentValidityRecord:
    if role_code not in VALIDITY_REVIEW_ROLES:
        raise HTTPException(status_code=403, detail="An authorised scrutiny or supervisory officer must review document validity.")
    if action not in {"VERIFY", "RETURN"}:
        raise HTTPException(status_code=422, detail="Choose Verify or Return.")
    if record.status != "PENDING_REVIEW":
        raise HTTPException(status_code=409, detail="Only pending document-validity records can be reviewed.")
    if len(note.strip()) < 8:
        raise HTTPException(status_code=422, detail="Enter a review note of at least eight characters.")

    now = datetime.now(UTC)
    if action == "VERIFY":
        previous_records = db.scalars(
            select(DocumentValidityRecord)
            .where(
                DocumentValidityRecord.application_requirement_id == record.application_requirement_id,
                DocumentValidityRecord.validity_type == record.validity_type,
                DocumentValidityRecord.status == "VERIFIED",
                DocumentValidityRecord.document_validity_record_id != record.document_validity_record_id,
            )
            .with_for_update()
        ).all()
        if previous_records:
            previous_records.sort(key=lambda item: item.reviewed_at or item.created_at, reverse=True)
            record.supersedes_validity_record_id = previous_records[0].document_validity_record_id
        for previous in previous_records:
            previous.status = "SUPERSEDED"
            previous.updated_at = now
        record.status = "VERIFIED"
        record.reviewed_by = actor_user_id
        record.reviewed_at = now
        record.review_note = note.strip()
        add_workflow_event(
            db, case, actor_user_id,
            event_type="DOCUMENT_VALIDITY_VERIFIED",
            summary=f"{record.validity_type.replace('_', ' ').title()} validity details verified.",
            event_payload={
                "document_validity_record_id": str(record.document_validity_record_id),
                "document_version_id": str(record.document_version_id),
                "valid_until": record.valid_until.isoformat() if record.valid_until else None,
                "review_due_at": record.review_due_at.isoformat() if record.review_due_at else None,
                "review_note": note.strip(),
            },
        )
    else:
        record.status = "RETURNED"
        record.reviewed_by = actor_user_id
        record.reviewed_at = now
        record.review_note = note.strip()
        add_workflow_event(
            db, case, actor_user_id,
            event_type="DOCUMENT_VALIDITY_RETURNED",
            summary=f"{record.validity_type.replace('_', ' ').title()} validity details returned for correction.",
            event_payload={
                "document_validity_record_id": str(record.document_validity_record_id),
                "document_version_id": str(record.document_version_id),
                "review_note": note.strip(),
            },
        )
    record.updated_at = now
    return record

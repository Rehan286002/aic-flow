import uuid
from datetime import date
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.application_field_definition import ApplicationFieldDefinition
from app.models.application_requirements import ApplicationRequirement
from app.models.checklist_item import ChecklistItem
from app.models.checklist_template import ChecklistTemplate
from app.models.document_type import DocumentType
from app.models.enums import ApplicationFamily, RequirementStatus

# Fixed prototype assessment reference date for Academic Year 2026-27 evaluation.
# This serves as a deterministic reference point for assessing elapsed building age (>30 years)
# and is NOT an official AICTE statutory application filing or submission deadline.
DEFAULT_ASSESSMENT_DATE = date(2026, 7, 1)

STANDARD_DOCUMENT_TYPES = [
    {
        "type_code": "AFFIDAVIT_UNDERTAKING",
        "type_name": "Affidavit / Undertaking",
        "description": "Notarized affidavit on non-judicial stamp paper affirming regulatory compliance",
    },
    {
        "type_code": "PAYMENT_RECEIPT",
        "type_name": "AICTE Web-Portal Payment Receipt",
        "description": "Official bank challan or web-portal payment gateway transaction receipt",
    },
    {
        "type_code": "BUILDING_DOCUMENT",
        "type_name": "Land / Building / Occupancy Document",
        "description": "Competent authority approved building completion, occupancy or sanction certificate",
    },
    {
        "type_code": "STRUCTURAL_STABILITY_CERTIFICATE",
        "type_name": "Structural Stability Certificate",
        "description": "Registered structural engineer certificate of building structural stability",
    },
    {
        "type_code": "FIRE_SAFETY_CERTIFICATE",
        "type_name": "Fire Safety Certificate",
        "description": "Fire safety certificate or NOC issued by the competent fire services authority",
    },
    {
        "type_code": "SATELLITE_MAP",
        "type_name": "Satellite Map / Geographical Coordinates",
        "description": "Satellite map showing geographical location and entrance GPS coordinates",
    },
    {
        "type_code": "AUDITED_STATEMENT",
        "type_name": "Audited Financial Statement",
        "description": "Previous-year audited balance sheet and statements of accounts with CA UDIN",
    },
]

STANDARD_FIELD_DEFINITIONS = [
    {
        "field_code": "completion_certificate_issue_date",
        "field_label": "Building Completion Certificate Issue Date",
        "data_type": "DATE",
        "applies_to": [ApplicationFamily.EXISTING_INSTITUTION],
        "applicant_editable": True,
    },
    {
        "field_code": "payment_applicable",
        "field_label": "Payment Receipt Applicable Declaration",
        "data_type": "BOOLEAN",
        "applies_to": [ApplicationFamily.EXISTING_INSTITUTION],
        "applicant_editable": True,
    },
    {
        "field_code": "application_remarks",
        "field_label": "Applicant Self-Disclosure Remarks",
        "data_type": "TEXT",
        "applies_to": [ApplicationFamily.EXISTING_INSTITUTION],
        "applicant_editable": True,
    },
]

ANNEXURE_2_1_ITEMS = [
    {
        "item_code": "EOA-SD-01",
        "title": "Affidavit 2",
        "description": "Notarized affidavit on ₹100 non-judicial stamp paper affirming compliance with AICTE governance, fee, and faculty norms under Approval Process Handbook Annexure 2.1.",
        "expected_document_type_code": "AFFIDAVIT_UNDERTAKING",
        "is_mandatory_by_default": True,
        "applicability_condition": {"rule": "ALWAYS"},
        "validation_config": {},
        "regulatory_clause_reference": "APH 2024-27 Annexure 2.1 Item 1",
        "display_order": 1,
    },
    {
        "item_code": "EOA-SD-02",
        "title": "Copy of AICTE Web-Portal payment receipt, if any",
        "description": "Copy of AICTE Web-Portal payment receipt, if any.",
        "expected_document_type_code": "PAYMENT_RECEIPT",
        "is_mandatory_by_default": False,
        "applicability_condition": {"rule": "PAYMENT_DECLARED_APPLICABLE"},
        "validation_config": {},
        "regulatory_clause_reference": "APH 2024-27 Annexure 2.1 Item 2",
        "display_order": 2,
    },
    {
        "item_code": "EOA-SD-03",
        "title": "Valid Occupancy Certificate / Completion Certificate / Building License / Form D",
        "description": "Valid Occupancy Certificate / Completion Certificate / Building License / Form D, as applicable, issued by the Competent Authority.",
        "expected_document_type_code": "BUILDING_DOCUMENT",
        "is_mandatory_by_default": True,
        "applicability_condition": {"rule": "ALWAYS"},
        "validation_config": {},
        "regulatory_clause_reference": "APH 2024-27 Annexure 2.1 Item 3",
        "display_order": 3,
    },
    {
        "item_code": "EOA-SD-04",
        "title": "Valid Structural Stability Certificate",
        "description": "Valid Structural Stability Certificate from a registered Structural Engineer when the building is more than 30 years from the issue of its Completion Certificate.",
        "expected_document_type_code": "STRUCTURAL_STABILITY_CERTIFICATE",
        "is_mandatory_by_default": False,
        "applicability_condition": {
            "rule": "BUILDING_AGE_GT_30",
            "threshold_years": 30,
        },
        "validation_config": {
            "validity_years": 5,
            "clause": "APH 2024-27 Annexure 2.1 Item 4 (validity period: 5 years)",
        },
        "regulatory_clause_reference": "APH 2024-27 Annexure 2.1 Item 4",
        "display_order": 4,
    },
    {
        "item_code": "EOA-SD-05",
        "title": "Valid Fire Safety Certificate",
        "description": "Valid Fire Safety Certificate issued by the Competent Authority.",
        "expected_document_type_code": "FIRE_SAFETY_CERTIFICATE",
        "is_mandatory_by_default": True,
        "applicability_condition": {"rule": "ALWAYS"},
        "validation_config": {"validity_rule": "ISSUER_SPECIFIC"},
        "regulatory_clause_reference": "APH 2024-27 Annexure 2.1 Item 5",
        "display_order": 5,
    },
    {
        "item_code": "EOA-SD-06",
        "title": "Satellite map showing geographical location of the land",
        "description": "Satellite map showing geographical location of the land, with latitude and longitude at the entrance of the main building.",
        "expected_document_type_code": "SATELLITE_MAP",
        "is_mandatory_by_default": True,
        "applicability_condition": {"rule": "ALWAYS"},
        "validation_config": {},
        "regulatory_clause_reference": "APH 2024-27 Annexure 2.1 Item 6",
        "display_order": 6,
    },
    {
        "item_code": "EOA-SD-07",
        "title": "Previous-year audited statement of accounts",
        "description": "Previous-year audited statement of accounts of the Trust / Society / Company.",
        "expected_document_type_code": "AUDITED_STATEMENT",
        "is_mandatory_by_default": True,
        "applicability_condition": {"rule": "ALWAYS"},
        "validation_config": {},
        "regulatory_clause_reference": "APH 2024-27 Annexure 2.1 Item 7",
        "display_order": 7,
    },
]


def seed_standard_references(db: Session) -> dict[str, int]:
    """Seed DocumentTypes, ApplicationFieldDefinitions, ChecklistTemplate and ChecklistItems idempotently."""
    counts = {
        "document_types": 0,
        "field_definitions": 0,
        "checklist_templates": 0,
        "checklist_items": 0,
    }

    # 1. Document Types
    for doc in STANDARD_DOCUMENT_TYPES:
        existing = db.scalar(
            select(DocumentType).where(DocumentType.type_code == doc["type_code"])
        )
        if not existing:
            db.add(
                DocumentType(
                    type_code=doc["type_code"],
                    type_name=doc["type_name"],
                    description=doc["description"],
                    is_active=True,
                )
            )
            counts["document_types"] += 1

    # 2. Field Definitions
    for field in STANDARD_FIELD_DEFINITIONS:
        existing_field = db.scalar(
            select(ApplicationFieldDefinition).where(
                ApplicationFieldDefinition.field_code == field["field_code"]
            )
        )
        if not existing_field:
            db.add(
                ApplicationFieldDefinition(
                    field_code=field["field_code"],
                    field_label=field["field_label"],
                    data_type=field["data_type"],
                    applies_to=field["applies_to"],
                    applicant_editable=field["applicant_editable"],
                    is_active=True,
                )
            )
            counts["field_definitions"] += 1

    # 3. Checklist Template (EOA-AY2026-27 v1)
    template_code = "EOA-AY2026-27"
    template = db.scalar(
        select(ChecklistTemplate).where(
            ChecklistTemplate.template_code == template_code,
            ChecklistTemplate.version_number == 1,
        )
    )
    if not template:
        template = ChecklistTemplate(
            template_code=template_code,
            template_name="Extension of Approval (EoA) Self-Disclosure Checklist (AY 2026-27)",
            application_family=ApplicationFamily.EXISTING_INSTITUTION,
            academic_year_from="2026-27",
            academic_year_to=None,
            version_number=1,
            regulatory_reference="AICTE Approval Process Handbook (APH) 2024-25 to 2026-27, Annexure 2.1",
            is_published=True,
        )
        db.add(template)
        db.flush()
        counts["checklist_templates"] += 1

    # 4. Checklist Items
    for item in ANNEXURE_2_1_ITEMS:
        existing_item = db.scalar(
            select(ChecklistItem).where(
                ChecklistItem.checklist_template_id == template.checklist_template_id,
                ChecklistItem.item_code == item["item_code"],
            )
        )
        if not existing_item:
            db.add(
                ChecklistItem(
                    checklist_template_id=template.checklist_template_id,
                    item_code=item["item_code"],
                    title=item["title"],
                    description=item["description"],
                    expected_document_type_code=item["expected_document_type_code"],
                    is_mandatory_by_default=item["is_mandatory_by_default"],
                    applicability_condition=item["applicability_condition"],
                    validation_config=item["validation_config"],
                    regulatory_clause_reference=item["regulatory_clause_reference"],
                    display_order=item["display_order"],
                )
            )
            counts["checklist_items"] += 1

    db.commit()
    return counts


def get_published_template_for_application(
    db: Session,
    academic_year: str,
    family: ApplicationFamily,
) -> ChecklistTemplate | None:
    """Retrieve published ChecklistTemplate matching family and academic year."""
    stmt = (
        select(ChecklistTemplate)
        .where(
            ChecklistTemplate.application_family == family,
            ChecklistTemplate.academic_year_from <= academic_year,
            ChecklistTemplate.is_published.is_(True),
        )
        .order_by(ChecklistTemplate.version_number.desc())
    )
    return db.scalars(stmt).first()


def evaluate_item_applicability(
    item: ChecklistItem,
    declarations: dict[str, Any],
    assessment_date: date | None = None,
) -> tuple[str, str]:
    """Calculate derived applicability status and regulatory determination reason.

    Assessment boundary rules:
    - EOA-SD-04 (Structural Stability Certificate):
        Requires Completion Certificate issue date.
        Threshold: More than 30 years elapsed from assessment date (commencement of AY 2026-27).
        - > 30 years: APPLICABLE
        - <= 30 years (including exact 30-year boundary): NOT_APPLICABLE
        - Missing/unknown: PENDING_DETERMINATION
    - EOA-SD-02 (AICTE Web-Portal Payment Receipt):
        Applicable 'if any' under APH Annexure 2.1.
        - Declared True: APPLICABLE
        - Declared False: NOT_APPLICABLE
        - Missing/None: PENDING_DETERMINATION
    - All other items: APPLICABLE (Mandatory under APH Annexure 2.1).
    """
    if assessment_date is None:
        assessment_date = DEFAULT_ASSESSMENT_DATE

    # 1. Structural Stability Certificate (EOA-SD-04)
    if item.item_code == "EOA-SD-04":
        raw_date = declarations.get("completion_certificate_issue_date")
        if not raw_date:
            return (
                "PENDING_DETERMINATION",
                "Building Completion Certificate issue date not declared; structural stability applicability pending determination.",
            )

        if isinstance(raw_date, str):
            cert_date = date.fromisoformat(raw_date)
        elif isinstance(raw_date, date):
            cert_date = raw_date
        else:
            return (
                "PENDING_DETERMINATION",
                "Invalid Completion Certificate issue date format; structural stability applicability pending determination.",
            )

        # Exact 30-year boundary calculation:
        # Exactly 30 years before assessment_date (e.g. 2026-07-01 -> 1996-07-01).
        # Clause specifies: "when the building is more than 30 years from the issue of its Completion Certificate".
        # If cert_date == boundary_date -> exactly 30.0 years elapsed -> NOT_APPLICABLE.
        # If cert_date < boundary_date -> more than 30 years elapsed -> APPLICABLE.
        boundary_date = date(
            assessment_date.year - 30,
            assessment_date.month,
            assessment_date.day,
        )

        elapsed_days = (assessment_date - cert_date).days
        elapsed_years = elapsed_days / 365.25

        if cert_date < boundary_date:
            return (
                "APPLICABLE",
                (
                    f"Building Completion Certificate issue date is {cert_date.isoformat()} "
                    f"(elapsed: {elapsed_years:.1f} years, exceeding the 30-year statutory threshold; "
                    "Structural Stability Certificate from registered Structural Engineer is required)."
                ),
            )
        else:
            return (
                "NOT_APPLICABLE",
                (
                    f"Building Completion Certificate issue date is {cert_date.isoformat()} "
                    f"(elapsed: {elapsed_years:.1f} years, within the 30-year statutory threshold; "
                    "Structural Stability Certificate is not applicable)."
                ),
            )

    # 2. Payment Receipt (EOA-SD-02)
    if item.item_code == "EOA-SD-02":
        payment_decl = declarations.get("payment_applicable")
        if payment_decl is True:
            return (
                "APPLICABLE",
                "Fee payment receipt declared applicable by institution under APH Chapter II norms.",
            )
        elif payment_decl is False:
            return (
                "NOT_APPLICABLE",
                "Fee payment declared exempt or not applicable under regulatory norms.",
            )
        else:
            return (
                "PENDING_DETERMINATION",
                "AICTE web-portal payment receipt applicability pending institutional self-disclosure declaration.",
            )

    # 3. Mandatory default items
    return (
        "APPLICABLE",
        "Mandatory self-disclosure requirement under AICTE Approval Process Handbook Annexure 2.1.",
    )


def initialize_revision_requirements(
    db: Session,
    revision_id: uuid.UUID,
    template_id: uuid.UUID,
    declarations: dict[str, Any],
    assessment_date: date | None = None,
) -> list[ApplicationRequirement]:
    """Initialize all ApplicationRequirement rows for a new revision with service-derived applicability."""
    items = db.scalars(
        select(ChecklistItem)
        .where(ChecklistItem.checklist_template_id == template_id)
        .order_by(ChecklistItem.display_order.asc())
    ).all()

    created_requirements: list[ApplicationRequirement] = []
    for item in items:
        app_status, reason = evaluate_item_applicability(
            item, declarations, assessment_date
        )
        req_status = (
            RequirementStatus.NOT_APPLICABLE
            if app_status == "NOT_APPLICABLE"
            else RequirementStatus.PENDING
        )

        req = ApplicationRequirement(
            application_revision_id=revision_id,
            checklist_item_id=item.checklist_item_id,
            applicability_status=app_status,
            status=req_status,
            determination_reason=reason,
        )
        db.add(req)
        created_requirements.append(req)

    return created_requirements

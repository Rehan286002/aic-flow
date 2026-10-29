import uuid
from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict


class ChecklistTemplateResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    checklist_template_id: uuid.UUID
    template_code: str
    template_name: str
    application_family: str
    academic_year_from: str
    academic_year_to: str | None = None
    version_number: int
    regulatory_reference: str | None = None
    is_published: bool


class ChecklistItemResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    checklist_item_id: uuid.UUID
    checklist_template_id: uuid.UUID
    item_code: str
    title: str
    description: str | None = None
    expected_document_type_code: str | None = None
    is_mandatory_by_default: bool
    applicability_condition: dict[str, Any]
    validation_config: dict[str, Any]
    regulatory_clause_reference: str | None = None
    display_order: int


class ApplicationRequirementResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    application_requirement_id: uuid.UUID
    application_revision_id: uuid.UUID
    checklist_item_id: uuid.UUID
    item_code: str
    title: str
    description: str | None = None
    expected_document_type_code: str | None = None
    applicability_status: str
    status: str
    determination_reason: str | None = None
    last_evaluated_at: datetime | None = None
    display_order: int

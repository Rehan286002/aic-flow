"""AIC-Verify — Validation Schemas."""

from __future__ import annotations

import re
from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.models.enums import FindingCategory, FindingSeverity, FindingStatus


class FindingEvidenceRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    finding_evidence_id: UUID
    document_version_id: UUID | None = None
    extracted_field_id: UUID | None = None
    verification_attempt_id: UUID | None = None
    page_number: int | None = None
    evidence_type: str
    evidence_reference: str | None = None
    evidence_summary: str | None = None
    created_at: datetime


class FindingRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    finding_id: UUID
    application_id: UUID
    application_revision_id: UUID
    validation_run_id: UUID | None = None
    validation_result_id: UUID | None = None
    category: FindingCategory
    severity: FindingSeverity
    status: FindingStatus
    title: str
    internal_reason: str | None = None
    recommended_action: str | None = None
    is_internal_only: bool
    created_at: datetime
    updated_at: datetime
    evidence: list[FindingEvidenceRead] = Field(default_factory=list)


class ValidationResultRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    validation_result_id: UUID
    validation_run_id: UUID
    application_requirement_id: UUID | None = None
    validation_rule_version_id: UUID | None = None
    result_status: str
    expected_value: Any | None = None
    observed_value: Any | None = None
    explanation: str
    evaluated_at: datetime
    findings: list[FindingRead] = Field(default_factory=list)


class ValidationRunCreate(BaseModel):
    run_type: str = Field(default="FULL", description="FULL, RULE_ONLY, or RECHECK")
    checklist_item_ids: list[UUID] | None = None


class ValidationRunSummary(BaseModel):
    validation_run_id: UUID
    status: str
    run_type: str
    engine_version: str | None = None
    started_at: datetime
    completed_at: datetime | None = None
    total_results: int = 0
    satisfied_count: int = 0
    deficient_count: int = 0
    not_applicable_count: int = 0
    unable_to_determine_count: int = 0
    warning_count: int = 0
    findings_by_severity: dict[str, int] = Field(default_factory=dict)


class ValidationRunRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    validation_run_id: UUID
    application_revision_id: UUID
    checklist_template_id: UUID | None = None
    run_type: str
    engine_version: str | None = None
    status: str
    started_at: datetime
    completed_at: datetime | None = None
    evaluation_as_of: datetime
    results: list[ValidationResultRead] = Field(default_factory=list)
    summary: ValidationRunSummary | None = None


class FindingStatusUpdate(BaseModel):
    """Payload for auditor finding status update with mandatory rationale."""

    status: FindingStatus
    review_note: str = Field(
        ...,
        min_length=5,
        max_length=2000,
        description="Mandatory auditor review rationale (minimum 5 non-whitespace characters)",
    )

    @field_validator("review_note")
    @classmethod
    def validate_review_note_whitespace(cls, v: str) -> str:
        non_ws = re.sub(r"\s", "", v)
        if len(non_ws) < 5:
            raise ValueError(
                "Review note must contain at least 5 non-whitespace characters"
            )
        return v.strip()

"""AIC-Verify — Synthetic State Revenue and Land Records Connector (SRC_REVENUE_LAND)."""

from __future__ import annotations

import json
import uuid
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, ClassVar

from app.connectors.base import (
    BaseSourceConnector,
    DocumentVerificationResult,
    InstitutionSnapshotResult,
    MalformedPayloadError,
    SourceEnvironment,
    SourceSyncStatus,
    SourceTimeoutError,
    SourceUnavailableError,
    compute_canonical_sha256,
)
from app.models.enums import SourceType, VerificationMethod, VerificationStatus

FIXTURE_PATH = (
    Path(__file__).resolve().parents[3]
    / "fixtures"
    / "source_records"
    / "SRC_REVENUE_LAND_institution.json"
)


def _get_default_payload() -> dict[str, Any]:
    if FIXTURE_PATH.is_file():
        with open(FIXTURE_PATH, "r", encoding="utf-8") as f:
            return json.load(f)
    return {
        "_source_code": "SRC_REVENUE_LAND",
        "_provenance": "SIMULATED",
        "_environment": "SIMULATED",
        "aicte_permanent_id": "SYNTH-AICTE-0001",
        "document_reference": "TITLE-DEED-REG-1989-8842",
        "registered_owner": "Apex Educational and Charitable Trust",
        "parcel_survey_numbers": ["42/1", "42/2"],
        "village": "Kurla",
        "district": "Mumbai Suburban",
        "state": "Maharashtra",
        "registered_area_sqm": 21245.0,
        "land_use_category": "EDUCATIONAL_INSTITUTIONAL",
        "encumbrance_status": "FREE_OF_ALL_ENCUMBRANCES",
        "registration_date": "1989-03-22",
    }


class LandRevenueConnector(BaseSourceConnector):
    """Synthetic adapter for State Revenue and Land Records Department (Mahabhumi / Bhulekh)."""

    source_code = "SRC_REVENUE_LAND"
    source_name = "State Revenue and Land Records Department (SYNTHETIC)"
    source_type = SourceType.GOVERNMENT_PORTAL
    integration_mode = "MOCK"
    adapter_version = "1.0.0-synthetic"
    official_domain = "mahabhumi.gov.in.synthetic"
    supported_document_types: ClassVar[list[int] | None] = [3]

    def fetch_institution_snapshot(
        self,
        aicte_permanent_id: str,
        institution_id: uuid.UUID | None = None,
        correlation_id: str | None = None,
        simulate_failure: str | None = None,
    ) -> InstitutionSnapshotResult:
        if simulate_failure == "TIMEOUT":
            raise SourceTimeoutError(
                f"Simulated timeout connecting to {self.source_code}"
            )
        if simulate_failure == "UNAVAILABLE":
            raise SourceUnavailableError(
                f"Simulated service unavailable in {self.source_code}"
            )
        if simulate_failure == "MALFORMED":
            raise MalformedPayloadError(
                f"Simulated malformed payload in {self.source_code}"
            )

        payload = _get_default_payload()
        if aicte_permanent_id != payload.get("aicte_permanent_id"):
            return InstitutionSnapshotResult(
                source_code=self.source_code,
                institution_id=institution_id,
                aicte_permanent_id=aicte_permanent_id,
                record_data={},
                source_system=self.source_code,
                payload_sha256=compute_canonical_sha256({}),
                effective_from=datetime(1989, 3, 22, tzinfo=UTC),
                environment=SourceEnvironment.SIMULATED,
                adapter_version=self.adapter_version,
                status=SourceSyncStatus.FAILED,
                records_received=0,
                error_code="RECORD_NOT_FOUND",
                error_summary=f"No registered land records found for institution {aicte_permanent_id}",
            )

        payload_sha256 = compute_canonical_sha256(payload)
        return InstitutionSnapshotResult(
            source_code=self.source_code,
            institution_id=institution_id,
            aicte_permanent_id=aicte_permanent_id,
            record_data=payload,
            source_system=self.source_code,
            source_reference=payload.get(
                "document_reference", "TITLE-DEED-REG-1989-8842"
            ),
            payload_sha256=payload_sha256,
            effective_from=datetime(1989, 3, 22, tzinfo=UTC),
            source_updated_at=datetime(2024, 1, 15, tzinfo=UTC),
            environment=SourceEnvironment.SIMULATED,
            adapter_version=self.adapter_version,
            status=SourceSyncStatus.SUCCEEDED,
            records_received=1,
        )

    def verify_document_reference(
        self,
        document_reference: str,
        document_type_code: str | None = None,
        expected_fields: dict[str, Any] | None = None,
        correlation_id: str | None = None,
        simulate_failure: str | None = None,
    ) -> DocumentVerificationResult:
        if simulate_failure == "TIMEOUT":
            raise SourceTimeoutError(f"Simulated timeout in {self.source_code}")
        if simulate_failure == "UNAVAILABLE":
            raise SourceUnavailableError(
                f"Simulated service unavailable in {self.source_code}"
            )

        payload = _get_default_payload()
        canonical_ref = payload.get("document_reference", "TITLE-DEED-REG-1989-8842")

        cleaned = document_reference.strip().replace(" ", "").upper()
        # Accept if reference matches canonical or contains 1989-8842
        is_match = (cleaned == canonical_ref.replace(" ", "").upper()) or (
            "8842" in cleaned
        )

        status = (
            VerificationStatus.VERIFIED if is_match else VerificationStatus.MISMATCH
        )
        summary = {
            "queried_reference": document_reference,
            "registered_deed_found": is_match,
            "registered_owner": payload.get("registered_owner") if is_match else None,
            "survey_numbers": payload.get("parcel_survey_numbers") if is_match else [],
            "encumbrance_status": payload.get("encumbrance_status")
            if is_match
            else None,
            "provenance": "SIMULATED",
        }

        return DocumentVerificationResult(
            source_code=self.source_code,
            method=VerificationMethod.OFFICIAL_PORTAL,
            status=status,
            source_reference_number=document_reference,
            response_summary=summary,
            compared_fields=expected_fields or {},
            source_response_reference=f"MAHABHUMI-{document_reference}",
            environment=SourceEnvironment.SIMULATED,
            adapter_version=self.adapter_version,
            response_sha256=compute_canonical_sha256(summary),
        )

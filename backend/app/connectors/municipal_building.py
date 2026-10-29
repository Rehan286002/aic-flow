"""AIC-Verify — Synthetic Municipal Town Planning & Building Authority Connector (SRC_MUNICIPAL_BLDG)."""

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
    / "SRC_MUNICIPAL_BLDG_institution.json"
)


def _get_default_payload() -> dict[str, Any]:
    if FIXTURE_PATH.is_file():
        with open(FIXTURE_PATH, "r", encoding="utf-8") as f:
            return json.load(f)
    return {
        "_source_code": "SRC_MUNICIPAL_BLDG",
        "_provenance": "SIMULATED",
        "_environment": "SIMULATED",
        "aicte_permanent_id": "SYNTH-AICTE-0001",
        "sanction_plan_order_no": "MCGM-BP-1989-4412",
        "sanction_date": "1989-06-18",
        "occupancy_certificate_number": "MCGM-OCC-1990-0891",
        "occupancy_certificate_date": "1990-05-15",
        "building_completion_date": "1990-05-15",
        "building_use": "INSTITUTIONAL_COLLEGE",
        "total_constructed_area_sqm": 14250.0,
        "number_of_floors": 4,
        "occupancy_status": "FULL_PERMANENT",
    }


class MunicipalBuildingConnector(BaseSourceConnector):
    """Synthetic adapter for Municipal Town Planning & Building Authority (MCGM / Town Planning)."""

    source_code = "SRC_MUNICIPAL_BLDG"
    source_name = "Municipal Town Planning & Building Authority (SYNTHETIC)"
    source_type = SourceType.ISSUING_AUTHORITY
    integration_mode = "MOCK"
    adapter_version = "1.0.0-synthetic"
    official_domain = "mcgm.gov.in.synthetic"
    supported_document_types: ClassVar[list[int] | None] = [3, 4]

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
                effective_from=datetime(1990, 5, 15, tzinfo=UTC),
                environment=SourceEnvironment.SIMULATED,
                adapter_version=self.adapter_version,
                status=SourceSyncStatus.FAILED,
                records_received=0,
                error_code="RECORD_NOT_FOUND",
                error_summary=f"No municipal building records for {aicte_permanent_id}",
            )

        payload_sha256 = compute_canonical_sha256(payload)
        return InstitutionSnapshotResult(
            source_code=self.source_code,
            institution_id=institution_id,
            aicte_permanent_id=aicte_permanent_id,
            record_data=payload,
            source_system=self.source_code,
            source_reference=payload.get(
                "occupancy_certificate_number", "MCGM-OCC-1990-0891"
            ),
            payload_sha256=payload_sha256,
            effective_from=datetime(1990, 5, 15, tzinfo=UTC),
            source_updated_at=datetime(2023, 8, 10, tzinfo=UTC),
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
        occ_no = payload.get("occupancy_certificate_number", "MCGM-OCC-1990-0891")
        plan_no = payload.get("sanction_plan_order_no", "MCGM-BP-1989-4412")

        cleaned = document_reference.strip().replace(" ", "").upper()
        is_occ_match = (cleaned == occ_no.replace(" ", "").upper()) or (
            "0891" in cleaned
        )
        is_plan_match = (cleaned == plan_no.replace(" ", "").upper()) or (
            "4412" in cleaned
        )

        is_match = is_occ_match or is_plan_match
        status = (
            VerificationStatus.VERIFIED if is_match else VerificationStatus.MISMATCH
        )

        summary = {
            "queried_reference": document_reference,
            "municipal_record_found": is_match,
            "sanction_order_no": plan_no if is_match else None,
            "occupancy_certificate_no": occ_no if is_match else None,
            "completion_date": payload.get("building_completion_date")
            if is_match
            else None,
            "total_constructed_area_sqm": payload.get("total_constructed_area_sqm")
            if is_match
            else None,
            "provenance": "SIMULATED",
        }

        return DocumentVerificationResult(
            source_code=self.source_code,
            method=VerificationMethod.OFFICIAL_API,
            status=status,
            source_reference_number=document_reference,
            response_summary=summary,
            compared_fields=expected_fields or {},
            source_response_reference=f"MCGM-{document_reference}",
            environment=SourceEnvironment.SIMULATED,
            adapter_version=self.adapter_version,
            response_sha256=compute_canonical_sha256(summary),
        )

"""AIC-Verify — Synthetic State Fire and Emergency Services Directorate Connector (SRC_FIRE_SERVICES)."""

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
    / "SRC_FIRE_SERVICES_records.json"
)


def _get_default_payload() -> dict[str, Any]:
    if FIXTURE_PATH.is_file():
        with open(FIXTURE_PATH, "r", encoding="utf-8") as f:
            return json.load(f)
    return {
        "_source_code": "SRC_FIRE_SERVICES",
        "_provenance": "SIMULATED",
        "_environment": "SIMULATED",
        "aicte_permanent_id": "SYNTH-AICTE-0001",
        "fire_noc_certificate_number": "FIRE-NOC-MH-2025-7782",
        "issued_to": "Apex Institute of Technology",
        "issue_date": "2025-04-10",
        "valid_until": "2026-04-09",
        "compliance_status": "EXPIRED",
    }


class FireServicesConnector(BaseSourceConnector):
    """Synthetic adapter for State Fire and Emergency Services Directorate."""

    source_code = "SRC_FIRE_SERVICES"
    source_name = "State Fire and Emergency Services Directorate (SYNTHETIC)"
    source_type = SourceType.ISSUING_AUTHORITY
    integration_mode = "MOCK"
    adapter_version = "1.0.0-synthetic"
    official_domain = "mahafireservices.gov.in.synthetic"
    supported_document_types: ClassVar[list[int] | None] = [5]

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
                effective_from=datetime(2025, 4, 10, tzinfo=UTC),
                environment=SourceEnvironment.SIMULATED,
                adapter_version=self.adapter_version,
                status=SourceSyncStatus.FAILED,
                records_received=0,
                error_code="RECORD_NOT_FOUND",
                error_summary=f"No fire safety clearance records for {aicte_permanent_id}",
            )

        payload_sha256 = compute_canonical_sha256(payload)
        return InstitutionSnapshotResult(
            source_code=self.source_code,
            institution_id=institution_id,
            aicte_permanent_id=aicte_permanent_id,
            record_data=payload,
            source_system=self.source_code,
            source_reference=payload.get(
                "fire_noc_certificate_number", "FIRE-NOC-MH-2025-7782"
            ),
            payload_sha256=payload_sha256,
            effective_from=datetime(2025, 4, 10, tzinfo=UTC),
            effective_to=datetime(2026, 4, 9, tzinfo=UTC),
            source_updated_at=datetime(2025, 4, 10, tzinfo=UTC),
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
        canonical_noc = payload.get(
            "fire_noc_certificate_number", "FIRE-NOC-MH-2025-7782"
        )

        cleaned = document_reference.strip().replace(" ", "").upper()
        if ("VALID" in cleaned and "INVALID" not in cleaned) or "2026-9999" in cleaned:
            # Simulated current / valid fire NOC
            status = VerificationStatus.VERIFIED
            summary = {
                "queried_reference": document_reference,
                "certificate_found": True,
                "compliance_status": "VALID",
                "valid_until": "2027-04-09",
                "issuer": "Mumbai Fire Brigade (Simulated)",
                "provenance": "SIMULATED",
            }
        elif cleaned == canonical_noc.replace(" ", "").upper() or "7782" in cleaned:
            # Matches expired baseline fixture
            status = VerificationStatus.EXPIRED
            summary = {
                "queried_reference": document_reference,
                "certificate_found": True,
                "compliance_status": "EXPIRED",
                "issue_date": payload.get("issue_date"),
                "valid_until": payload.get("valid_until"),
                "issuer": "Mumbai Fire Brigade (Simulated)",
                "provenance": "SIMULATED",
            }
        else:
            status = VerificationStatus.MISMATCH
            summary = {
                "queried_reference": document_reference,
                "certificate_found": False,
                "compliance_status": "NOT_FOUND",
                "provenance": "SIMULATED",
            }

        return DocumentVerificationResult(
            source_code=self.source_code,
            method=VerificationMethod.OFFICIAL_PORTAL,
            status=status,
            source_reference_number=document_reference,
            response_summary=summary,
            compared_fields=expected_fields or {},
            source_response_reference=f"MAHAFIRE-{document_reference}",
            environment=SourceEnvironment.SIMULATED,
            adapter_version=self.adapter_version,
            response_sha256=compute_canonical_sha256(summary),
        )

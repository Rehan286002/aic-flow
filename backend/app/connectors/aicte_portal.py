"""AIC-Flow evidence adapter — Synthetic AICTE Master Institutional Portal Connector (SRC_AICTE_PORTAL)."""

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
    / "SRC_AICTE_PORTAL_institution.json"
)


def _get_default_payload() -> dict[str, Any]:
    if FIXTURE_PATH.is_file():
        with open(FIXTURE_PATH, "r", encoding="utf-8") as f:
            return json.load(f)
    return {
        "_source_code": "SRC_AICTE_PORTAL",
        "_provenance": "SIMULATED",
        "_environment": "SIMULATED",
        "aicte_permanent_id": "SYNTH-AICTE-0001",
        "institution_name": "Apex Institute of Technology",
        "legal_entity_name": "Apex Educational and Charitable Trust",
        "establishment_year": 1989,
        "address": {
            "campus_name": "Apex Technical Campus",
            "survey_number": "Survey No. 42/1, 42/2",
            "village_taluka": "Kurla",
            "district": "Mumbai Suburban",
            "state": "Maharashtra",
            "pincode": "400070",
        },
        "declared_coordinates": {"latitude": 19.0657, "longitude": 72.8792},
        "sanctioned_land_acres": 5.25,
        "approved_total_builtup_area_sqm": 14250.0,
    }


class AICTEPortalConnector(BaseSourceConnector):
    """Synthetic adapter for AICTE Master Institutional Portal records and receipts."""

    source_code = "SRC_AICTE_PORTAL"
    source_name = "AICTE Master Institutional Portal (SYNTHETIC)"
    source_type = SourceType.INTERNAL_REFERENCE
    integration_mode = "MOCK"
    adapter_version = "1.0.0-synthetic"
    official_domain = "aicte.gov.in.synthetic"
    supported_document_types: ClassVar[list[int] | None] = [1, 2]

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
            raise SourceUnavailableError(f"Simulated outage for {self.source_code}")
        if simulate_failure == "MALFORMED":
            raise MalformedPayloadError(
                f"Simulated malformed response from {self.source_code}"
            )

        payload = _get_default_payload()
        if aicte_permanent_id != payload.get("aicte_permanent_id"):
            # Unknown institution returns empty/failed snapshot
            return InstitutionSnapshotResult(
                source_code=self.source_code,
                institution_id=institution_id,
                aicte_permanent_id=aicte_permanent_id,
                record_data={},
                source_system=self.source_code,
                payload_sha256=compute_canonical_sha256({}),
                effective_from=datetime(1989, 6, 1, tzinfo=UTC),
                environment=SourceEnvironment.SIMULATED,
                adapter_version=self.adapter_version,
                status=SourceSyncStatus.FAILED,
                records_received=0,
                error_code="INSTITUTION_NOT_FOUND",
                error_summary=f"Institution ID {aicte_permanent_id} not found in AICTE master records.",
            )

        payload_sha256 = compute_canonical_sha256(payload)
        return InstitutionSnapshotResult(
            source_code=self.source_code,
            institution_id=institution_id,
            aicte_permanent_id=aicte_permanent_id,
            record_data=payload,
            source_system=self.source_code,
            source_reference=f"AICTE-REG-{aicte_permanent_id}",
            payload_sha256=payload_sha256,
            effective_from=datetime(1989, 6, 1, tzinfo=UTC),
            source_updated_at=datetime(2025, 4, 1, 10, 0, tzinfo=UTC),
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

        # Check for simulated payment receipts or institutional affidavit registrations
        cleaned_ref = document_reference.strip().upper()
        if "PAY" in cleaned_ref or "REC" in cleaned_ref:
            # Synthetic payment receipt resolution
            is_valid = cleaned_ref.startswith("AICTE-PAY-") or "VALID" in cleaned_ref
            status = (
                VerificationStatus.VERIFIED if is_valid else VerificationStatus.MISMATCH
            )
            summary = {
                "transaction_reference": document_reference,
                "portal_payment_status": "SUCCESS" if is_valid else "NOT_FOUND",
                "payment_gateway": "SBI-ePay-Simulated",
                "simulated_amount_inr": 150000.0 if is_valid else 0.0,
                "provenance": "SIMULATED",
            }
        else:
            is_valid = True
            status = VerificationStatus.VERIFIED
            summary = {
                "document_reference": document_reference,
                "master_registry_entry_found": True,
                "provenance": "SIMULATED",
            }

        return DocumentVerificationResult(
            source_code=self.source_code,
            method=VerificationMethod.OFFICIAL_PORTAL,
            status=status,
            source_reference_number=document_reference,
            response_summary=summary,
            compared_fields=expected_fields or {},
            source_response_reference=f"AICTE-REF-{cleaned_ref}",
            environment=SourceEnvironment.SIMULATED,
            adapter_version=self.adapter_version,
            response_sha256=compute_canonical_sha256(summary),
        )

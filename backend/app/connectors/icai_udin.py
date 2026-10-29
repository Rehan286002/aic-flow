"""AIC-Verify — Synthetic ICAI UDIN Verification Portal Connector (SRC_ICAI_UDIN)."""

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
    / "SRC_ICAI_UDIN_records.json"
)


def _get_default_payload() -> dict[str, Any]:
    if FIXTURE_PATH.is_file():
        with open(FIXTURE_PATH, "r", encoding="utf-8") as f:
            return json.load(f)
    return {
        "_source_code": "SRC_ICAI_UDIN",
        "_provenance": "SIMULATED",
        "_environment": "SIMULATED",
        "aicte_permanent_id": "SYNTH-AICTE-0001",
        "udin": "26045891AAAAAA1234",
        "ca_membership_number": "045891",
        "ca_name": "CA Suresh N. Khandelwal",
        "ca_firm_registration_number": "102458W",
        "client_name": "Apex Educational and Charitable Trust",
        "document_type": "AUDIT_REPORT_FORM_10B",
        "financial_year": "2024-25",
        "audit_date": "2025-09-28",
        "status": "ACTIVE",
    }


class ICAIUDINConnector(BaseSourceConnector):
    """Synthetic adapter for Institute of Chartered Accountants of India (ICAI) UDIN Portal."""

    source_code = "SRC_ICAI_UDIN"
    source_name = "ICAI UDIN Verification Portal (SYNTHETIC)"
    source_type = SourceType.DIGITAL_REPOSITORY
    integration_mode = "MOCK"
    adapter_version = "1.0.0-synthetic"
    official_domain = "udin.icai.org.synthetic"
    supported_document_types: ClassVar[list[int] | None] = [7]

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
                effective_from=datetime(2025, 9, 28, tzinfo=UTC),
                environment=SourceEnvironment.SIMULATED,
                adapter_version=self.adapter_version,
                status=SourceSyncStatus.FAILED,
                records_received=0,
                error_code="RECORD_NOT_FOUND",
                error_summary=f"No UDIN records on file for {aicte_permanent_id}",
            )

        payload_sha256 = compute_canonical_sha256(payload)
        return InstitutionSnapshotResult(
            source_code=self.source_code,
            institution_id=institution_id,
            aicte_permanent_id=aicte_permanent_id,
            record_data=payload,
            source_system=self.source_code,
            source_reference=payload.get("udin", "26045891AAAAAA1234"),
            payload_sha256=payload_sha256,
            effective_from=datetime(2025, 9, 28, tzinfo=UTC),
            source_updated_at=datetime(2025, 9, 28, tzinfo=UTC),
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
        canonical_udin = payload.get("udin", "26045891AAAAAA1234")

        cleaned = document_reference.strip().replace(" ", "").upper()
        if "REVOKED" in cleaned:
            status = VerificationStatus.MISMATCH
            summary = {
                "queried_udin": document_reference,
                "udin_found": True,
                "status": "REVOKED",
                "revocation_reason": "Withdrawn by practicing Chartered Accountant",
                "provenance": "SIMULATED",
            }
        elif "INVALID" in cleaned:
            status = VerificationStatus.MISMATCH
            summary = {
                "queried_udin": document_reference,
                "udin_found": False,
                "status": "NOT_FOUND",
                "provenance": "SIMULATED",
            }
        elif (
            cleaned == canonical_udin
            or ("VALID" in cleaned and "INVALID" not in cleaned)
            or "AAAAAA1234" in cleaned
        ):
            status = VerificationStatus.VERIFIED
            summary = {
                "queried_udin": document_reference,
                "udin_found": True,
                "status": "ACTIVE",
                "ca_membership_number": payload.get("ca_membership_number"),
                "ca_name": payload.get("ca_name"),
                "ca_firm_registration_number": payload.get(
                    "ca_firm_registration_number"
                ),
                "client_name": payload.get("client_name"),
                "financial_year": payload.get("financial_year"),
                "audit_date": payload.get("audit_date"),
                "document_type": payload.get("document_type"),
                "provenance": "SIMULATED",
            }
        else:
            status = VerificationStatus.MISMATCH
            summary = {
                "queried_udin": document_reference,
                "udin_found": False,
                "status": "NOT_FOUND",
                "provenance": "SIMULATED",
            }

        return DocumentVerificationResult(
            source_code=self.source_code,
            method=VerificationMethod.OFFICIAL_PORTAL,
            status=status,
            source_reference_number=document_reference,
            response_summary=summary,
            compared_fields=expected_fields or {},
            source_response_reference=f"ICAI-UDIN-{document_reference}",
            environment=SourceEnvironment.SIMULATED,
            adapter_version=self.adapter_version,
            response_sha256=compute_canonical_sha256(summary),
        )

"""AIC-Verify — Synthetic ISRO Bhuvan / Survey of India Geoportal Connector (SRC_BHUVAN_GEOMAP)."""

from __future__ import annotations

import json
import math
import uuid
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, ClassVar

from app.connectors.base import (
    BaseSourceConnector,
    CoordinateLookupResult,
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
    / "SRC_BHUVAN_GEOMAP_records.json"
)

# Coarse boundary bounds for Indian territorial territory (plausibility check)
INDIA_BOUNDS = {
    "min_lat": 8.0,
    "max_lat": 37.5,
    "min_lon": 68.0,
    "max_lon": 97.5,
}

REGISTERED_COORDS = {"lat": 19.0657, "lon": 72.8792}


def _haversine_distance_meters(
    lat1: float, lon1: float, lat2: float, lon2: float
) -> float:
    """Calculate approximate distance in meters between two lat/lon coordinates."""
    r = 6371000.0  # Earth radius in meters
    phi1 = math.radians(lat1)
    phi2 = math.radians(lat2)
    delta_phi = math.radians(lat2 - lat1)
    delta_lambda = math.radians(lon2 - lon1)

    a = (
        math.sin(delta_phi / 2.0) ** 2
        + math.cos(phi1) * math.cos(phi2) * math.sin(delta_lambda / 2.0) ** 2
    )
    c = 2.0 * math.atan2(math.sqrt(a), math.sqrt(1.0 - a))
    return r * c


def _get_default_payload() -> dict[str, Any]:
    if FIXTURE_PATH.is_file():
        with open(FIXTURE_PATH, "r", encoding="utf-8") as f:
            return json.load(f)
    return {
        "_source_code": "SRC_BHUVAN_GEOMAP",
        "_provenance": "SIMULATED",
        "_environment": "SIMULATED",
        "aicte_permanent_id": "SYNTH-AICTE-0001",
        "campus_name": "Apex Institute of Technology, Kurla Campus",
        "registered_entrance_coordinates": {"latitude": 19.0657, "longitude": 72.8792},
        "cadastral_survey_numbers": ["42/1", "42/2"],
        "geospatial_resolution": {
            "resolved_state": "Maharashtra",
            "resolved_district": "Mumbai Suburban",
            "resolved_taluka": "Kurla",
            "resolved_pincode": "400070",
        },
    }


class BhuvanGeoportalConnector(BaseSourceConnector):
    """Synthetic adapter for ISRO Bhuvan / Survey of India geospatial verification."""

    source_code = "SRC_BHUVAN_GEOMAP"
    source_name = "ISRO Bhuvan / Survey of India Geoportal (SYNTHETIC)"
    source_type = SourceType.GOVERNMENT_PORTAL
    integration_mode = "MOCK"
    adapter_version = "1.0.0-synthetic"
    official_domain = "bhuvan.nrsc.gov.in.synthetic"
    supported_document_types: ClassVar[list[int] | None] = [6]

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
                effective_from=datetime(2025, 1, 1, tzinfo=UTC),
                environment=SourceEnvironment.SIMULATED,
                adapter_version=self.adapter_version,
                status=SourceSyncStatus.FAILED,
                records_received=0,
                error_code="RECORD_NOT_FOUND",
                error_summary=f"No cadastral geo-record found for {aicte_permanent_id}",
            )

        payload_sha256 = compute_canonical_sha256(payload)
        return InstitutionSnapshotResult(
            source_code=self.source_code,
            institution_id=institution_id,
            aicte_permanent_id=aicte_permanent_id,
            record_data=payload,
            source_system=self.source_code,
            source_reference="BHUVAN-SURVEY-42-MUM",
            payload_sha256=payload_sha256,
            effective_from=datetime(2025, 1, 1, tzinfo=UTC),
            source_updated_at=datetime(2025, 12, 15, tzinfo=UTC),
            environment=SourceEnvironment.SIMULATED,
            adapter_version=self.adapter_version,
            status=SourceSyncStatus.SUCCEEDED,
            records_received=1,
        )

    def lookup_coordinates(
        self,
        latitude: float,
        longitude: float,
        correlation_id: str | None = None,
        simulate_failure: str | None = None,
    ) -> CoordinateLookupResult:
        """Resolve geographical coordinates against synthetic Bhuvan cadastral layer."""
        if simulate_failure == "TIMEOUT":
            raise SourceTimeoutError(f"Simulated timeout in {self.source_code}")
        if simulate_failure == "UNAVAILABLE":
            raise SourceUnavailableError(f"Simulated outage in {self.source_code}")

        # Coarse bounding box plausibility check
        is_coarse_valid = (
            INDIA_BOUNDS["min_lat"] <= latitude <= INDIA_BOUNDS["max_lat"]
            and INDIA_BOUNDS["min_lon"] <= longitude <= INDIA_BOUNDS["max_lon"]
        )

        distance = _haversine_distance_meters(
            latitude, longitude, REGISTERED_COORDS["lat"], REGISTERED_COORDS["lon"]
        )

        # Distance heuristic: within 500m is considered matching the registered campus
        is_match = is_coarse_valid and (distance <= 500.0)
        status = (
            VerificationStatus.VERIFIED
            if is_match
            else (
                VerificationStatus.MISMATCH
                if is_coarse_valid
                else VerificationStatus.FAILED
            )
        )

        details = {
            "queried_latitude": latitude,
            "queried_longitude": longitude,
            "registered_latitude": REGISTERED_COORDS["lat"],
            "registered_longitude": REGISTERED_COORDS["lon"],
            "distance_meters": round(distance, 2),
            "coarse_bounds_valid": is_coarse_valid,
            "resolved_state": "Maharashtra" if is_coarse_valid else "OUTSIDE_INDIA",
            "resolved_district": "Mumbai Suburban" if is_coarse_valid else None,
            "resolved_pincode": "400070" if is_coarse_valid else None,
            "provenance": "SIMULATED",
        }

        return CoordinateLookupResult(
            source_code=self.source_code,
            latitude=latitude,
            longitude=longitude,
            status=status,
            resolved_state=details["resolved_state"],
            resolved_district=details["resolved_district"],
            resolved_pincode=details["resolved_pincode"],
            coarse_bounds_valid=is_coarse_valid,
            distance_meters=round(distance, 2),
            details=details,
            environment=SourceEnvironment.SIMULATED,
            adapter_version=self.adapter_version,
            response_sha256=compute_canonical_sha256(details),
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
            raise SourceUnavailableError(f"Simulated outage in {self.source_code}")

        # Try to parse lat/lon from expected_fields if provided
        lat = expected_fields.get("latitude") if expected_fields else None
        lon = expected_fields.get("longitude") if expected_fields else None

        if lat is not None and lon is not None:
            coord_res = self.lookup_coordinates(float(lat), float(lon))
            return DocumentVerificationResult(
                source_code=self.source_code,
                method=VerificationMethod.OFFICIAL_API,
                status=coord_res.status,
                source_reference_number=document_reference,
                response_summary=coord_res.details,
                compared_fields=expected_fields or {},
                source_response_reference=f"BHUVAN-LOOKUP-{lat}-{lon}",
                environment=SourceEnvironment.SIMULATED,
                adapter_version=self.adapter_version,
                response_sha256=coord_res.response_sha256,
            )

        summary = {
            "queried_reference": document_reference,
            "layer": "BHUVAN_2D_SATELLITE",
            "provenance": "SIMULATED",
        }
        return DocumentVerificationResult(
            source_code=self.source_code,
            method=VerificationMethod.OFFICIAL_PORTAL,
            status=VerificationStatus.VERIFIED,
            source_reference_number=document_reference,
            response_summary=summary,
            compared_fields=expected_fields or {},
            source_response_reference=f"BHUVAN-{document_reference}",
            environment=SourceEnvironment.SIMULATED,
            adapter_version=self.adapter_version,
            response_sha256=compute_canonical_sha256(summary),
        )

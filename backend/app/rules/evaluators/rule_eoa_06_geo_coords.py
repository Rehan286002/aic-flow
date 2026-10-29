"""AIC-Verify — Rule Evaluator for EOA-SD-06: Satellite Map and Entrance Coordinates.

Regulatory Reference:
AICTE Approval Process Handbook (APH) 2024–2027 Annexure 2.1 Item vi:
Satellite map showing geographical location of the land, with latitude and longitude
at the entrance of the main building.

Safeguards Enforced:
1. Reuses exact Phase 4 coordinate plausibility helpers (6.0 <= lat <= 38.0, 68.0 <= lon <= 98.0).
2. Coarse bounding box is explicitly framed as a plausibility check, not proof of boundaries.
3. Distance thresholds remain advisory heuristics only; deviations > 5 km produce advisory
   observations (WARNING/INFRASTRUCTURE_OBSERVATION), NOT automatic statutory DEFICIENT outcomes.
4. Uses only fields actually returned by existing Bhuvan connector (distance_meters, resolved_state,
   resolved_district, coarse_bounds_valid).
5. All synthetic outcomes explicitly labelled SIMULATED.
"""

from __future__ import annotations

import logging
from typing import Any

from app.connectors.bhuvan_geomap import BhuvanGeoportalConnector
from app.models.enums import FindingCategory, FindingSeverity
from app.rules.base import (
    AuthoritativeFieldResolver,
    BaseRuleEvaluator,
    FindingDraft,
    FindingEvidenceDraft,
    RuleEvaluationContext,
    RuleEvaluationOutcome,
)
from app.services.field_extraction_service import (
    is_valid_indian_latitude,
    is_valid_indian_longitude,
)

logger = logging.getLogger(__name__)


class RuleEvaluatorEOA06(BaseRuleEvaluator):
    """Evaluates EOA-SD-06 (Satellite Map and Entrance Coordinates) compliance."""

    rule_code = "RULE_EOA_06_GEO_COORDS"

    def evaluate(self, ctx: RuleEvaluationContext) -> RuleEvaluationOutcome:
        findings: list[FindingDraft] = []

        # 1. Document Upload Presence
        if not ctx.document_version:
            findings.append(
                FindingDraft(
                    category=FindingCategory.MISSING_DOCUMENT,
                    severity=FindingSeverity.HIGH,
                    title="Satellite Map Document Missing",
                    internal_reason=(
                        "Mandatory requirement EOA-SD-06 has no uploaded document version. "
                        "AICTE APH Annexure 2.1 Item vi mandates satellite map showing entrance GPS coordinates."
                    ),
                    recommended_action="Upload satellite map document showing main entrance coordinates.",
                    is_internal_only=False,
                )
            )
            return RuleEvaluationOutcome(
                status="DEFICIENT",
                expected_value={"document_uploaded": True},
                observed_value={"document_uploaded": False},
                explanation="Satellite map document is missing from the application submission.",
                findings=findings,
            )

        # 2. Check for Disputed Fields
        disputed_fields = [f for f in ctx.fields.values() if f.is_disputed]
        if disputed_fields:
            for df in disputed_fields:
                findings.append(AuthoritativeFieldResolver.build_dispute_finding(df))
            return RuleEvaluationOutcome(
                status="UNABLE_TO_DETERMINE",
                expected_value={"dispute_free": True},
                observed_value={
                    "disputed_fields": [df.field_code for df in disputed_fields]
                },
                explanation="Geospatial candidate coordinates contain conflicting reviews. Determination halted.",
                findings=findings,
            )

        # 3. Check for Empty Extractions
        if not ctx.fields:
            findings.append(
                FindingDraft(
                    category=FindingCategory.INCOMPLETE_DOCUMENT,
                    severity=FindingSeverity.MEDIUM,
                    title="Geospatial Coordinates Unextracted",
                    internal_reason="Satellite map uploaded but latitude/longitude coordinates could not be parsed.",
                    recommended_action="Review map imagery clarity or conduct manual auditor verification.",
                    is_internal_only=True,
                )
            )
            return RuleEvaluationOutcome(
                status="UNABLE_TO_DETERMINE",
                expected_value={"coordinates_extracted": True},
                observed_value={"coordinates_extracted": False},
                explanation="Satellite map entrance coordinates could not be extracted by automated pipeline.",
                findings=findings,
            )

        lat_field = ctx.fields.get("latitude")
        lon_field = ctx.fields.get("longitude")

        lat_val: float | None = None
        lon_val: float | None = None

        if lat_field and isinstance(lat_field.normalized_value, dict):
            lat_val = lat_field.normalized_value.get("decimal_degrees")
        if lon_field and isinstance(lon_field.normalized_value, dict):
            lon_val = lon_field.normalized_value.get("decimal_degrees")

        # Fallback raw parse
        if lat_val is None and lat_field and lat_field.raw_value:
            import re

            m = re.search(r"(\d+\.\d+)", lat_field.raw_value)
            if m:
                lat_val = float(m.group(1))
        if lon_val is None and lon_field and lon_field.raw_value:
            import re

            m = re.search(r"(\d+\.\d+)", lon_field.raw_value)
            if m:
                lon_val = float(m.group(1))

        if lat_val is None or lon_val is None:
            findings.append(
                FindingDraft(
                    category=FindingCategory.INCOMPLETE_DOCUMENT,
                    severity=FindingSeverity.HIGH,
                    title="Incomplete Latitude or Longitude Coordinate Pair",
                    internal_reason=f"Coordinates partially extracted: latitude={lat_val}, longitude={lon_val}.",
                    recommended_action="Ensure both latitude and longitude are clearly marked on the satellite map.",
                    is_internal_only=False,
                )
            )
            return RuleEvaluationOutcome(
                status="DEFICIENT",
                expected_value={
                    "latitude_extracted": True,
                    "longitude_extracted": True,
                },
                observed_value={"latitude": lat_val, "longitude": lon_val},
                explanation="Both latitude and longitude entrance coordinates are required under APH Annexure 2.1 Item vi.",
                findings=findings,
            )

        observed: dict[str, Any] = {
            "latitude": lat_val,
            "longitude": lon_val,
            "provenance": "SIMULATED",
        }

        # 4. Phase 4 Coordinate Plausibility Check (Safeguard 3: Plausibility, not proof)
        is_lat_plausible = is_valid_indian_latitude(lat_val)
        is_lon_plausible = is_valid_indian_longitude(lon_val)
        observed["coarse_bounds_plausibility_check"] = (
            is_lat_plausible and is_lon_plausible
        )

        if not (is_lat_plausible and is_lon_plausible):
            findings.append(
                FindingDraft(
                    category=FindingCategory.FIELD_MISMATCH,
                    severity=FindingSeverity.HIGH,
                    title="Entrance Coordinates Fail Indian Landmass Plausibility Check",
                    internal_reason=(
                        f"Extracted coordinates ({lat_val:.4f}° N, {lon_val:.4f}° E) fall outside the "
                        "coarse Indian landmass plausibility bounds (6.0°–38.0° N, 68.0°–98.0° E)."
                    ),
                    recommended_action="Provide accurate campus entrance coordinates located in India.",
                    is_internal_only=False,
                    evidence_items=[
                        FindingEvidenceDraft(
                            document_version_id=ctx.document_version.document_version_id,
                            extracted_field_id=lat_field.extracted_field_id
                            if lat_field
                            else None,
                            evidence_type="EXTRACTED_FIELD",
                            evidence_summary=f"Extracted coords: {lat_val}, {lon_val}",
                        )
                    ],
                )
            )
            return RuleEvaluationOutcome(
                status="DEFICIENT",
                expected_value={"plausible_indian_coordinates": True},
                observed_value=observed,
                explanation="Extracted coordinates fail coarse Indian territory plausibility check.",
                findings=findings,
            )

        # 5. Query Existing Synthetic Bhuvan Connector (using only actual returned fields)
        bhuvan = BhuvanGeoportalConnector()
        lookup_res = bhuvan.lookup_coordinates(latitude=lat_val, longitude=lon_val)

        observed["distance_meters"] = lookup_res.distance_meters
        observed["resolved_state"] = lookup_res.resolved_state
        observed["resolved_district"] = lookup_res.resolved_district
        observed["coarse_bounds_valid"] = lookup_res.coarse_bounds_valid

        dist_m = lookup_res.distance_meters or 0.0

        # 6. Apply Distance Bands as Advisory Heuristics Only (Safeguard 3)
        # > 5 km must NOT automatically produce a statutory DEFICIENT result!
        outcome_status = "SATISFIED"
        if dist_m > 5000.0:
            outcome_status = "WARNING"
            findings.append(
                FindingDraft(
                    category=FindingCategory.INFRASTRUCTURE_OBSERVATION,
                    severity=FindingSeverity.MEDIUM,
                    title="Geospatial Proximity Advisory: Deviation > 5 km [SIMULATED]",
                    internal_reason=(
                        f"Extracted entrance coordinates deviate by {dist_m / 1000.0:.2f} km from the registered "
                        f"campus entrance coordinates in the synthetic Bhuvan cadastral layer [SIMULATED]. "
                        "Under regulatory guidelines, this distance band is treated as an advisory heuristic observation "
                        "and does not constitute an automatic statutory failure."
                    ),
                    recommended_action="Auditor to verify satellite map imagery against cadastral survey parcel.",
                    is_internal_only=True,
                )
            )
        elif dist_m > 1000.0:
            outcome_status = "WARNING"
            findings.append(
                FindingDraft(
                    category=FindingCategory.INFRASTRUCTURE_OBSERVATION,
                    severity=FindingSeverity.INFO,
                    title="Geospatial Proximity Advisory: Deviation between 1 km and 5 km [SIMULATED]",
                    internal_reason=(
                        f"Extracted entrance coordinates deviate by {dist_m:.1f} meters from registered entrance "
                        "in synthetic Bhuvan layer [SIMULATED] (advisory observation)."
                    ),
                    recommended_action="Confirm location of specific main building entrance gate.",
                    is_internal_only=True,
                )
            )

        explanation = (
            f"Entrance coordinates ({lat_val:.4f}° N, {lon_val:.4f}° E) verified plausible within Indian landmass; "
            f"geospatial distance to registered entrance is {dist_m:.1f}m (advisory heuristic) [SIMULATED]."
        )

        return RuleEvaluationOutcome(
            status=outcome_status,
            expected_value={"plausible_coordinates": True, "provenance": "SIMULATED"},
            observed_value=observed,
            explanation=explanation,
            findings=findings,
        )

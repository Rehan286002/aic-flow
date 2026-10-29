"""AIC-Verify — Phase 5 Batch 1: Synthetic Source Connector & Registry Test Suite.

Verifies:
- All 6 synthetic provider adapters.
- Explicit SIMULATED provenance tagging.
- Canonical SHA-256 calculation and key order invariance.
- Idempotent seeding and unchanged snapshot suppression.
- Snapshot versioning and historical snapshot immutability.
- Simulated timeout, unavailability, and malformed payload resilience.
- Document verification attempts and compared fields persistence.
- Unknown source rejection.
"""

from __future__ import annotations

from datetime import UTC, datetime

import pytest
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.connectors.aicte_portal import AICTEPortalConnector
from app.connectors.base import (
    BaseSourceConnector,
    InstitutionSnapshotResult,
    MalformedPayloadError,
    SourceEnvironment,
    SourceSyncStatus,
    SourceTimeoutError,
    SourceUnavailableError,
    UnknownSourceError,
    compute_canonical_sha256,
)
from app.connectors.bhuvan_geomap import BhuvanGeoportalConnector
from app.connectors.fire_services import FireServicesConnector
from app.connectors.icai_udin import ICAIUDINConnector
from app.connectors.land_revenue import LandRevenueConnector
from app.connectors.municipal_building import MunicipalBuildingConnector
from app.connectors.registry import SourceConnectorRegistry, connector_registry
from app.models.document_version import DocumentVersion
from app.models.enums import VerificationMethod, VerificationStatus
from app.models.institution import Institution
from app.models.institution_record_version import InstitutionRecordVersion
from app.models.verification_attempt import VerificationAttempt
from app.models.verification_source import VerificationSource
from app.services.source_connector_service import (
    SourceConnectorService,
)

DEMO_INST_ID = "SYNTH-AICTE-0001"


# --- Unit Tests: Connector Implementations & Registry ---


def test_six_connectors_registered():
    """All 6 synthetic provider connectors are registered and discoverable."""
    expected_codes = [
        "SRC_AICTE_PORTAL",
        "SRC_REVENUE_LAND",
        "SRC_MUNICIPAL_BLDG",
        "SRC_FIRE_SERVICES",
        "SRC_ICAI_UDIN",
        "SRC_BHUVAN_GEOMAP",
    ]
    registered = connector_registry.list_source_codes()
    for code in expected_codes:
        assert code in registered
        connector = connector_registry.get(code)
        assert isinstance(connector, BaseSourceConnector)
        assert connector.source_code == code
        assert connector.health_check() is True


def test_unknown_source_code_rejected():
    """Requesting an unregistered source code raises UnknownSourceError."""
    registry = SourceConnectorRegistry()
    with pytest.raises(UnknownSourceError, match="No connector registered"):
        registry.get("SRC_NONEXISTENT_PORTAL")


def test_canonical_sha256_reproducibility():
    """Canonical SHA-256 computation is strictly key-order invariant."""
    dict_a = {"name": "Apex", "year": 1989, "details": {"active": True, "code": "AIT"}}
    dict_b = {"details": {"code": "AIT", "active": True}, "year": 1989, "name": "Apex"}

    hash_a = compute_canonical_sha256(dict_a)
    hash_b = compute_canonical_sha256(dict_b)

    assert hash_a == hash_b
    assert len(hash_a) == 64


def test_aicte_portal_connector_snapshot_and_simulated_provenance():
    """AICTE Portal connector returns synthetic institutional record with SIMULATED provenance."""
    connector = AICTEPortalConnector()
    result = connector.fetch_institution_snapshot(DEMO_INST_ID)

    assert result.status == SourceSyncStatus.SUCCEEDED
    assert result.environment == SourceEnvironment.SIMULATED
    assert result.aicte_permanent_id == DEMO_INST_ID
    assert result.record_data["_provenance"] == "SIMULATED"
    assert result.record_data["establishment_year"] == 1989
    assert result.source_reference == "AICTE-REG-SYNTH-AICTE-0001"
    assert len(result.payload_sha256) == 64

    # Verification of simulated payment
    ver_res = connector.verify_document_reference("AICTE-PAY-2026-9812")
    assert ver_res.status == VerificationStatus.VERIFIED
    assert ver_res.environment == SourceEnvironment.SIMULATED
    assert ver_res.response_summary["portal_payment_status"] == "SUCCESS"


def test_land_revenue_connector_verification():
    """Land Revenue connector matches valid deed references and detects unknown records."""
    connector = LandRevenueConnector()
    snap = connector.fetch_institution_snapshot(DEMO_INST_ID)

    assert snap.status == SourceSyncStatus.SUCCEEDED
    assert snap.environment == SourceEnvironment.SIMULATED
    assert "TITLE-DEED-REG-1989-8842" in snap.source_reference

    # Valid deed reference
    match_res = connector.verify_document_reference("TITLE-DEED-REG-1989-8842")
    assert match_res.status == VerificationStatus.VERIFIED
    assert match_res.response_summary["registered_deed_found"] is True

    # Mismatch deed reference
    mismatch_res = connector.verify_document_reference("UNKNOWN-DEED-2020-0000")
    assert mismatch_res.status == VerificationStatus.MISMATCH
    assert mismatch_res.response_summary["registered_deed_found"] is False


def test_municipal_building_connector_verification():
    """Municipal Building connector verifies occupancy certificate and sanction plan order."""
    connector = MunicipalBuildingConnector()
    snap = connector.fetch_institution_snapshot(DEMO_INST_ID)

    assert snap.status == SourceSyncStatus.SUCCEEDED
    assert snap.record_data["building_completion_date"] == "1990-05-15"

    # Verify occupancy certificate
    occ_res = connector.verify_document_reference("MCGM-OCC-1990-0891")
    assert occ_res.status == VerificationStatus.VERIFIED
    assert occ_res.response_summary["completion_date"] == "1990-05-15"

    # Unknown certificate
    bad_res = connector.verify_document_reference("MCGM-UNKNOWN-9999")
    assert bad_res.status == VerificationStatus.MISMATCH


def test_fire_services_connector_expiration_and_validity():
    """Fire Services connector detects expired NOC vs current certificate."""
    connector = FireServicesConnector()
    snap = connector.fetch_institution_snapshot(DEMO_INST_ID)

    assert snap.status == SourceSyncStatus.SUCCEEDED
    assert snap.record_data["compliance_status"] == "EXPIRED"

    # Matches baseline expired NOC (FIRE-NOC-MH-2025-7782 expired on 2026-04-09)
    expired_res = connector.verify_document_reference("FIRE-NOC-MH-2025-7782")
    assert expired_res.status == VerificationStatus.EXPIRED
    assert expired_res.response_summary["compliance_status"] == "EXPIRED"
    assert expired_res.response_summary["valid_until"] == "2026-04-09"

    # Valid simulated renewal certificate
    valid_res = connector.verify_document_reference("FIRE-NOC-MH-2026-9999-VALID")
    assert valid_res.status == VerificationStatus.VERIFIED
    assert valid_res.response_summary["compliance_status"] == "VALID"


def test_icai_udin_connector_verification_and_revocation():
    """ICAI UDIN connector verifies active UDINs and detects revoked or nonexistent UDINs."""
    connector = ICAIUDINConnector()
    snap = connector.fetch_institution_snapshot(DEMO_INST_ID)

    assert snap.status == SourceSyncStatus.SUCCEEDED
    assert snap.record_data["ca_membership_number"] == "045891"

    # Active UDIN
    udin_res = connector.verify_document_reference("26045891AAAAAA1234")
    assert udin_res.status == VerificationStatus.VERIFIED
    assert udin_res.response_summary["status"] == "ACTIVE"
    assert udin_res.response_summary["ca_membership_number"] == "045891"

    # Revoked UDIN
    revoked_res = connector.verify_document_reference("26045891REVOKED123")
    assert revoked_res.status == VerificationStatus.MISMATCH
    assert revoked_res.response_summary["status"] == "REVOKED"

    # Nonexistent UDIN
    not_found_res = connector.verify_document_reference("99999999INVALID000")
    assert not_found_res.status == VerificationStatus.MISMATCH
    assert not_found_res.response_summary["status"] == "NOT_FOUND"


def test_bhuvan_geomap_coordinates_and_bounds():
    """Bhuvan Geoportal connector verifies Indian boundary bounds and geodesic distance."""
    connector = BhuvanGeoportalConnector()

    # Valid coordinates close to registered campus entrance (19.0657, 72.8792)
    near_res = connector.lookup_coordinates(19.0658, 72.8793)
    assert near_res.status == VerificationStatus.VERIFIED
    assert near_res.coarse_bounds_valid is True
    assert near_res.distance_meters is not None
    assert near_res.distance_meters < 50.0  # Within ~15 meters
    assert near_res.resolved_state == "Maharashtra"
    assert near_res.environment == SourceEnvironment.SIMULATED

    # Coordinate in India but far away (e.g. New Delhi 28.6139, 77.2090)
    delhi_res = connector.lookup_coordinates(28.6139, 77.2090)
    assert (
        delhi_res.status == VerificationStatus.MISMATCH
    )  # Plausible in India, but mismatch with campus
    assert delhi_res.coarse_bounds_valid is True
    assert delhi_res.distance_meters > 500000.0  # > 500km away

    # Coordinate completely outside India (e.g. London 51.5074, -0.1278)
    foreign_res = connector.lookup_coordinates(51.5074, -0.1278)
    assert foreign_res.status == VerificationStatus.FAILED
    assert foreign_res.coarse_bounds_valid is False
    assert foreign_res.resolved_state == "OUTSIDE_INDIA"


def test_connector_failure_simulations():
    """All connectors raise appropriate exceptions when failure simulation is requested."""
    connectors = [
        AICTEPortalConnector(),
        LandRevenueConnector(),
        MunicipalBuildingConnector(),
        FireServicesConnector(),
        ICAIUDINConnector(),
        BhuvanGeoportalConnector(),
    ]

    for conn in connectors:
        with pytest.raises(SourceTimeoutError, match="Simulated timeout"):
            conn.fetch_institution_snapshot(DEMO_INST_ID, simulate_failure="TIMEOUT")

        with pytest.raises(SourceUnavailableError, match="Simulated"):
            conn.fetch_institution_snapshot(
                DEMO_INST_ID, simulate_failure="UNAVAILABLE"
            )

        with pytest.raises(MalformedPayloadError, match="Simulated malformed"):
            conn.fetch_institution_snapshot(DEMO_INST_ID, simulate_failure="MALFORMED")

        with pytest.raises(SourceTimeoutError, match="Simulated timeout"):
            conn.verify_document_reference("REF-123", simulate_failure="TIMEOUT")

        with pytest.raises(SourceUnavailableError, match="Simulated"):
            conn.verify_document_reference("REF-123", simulate_failure="UNAVAILABLE")


# --- Integration Tests: Database Persistence & Service Layer ---


def test_seed_or_update_verification_sources(db: Session):
    """Seed verification sources idempotently creates records with MOCK mode and SIMULATED flags."""
    service = SourceConnectorService()

    # First run
    counts_1 = service.seed_or_update_verification_sources(db)
    assert counts_1["inserted"] + counts_1["unchanged"] == 6

    # Verify rows in database
    sources = db.scalars(select(VerificationSource)).all()
    assert len(sources) == 6
    for s in sources:
        assert s.is_authorized is True
        assert s.is_enabled is True
        assert s.integration_mode == "MOCK"

    # Second run is completely idempotent
    counts_2 = service.seed_or_update_verification_sources(db)
    assert counts_2["inserted"] == 0
    assert counts_2["updated"] == 0
    assert counts_2["unchanged"] == 6


def test_sync_institution_source_lifecycle(db: Session):
    """Sync creates SourceSyncRun audit log and versioned InstitutionRecordVersion."""
    service = SourceConnectorService()
    service.seed_or_update_verification_sources(db)

    inst = db.scalar(
        select(Institution).where(
            Institution.aicte_permanent_institution_id == DEMO_INST_ID
        )
    )
    assert inst is not None

    # First sync creates v1
    sync_run_1, version_1 = service.sync_institution_source(
        db=db,
        institution_id=inst.institution_id,
        source_code="SRC_AICTE_PORTAL",
        sync_kind="ON_DEMAND",
    )
    assert sync_run_1.status == SourceSyncStatus.SUCCEEDED
    assert sync_run_1.environment == "SIMULATED"
    assert sync_run_1.records_received == 1
    assert version_1 is not None
    assert version_1.source_system == "SRC_AICTE_PORTAL"
    assert len(version_1.source_payload_sha256) == 64

    # Second sync with unchanged payload returns same version without creating redundant row
    sync_run_2, version_2 = service.sync_institution_source(
        db=db,
        institution_id=inst.institution_id,
        source_code="SRC_AICTE_PORTAL",
        sync_kind="ON_DEMAND",
    )
    assert sync_run_2.status == SourceSyncStatus.SUCCEEDED
    assert (
        version_2.institution_record_version_id
        == version_1.institution_record_version_id
    )
    assert version_2.record_version == version_1.record_version


def test_sync_institution_source_failure_handling(db: Session):
    """Simulated failure marks SourceSyncRun as FAILED and returns None without creating a snapshot."""
    service = SourceConnectorService()
    service.seed_or_update_verification_sources(db)

    inst = db.scalar(
        select(Institution).where(
            Institution.aicte_permanent_institution_id == DEMO_INST_ID
        )
    )

    sync_run, version = service.sync_institution_source(
        db=db,
        institution_id=inst.institution_id,
        source_code="SRC_FIRE_SERVICES",
        simulate_failure="UNAVAILABLE",
    )
    assert sync_run.status == SourceSyncStatus.FAILED
    assert sync_run.error_code == "SourceUnavailableError"
    assert version is None


def test_verify_document_reference_attempt_persistence(db: Session):
    """Document reference verification creates a persistent VerificationAttempt record."""
    service = SourceConnectorService()
    service.seed_or_update_verification_sources(db)

    # Get any clean document version for demo institution
    doc_ver = db.scalar(
        select(DocumentVersion).order_by(DocumentVersion.version_number.desc())
    )
    assert doc_ver is not None

    # Perform fire NOC verification
    attempt = service.verify_document_reference(
        db=db,
        document_version_id=doc_ver.document_version_id,
        source_code="SRC_FIRE_SERVICES",
        method=VerificationMethod.OFFICIAL_PORTAL,
        reference_number="FIRE-NOC-MH-2025-7782",
        expected_fields={"certificate_number": "FIRE-NOC-MH-2025-7782"},
    )

    assert attempt.verification_attempt_id is not None
    assert attempt.status == VerificationStatus.EXPIRED
    assert attempt.response_summary["compliance_status"] == "EXPIRED"
    assert attempt.response_summary["provenance"] == "SIMULATED"
    assert attempt.completed_at is not None

    # Query directly from DB to verify persistence
    persisted = db.scalar(
        select(VerificationAttempt).where(
            VerificationAttempt.verification_attempt_id
            == attempt.verification_attempt_id
        )
    )
    assert persisted is not None
    assert persisted.status == VerificationStatus.EXPIRED


def test_snapshot_versioning_preserves_history(db: Session, monkeypatch):
    """An intentional update to source data creates a new record_version while preserving previous version."""
    service = SourceConnectorService()
    service.seed_or_update_verification_sources(db)

    inst = db.scalar(
        select(Institution).where(
            Institution.aicte_permanent_institution_id == DEMO_INST_ID
        )
    )
    assert inst is not None

    # Initial sync
    _, v1 = service.sync_institution_source(db, inst.institution_id, "SRC_AICTE_PORTAL")
    assert v1 is not None
    original_sha = v1.source_payload_sha256
    v1_id = v1.institution_record_version_id
    v1_ver = v1.record_version

    # Simulate updated data from provider
    connector = service.registry.get("SRC_AICTE_PORTAL")
    original_fetch = connector.fetch_institution_snapshot

    def mock_fetch_updated(*args, **kwargs):
        res = original_fetch(*args, **kwargs)
        # Update built-up area to create new payload
        new_data = dict(res.record_data)
        new_data["approved_total_builtup_area_sqm"] = 16500.0
        new_sha = compute_canonical_sha256(new_data)
        return InstitutionSnapshotResult(
            source_code=res.source_code,
            institution_id=res.institution_id,
            aicte_permanent_id=res.aicte_permanent_id,
            record_data=new_data,
            source_system=res.source_system,
            source_reference=res.source_reference,
            payload_sha256=new_sha,
            effective_from=res.effective_from,
            source_updated_at=datetime.now(UTC),
            environment=SourceEnvironment.SIMULATED,
            adapter_version=res.adapter_version,
            status=SourceSyncStatus.SUCCEEDED,
            records_received=1,
        )

    monkeypatch.setattr(connector, "fetch_institution_snapshot", mock_fetch_updated)

    # Sync again with updated data
    _, v2 = service.sync_institution_source(db, inst.institution_id, "SRC_AICTE_PORTAL")
    assert v2 is not None
    assert v2.institution_record_version_id != v1_id
    assert v2.record_version > v1_ver
    assert v2.source_payload_sha256 != original_sha
    assert v2.record_data["approved_total_builtup_area_sqm"] == 16500.0

    # Verify v1 still exists unchanged in the database
    v1_recheck = db.scalar(
        select(InstitutionRecordVersion).where(
            InstitutionRecordVersion.institution_record_version_id == v1_id
        )
    )
    assert v1_recheck is not None
    assert v1_recheck.record_version == v1_ver
    assert v1_recheck.source_payload_sha256 == original_sha
    assert v1_recheck.record_data["approved_total_builtup_area_sqm"] == 14250.0


def test_seed_sources_script_idempotent():
    """The seed_sources CLI script executes cleanly and is idempotent."""
    from scripts.seed_sources import seed_sources

    res1 = seed_sources()
    assert "source_counts" in res1
    assert "snapshot_counts" in res1

    res2 = seed_sources()
    assert res2["source_counts"]["inserted"] == 0
    assert res2["snapshot_counts"]["inserted"] == 0

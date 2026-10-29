"""AIC-Flow evidence adapter — Source Connector Service.

Orchestrates database persistence for verification sources, sync runs,
versioned institutional snapshots, and document verification attempts.
"""

from __future__ import annotations

import logging
import uuid
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.connectors.base import (
    CoordinateLookupResult,
    DocumentVerificationResult,
    MalformedPayloadError,
    SourceConnectorError,
    SourceEnvironment,
    SourceSyncKind,
    SourceSyncStatus,
    SourceTimeoutError,
    SourceUnavailableError,
    UnknownSourceError,
)
from app.connectors.bhuvan_geomap import BhuvanGeoportalConnector
from app.connectors.registry import connector_registry
from app.models.enums import VerificationMethod, VerificationStatus
from app.models.institution import Institution
from app.models.institution_record_version import InstitutionRecordVersion
from app.models.source_sync_run import SourceSyncRun
from app.models.verification_attempt import VerificationAttempt
from app.models.verification_source import VerificationSource

logger = logging.getLogger(__name__)


class SourceConnectorService:
    """Service managing synthetic verification source synchronization and persistence."""

    def __init__(self, registry=None) -> None:
        self.registry = registry or connector_registry

    def seed_or_update_verification_sources(self, db: Session) -> dict[str, int]:
        """Idempotently seed or update the six approved verification sources in the database.

        Returns counts of inserted, updated, and unchanged source records.
        """
        counts = {"inserted": 0, "updated": 0, "unchanged": 0}

        for connector in self.registry.list_connectors():
            existing = db.scalar(
                select(VerificationSource).where(
                    VerificationSource.source_code == connector.source_code
                )
            )

            if not existing:
                source = VerificationSource(
                    source_code=connector.source_code,
                    source_name=connector.source_name,
                    source_type=connector.source_type,
                    supported_document_types=connector.supported_document_types,
                    official_domain=connector.official_domain,
                    integration_mode=connector.integration_mode,
                    is_authorized=True,
                    is_enabled=True,
                )
                db.add(source)
                counts["inserted"] += 1
            else:
                updated = False
                if existing.source_name != connector.source_name:
                    existing.source_name = connector.source_name
                    updated = True
                if existing.source_type != connector.source_type:
                    existing.source_type = connector.source_type
                    updated = True
                if (
                    existing.supported_document_types
                    != connector.supported_document_types
                ):
                    existing.supported_document_types = (
                        connector.supported_document_types
                    )
                    updated = True
                if existing.official_domain != connector.official_domain:
                    existing.official_domain = connector.official_domain
                    updated = True
                if existing.integration_mode != connector.integration_mode:
                    existing.integration_mode = connector.integration_mode
                    updated = True
                if not existing.is_authorized:
                    existing.is_authorized = True
                    updated = True
                if not existing.is_enabled:
                    existing.is_enabled = True
                    updated = True

                if updated:
                    counts["updated"] += 1
                else:
                    counts["unchanged"] += 1

        db.commit()
        return counts

    def get_verification_source(
        self, db: Session, source_code: str
    ) -> VerificationSource | None:
        """Retrieve VerificationSource database model by source_code."""
        return db.scalar(
            select(VerificationSource).where(
                VerificationSource.source_code == source_code
            )
        )

    def list_verification_sources(self, db: Session) -> list[VerificationSource]:
        """List all registered VerificationSource database records."""
        return list(
            db.scalars(
                select(VerificationSource).order_by(VerificationSource.source_code)
            ).all()
        )

    def sync_institution_source(
        self,
        db: Session,
        institution_id: uuid.UUID,
        source_code: str,
        sync_kind: str = SourceSyncKind.ON_DEMAND,
        recorded_by: uuid.UUID | None = None,
        simulate_failure: str | None = None,
    ) -> tuple[SourceSyncRun, InstitutionRecordVersion | None]:
        """Synchronize an institution record from the specified source connector.

        Creates an audit record in source_sync_runs and, if new or changed, creates
        a new versioned snapshot in institution_record_versions.
        """
        inst = db.scalar(
            select(Institution).where(Institution.institution_id == institution_id)
        )
        if not inst:
            raise ValueError(f"Institution not found: {institution_id}")

        source = self.get_verification_source(db, source_code)
        if not source:
            raise UnknownSourceError(
                f"Verification source not registered in database: {source_code}"
            )

        connector = self.registry.get(source_code)
        correlation_id = str(uuid.uuid4())
        started_at = datetime.now(UTC)

        sync_run = SourceSyncRun(
            verification_source_id=source.verification_source_id,
            environment=SourceEnvironment.SIMULATED,
            sync_kind=sync_kind,
            adapter_version=connector.adapter_version,
            status=SourceSyncStatus.RUNNING,
            request_correlation_id=correlation_id,
            started_at=started_at,
            records_received=0,
            sanitized_summary={},
        )
        db.add(sync_run)
        db.flush()

        try:
            snapshot_res = connector.fetch_institution_snapshot(
                aicte_permanent_id=inst.aicte_permanent_institution_id,
                institution_id=institution_id,
                correlation_id=correlation_id,
                simulate_failure=simulate_failure,
            )
        except (SourceTimeoutError, SourceUnavailableError, MalformedPayloadError) as e:
            sync_run.status = SourceSyncStatus.FAILED
            sync_run.error_code = type(e).__name__
            sync_run.error_summary = str(e)
            sync_run.completed_at = datetime.now(UTC)
            db.commit()
            return sync_run, None

        if snapshot_res.status == SourceSyncStatus.FAILED:
            sync_run.status = SourceSyncStatus.FAILED
            sync_run.error_code = snapshot_res.error_code
            sync_run.error_summary = snapshot_res.error_summary
            sync_run.completed_at = datetime.now(UTC)
            db.commit()
            return sync_run, None

        # Successful sync run execution
        sync_run.status = SourceSyncStatus.SUCCEEDED
        sync_run.records_received = snapshot_res.records_received
        sync_run.response_sha256 = snapshot_res.payload_sha256
        sync_run.source_updated_at = snapshot_res.source_updated_at
        sync_run.sanitized_summary = {
            "source_system": snapshot_res.source_system,
            "source_reference": snapshot_res.source_reference,
            "aicte_permanent_id": snapshot_res.aicte_permanent_id,
            "payload_sha256": snapshot_res.payload_sha256,
            "provenance": "SIMULATED",
        }
        sync_run.completed_at = datetime.now(UTC)

        # Check latest record version for this institution and source_system
        latest_for_source = db.scalar(
            select(InstitutionRecordVersion)
            .where(
                InstitutionRecordVersion.institution_id == institution_id,
                InstitutionRecordVersion.source_system == snapshot_res.source_system,
            )
            .order_by(InstitutionRecordVersion.record_version.desc())
        )

        if (
            latest_for_source
            and latest_for_source.source_payload_sha256 == snapshot_res.payload_sha256
        ):
            # Payload unchanged; preserve history without creating redundant row
            db.commit()
            return sync_run, latest_for_source

        # Changed or initial snapshot: calculate next record_version for institution
        max_record_version = (
            db.scalar(
                select(func.max(InstitutionRecordVersion.record_version)).where(
                    InstitutionRecordVersion.institution_id == institution_id
                )
            )
            or 0
        )
        next_version = max_record_version + 1

        new_version = InstitutionRecordVersion(
            institution_id=institution_id,
            record_version=next_version,
            record_data=snapshot_res.record_data,
            source_system=snapshot_res.source_system,
            source_reference=snapshot_res.source_reference,
            effective_from=snapshot_res.effective_from,
            effective_to=snapshot_res.effective_to,
            recorded_at=datetime.now(UTC),
            recorded_by=recorded_by,
            source_sync_run_id=sync_run.source_sync_run_id,
            source_updated_at=snapshot_res.source_updated_at,
            source_payload_sha256=snapshot_res.payload_sha256,
        )
        db.add(new_version)
        db.commit()
        return sync_run, new_version

    def verify_document_reference(
        self,
        db: Session,
        document_version_id: uuid.UUID,
        source_code: str,
        method: VerificationMethod = VerificationMethod.OFFICIAL_PORTAL,
        reference_number: str | None = None,
        document_type_code: str | None = None,
        expected_fields: dict[str, Any] | None = None,
        requested_by: uuid.UUID | None = None,
        simulate_failure: str | None = None,
    ) -> VerificationAttempt:
        """Execute and record a document reference verification attempt."""
        source = self.get_verification_source(db, source_code)
        source_id = source.verification_source_id if source else None
        connector = self.registry.get(source_code)
        correlation_id = str(uuid.uuid4())

        attempt = VerificationAttempt(
            document_version_id=document_version_id,
            verification_source_id=source_id,
            method=method,
            status=VerificationStatus.PENDING,
            requested_by=requested_by,
            source_reference_number=reference_number,
            request_correlation_id=correlation_id,
            response_summary={},
            compared_fields=expected_fields or {},
            requested_at=datetime.now(UTC),
        )
        db.add(attempt)
        db.flush()

        try:
            ver_result: DocumentVerificationResult = (
                connector.verify_document_reference(
                    document_reference=reference_number or "",
                    document_type_code=document_type_code,
                    expected_fields=expected_fields,
                    correlation_id=correlation_id,
                    simulate_failure=simulate_failure,
                )
            )
            attempt.status = ver_result.status
            attempt.response_summary = ver_result.response_summary
            attempt.compared_fields = ver_result.compared_fields
            attempt.source_response_reference = ver_result.source_response_reference
            attempt.completed_at = datetime.now(UTC)
        except SourceTimeoutError as e:
            attempt.status = VerificationStatus.SOURCE_UNAVAILABLE
            attempt.response_summary = {
                "error": "TIMEOUT",
                "detail": str(e),
                "provenance": "SIMULATED",
            }
            attempt.completed_at = datetime.now(UTC)
        except SourceUnavailableError as e:
            attempt.status = VerificationStatus.SOURCE_UNAVAILABLE
            attempt.response_summary = {
                "error": "UNAVAILABLE",
                "detail": str(e),
                "provenance": "SIMULATED",
            }
            attempt.completed_at = datetime.now(UTC)
        except (SourceConnectorError, RuntimeError, ValueError, KeyError) as e:
            attempt.status = VerificationStatus.FAILED
            attempt.response_summary = {
                "error": type(e).__name__,
                "detail": str(e),
                "provenance": "SIMULATED",
            }
            attempt.completed_at = datetime.now(UTC)

        db.commit()
        return attempt

    def lookup_coordinates(
        self,
        latitude: float,
        longitude: float,
        correlation_id: str | None = None,
        simulate_failure: str | None = None,
    ) -> CoordinateLookupResult:
        """Resolve geographical coordinates through the Bhuvan Geoportal connector."""
        bhuvan_connector = self.registry.get("SRC_BHUVAN_GEOMAP")
        if not isinstance(bhuvan_connector, BhuvanGeoportalConnector):
            raise TypeError(
                "Connector for SRC_BHUVAN_GEOMAP is not a BhuvanGeoportalConnector instance"
            )
        return bhuvan_connector.lookup_coordinates(
            latitude=latitude,
            longitude=longitude,
            correlation_id=correlation_id,
            simulate_failure=simulate_failure,
        )

    def get_latest_institution_snapshots(
        self,
        db: Session,
        institution_id: uuid.UUID,
    ) -> dict[str, InstitutionRecordVersion]:
        """Return a mapping of source_system -> latest InstitutionRecordVersion for an institution."""
        records = db.scalars(
            select(InstitutionRecordVersion)
            .where(InstitutionRecordVersion.institution_id == institution_id)
            .order_by(InstitutionRecordVersion.record_version.asc())
        ).all()

        latest: dict[str, InstitutionRecordVersion] = {}
        for rec in records:
            latest[rec.source_system] = rec
        return latest

    def get_institution_snapshot_history(
        self,
        db: Session,
        institution_id: uuid.UUID,
        source_system: str | None = None,
    ) -> list[InstitutionRecordVersion]:
        """Return chronological history of institution record versions."""
        query = select(InstitutionRecordVersion).where(
            InstitutionRecordVersion.institution_id == institution_id
        )
        if source_system:
            query = query.where(InstitutionRecordVersion.source_system == source_system)
        query = query.order_by(InstitutionRecordVersion.record_version.asc())
        return list(db.scalars(query).all())


# Global default service instance
source_connector_service = SourceConnectorService()

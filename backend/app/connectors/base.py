"""AIC-Verify — Base Source Connector Interface and Data Contracts.

Defines the abstract base connector, result dataclasses, canonical SHA-256 calculation,
and simulation failure types for synthetic provider adapters.
"""

from __future__ import annotations

import hashlib
import json
import uuid
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import StrEnum
from typing import Any, ClassVar

from app.models.enums import SourceType, VerificationMethod, VerificationStatus


class SourceEnvironment(StrEnum):
    """Execution environment for verification sources (matches chk_source_sync_environment)."""

    SIMULATED = "SIMULATED"
    SANDBOX = "SANDBOX"
    PRODUCTION = "PRODUCTION"
    PUBLIC_DATA = "PUBLIC_DATA"


class SourceSyncKind(StrEnum):
    """Synchronization kind for source sync runs (matches chk_source_sync_kind)."""

    FULL = "FULL"
    INCREMENTAL = "INCREMENTAL"
    ON_DEMAND = "ON_DEMAND"
    HEALTH_CHECK = "HEALTH_CHECK"


class SourceSyncStatus(StrEnum):
    """Synchronization execution status (matches chk_source_sync_status)."""

    QUEUED = "QUEUED"
    RUNNING = "RUNNING"
    SUCCEEDED = "SUCCEEDED"
    PARTIAL = "PARTIAL"
    FAILED = "FAILED"
    CANCELLED = "CANCELLED"


# --- Exceptions ---


class SourceConnectorError(Exception):
    """Base exception for source connector operations."""


class SourceUnavailableError(SourceConnectorError):
    """Raised when an external or synthetic verification source is unavailable."""


class SourceTimeoutError(SourceConnectorError):
    """Raised when a verification request times out."""


class MalformedPayloadError(SourceConnectorError):
    """Raised when a source response payload is structurally malformed."""


class UnknownSourceError(SourceConnectorError):
    """Raised when an unregistered source code is requested."""


# --- Canonical Serialization & Hashing ---


def compute_canonical_sha256(data: dict[str, Any] | str | bytes) -> str:
    """Calculate deterministic SHA-256 hex digest over canonical JSON or raw bytes.

    For dictionary payloads, guarantees reproducibility by sorting keys and removing
    whitespace separators.
    """
    if isinstance(data, bytes):
        raw = data
    elif isinstance(data, str):
        raw = data.encode("utf-8")
    else:
        raw = json.dumps(
            data, sort_keys=True, separators=(",", ":"), ensure_ascii=False
        ).encode("utf-8")
    return hashlib.sha256(raw).hexdigest()


# --- Result Dataclasses ---


@dataclass(frozen=True)
class InstitutionSnapshotResult:
    """Result of retrieving a versioned institutional master record snapshot."""

    source_code: str
    aicte_permanent_id: str
    record_data: dict[str, Any]
    source_system: str
    payload_sha256: str
    effective_from: datetime
    institution_id: uuid.UUID | None = None
    effective_to: datetime | None = None
    source_updated_at: datetime | None = None
    source_reference: str | None = None
    environment: SourceEnvironment = SourceEnvironment.SIMULATED
    adapter_version: str = "1.0.0-synthetic"
    status: SourceSyncStatus = SourceSyncStatus.SUCCEEDED
    records_received: int = 1
    error_code: str | None = None
    error_summary: str | None = None
    retrieved_at: datetime = field(default_factory=lambda: datetime.now(UTC))


@dataclass(frozen=True)
class DocumentVerificationResult:
    """Result of querying a document or field reference against an issuing authority."""

    source_code: str
    method: VerificationMethod
    status: VerificationStatus
    source_reference_number: str | None = None
    response_summary: dict[str, Any] = field(default_factory=dict)
    compared_fields: dict[str, Any] = field(default_factory=dict)
    source_response_reference: str | None = None
    environment: SourceEnvironment = SourceEnvironment.SIMULATED
    adapter_version: str = "1.0.0-synthetic"
    response_sha256: str = ""
    error_code: str | None = None
    error_summary: str | None = None
    completed_at: datetime = field(default_factory=lambda: datetime.now(UTC))


@dataclass(frozen=True)
class CoordinateLookupResult:
    """Result of querying geographical coordinates against a geospatial portal."""

    source_code: str
    latitude: float
    longitude: float
    status: VerificationStatus
    resolved_state: str | None = None
    resolved_district: str | None = None
    resolved_pincode: str | None = None
    coarse_bounds_valid: bool = True
    distance_meters: float | None = None
    details: dict[str, Any] = field(default_factory=dict)
    environment: SourceEnvironment = SourceEnvironment.SIMULATED
    adapter_version: str = "1.0.0-synthetic"
    response_sha256: str = ""
    error_code: str | None = None
    error_summary: str | None = None
    completed_at: datetime = field(default_factory=lambda: datetime.now(UTC))


# --- Abstract Base Connector ---


class BaseSourceConnector(ABC):
    """Abstract base connector for issuing authorities, registries and data portals."""

    source_code: str
    source_name: str
    source_type: SourceType
    integration_mode: str = "MOCK"
    adapter_version: str = "1.0.0-synthetic"
    official_domain: str | None = None
    supported_document_types: ClassVar[list[int] | None] = None

    @abstractmethod
    def fetch_institution_snapshot(
        self,
        aicte_permanent_id: str,
        institution_id: uuid.UUID | None = None,
        correlation_id: str | None = None,
        simulate_failure: str | None = None,
    ) -> InstitutionSnapshotResult:
        """Fetch versioned institutional master record snapshot from the provider."""
        ...

    @abstractmethod
    def verify_document_reference(
        self,
        document_reference: str,
        document_type_code: str | None = None,
        expected_fields: dict[str, Any] | None = None,
        correlation_id: str | None = None,
        simulate_failure: str | None = None,
    ) -> DocumentVerificationResult:
        """Verify an issued certificate or document reference with the provider."""
        ...

    def health_check(self) -> bool:
        """Check availability of the provider."""
        return True

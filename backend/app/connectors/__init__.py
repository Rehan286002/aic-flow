"""AIC-Verify — Source Connectors and Verification Adapters."""

from app.connectors.aicte_portal import AICTEPortalConnector
from app.connectors.base import (
    BaseSourceConnector,
    CoordinateLookupResult,
    DocumentVerificationResult,
    InstitutionSnapshotResult,
    MalformedPayloadError,
    SourceConnectorError,
    SourceEnvironment,
    SourceSyncKind,
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

__all__ = [
    "AICTEPortalConnector",
    "BaseSourceConnector",
    "BhuvanGeoportalConnector",
    "CoordinateLookupResult",
    "DocumentVerificationResult",
    "FireServicesConnector",
    "ICAIUDINConnector",
    "InstitutionSnapshotResult",
    "LandRevenueConnector",
    "MalformedPayloadError",
    "MunicipalBuildingConnector",
    "SourceConnectorError",
    "SourceConnectorRegistry",
    "SourceEnvironment",
    "SourceSyncKind",
    "SourceSyncStatus",
    "SourceTimeoutError",
    "SourceUnavailableError",
    "UnknownSourceError",
    "compute_canonical_sha256",
    "connector_registry",
]

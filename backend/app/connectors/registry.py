"""AIC-Verify — Source Connector Registry.

Maintains singleton registry of all configured issuing authorities, government portals
and synthetic verification connectors.
"""

from __future__ import annotations

from app.connectors.aicte_portal import AICTEPortalConnector
from app.connectors.base import BaseSourceConnector, UnknownSourceError
from app.connectors.bhuvan_geomap import BhuvanGeoportalConnector
from app.connectors.fire_services import FireServicesConnector
from app.connectors.icai_udin import ICAIUDINConnector
from app.connectors.land_revenue import LandRevenueConnector
from app.connectors.municipal_building import MunicipalBuildingConnector


class SourceConnectorRegistry:
    """Registry for managing and resolving source connector instances by source_code."""

    def __init__(self) -> None:
        self._connectors: dict[str, BaseSourceConnector] = {}
        self._register_default_connectors()

    def _register_default_connectors(self) -> None:
        """Register the six approved synthetic source connectors."""
        defaults = [
            AICTEPortalConnector(),
            LandRevenueConnector(),
            MunicipalBuildingConnector(),
            FireServicesConnector(),
            ICAIUDINConnector(),
            BhuvanGeoportalConnector(),
        ]
        for connector in defaults:
            self.register(connector)

    def register(self, connector: BaseSourceConnector) -> None:
        """Register a source connector instance."""
        self._connectors[connector.source_code] = connector

    def get(self, source_code: str) -> BaseSourceConnector:
        """Get connector instance by source_code. Raises UnknownSourceError if unregistered."""
        if source_code not in self._connectors:
            raise UnknownSourceError(
                f"No connector registered for source code: {source_code}"
            )
        return self._connectors[source_code]

    def list_connectors(self) -> list[BaseSourceConnector]:
        """Return all registered connector instances."""
        return list(self._connectors.values())

    def list_source_codes(self) -> list[str]:
        """Return list of all registered source codes."""
        return list(self._connectors.keys())


# Global singleton registry instance
connector_registry = SourceConnectorRegistry()

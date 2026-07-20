# src/infrastructure/connectors/connector_resolver.py
"""Implementation of the IConnectorResolver interface using the ConnectorRegistry."""

from typing import Any

from src.domain.interfaces.connector_resolver import IConnectorResolver
from src.domain.interfaces.connectors import ConnectorType, IConnector
from src.infrastructure.connectors.connector_registry import ConnectorRegistry


class ConnectorResolver(IConnectorResolver):
    """Resolves and instantiates IConnector implementations using the global registry."""

    def resolve(self, connector_type: ConnectorType, **kwargs: Any) -> IConnector:
        """Instantiate the concrete connector registered for the specified type."""
        factory = ConnectorRegistry.get_factory(connector_type)
        return factory(**kwargs)

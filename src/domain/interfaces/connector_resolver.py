# src/domain/interfaces/connector_resolver.py
"""Domain interface for resolving infrastructure connectors."""

from abc import ABC, abstractmethod
from typing import Any

from src.domain.interfaces.connectors import ConnectorType, IConnector


class IConnectorResolver(ABC):
    """Interface for resolving and instantiating IConnector implementations."""

    @abstractmethod
    def resolve(self, connector_type: ConnectorType, **kwargs: Any) -> IConnector:
        """Resolve and instantiate a connector of the given type with the provided arguments."""
        pass

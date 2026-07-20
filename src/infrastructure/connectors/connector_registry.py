# src/infrastructure/connectors/connector_registry.py
"""Registry to associate ConnectorType values to concrete connector implementations."""

from typing import Any, Callable, Dict

import structlog

from src.domain.interfaces.connectors import ConnectorType, IConnector

logger = structlog.get_logger(__name__)


class ConnectorRegistry:
    """Pluggable registry mapping ConnectorType to concrete connector factory methods."""

    _registry: Dict[ConnectorType, Callable[..., IConnector]] = {}

    @classmethod
    def register(
        cls,
        connector_type: ConnectorType,
        factory: Callable[..., IConnector],
    ) -> None:
        """Register a new factory function for a given ConnectorType."""
        logger.info("Registering connector implementation", type=connector_type)
        cls._registry[connector_type] = factory

    @classmethod
    def get_factory(cls, connector_type: ConnectorType) -> Callable[..., IConnector]:
        """Retrieve the registered factory function for the given ConnectorType."""
        if connector_type not in cls._registry:
            raise ValueError(
                f"No connector implementation registered for type: {connector_type}"
            )
        return cls._registry[connector_type]


# Self-register default connector types on import to simplify bootstrap
from src.infrastructure.connectors.hostinger.hostinger_connector import (
    HostingerConnector,
)
from src.infrastructure.connectors.linux.ssh_connector import LinuxSSHConnector

ConnectorRegistry.register(ConnectorType.SSH, lambda **kw: LinuxSSHConnector(**kw))
ConnectorRegistry.register(
    ConnectorType.HOSTINGER, lambda **kw: HostingerConnector(**kw)
)

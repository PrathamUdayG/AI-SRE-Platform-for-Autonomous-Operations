# src/application/services/telemetry_orchestrator.py
"""Service responsible for orchestrating one-off telemetry collection sessions."""

from datetime import datetime, timezone
from typing import List

import structlog

from src.domain.dtos.telemetry import CollectionContext, RawMetric
from src.domain.entities.telemetry import TelemetryMetric
from src.domain.exceptions import ConnectionFailedError, NotFoundError
from src.domain.interfaces.connector_resolver import IConnectorResolver
from src.domain.interfaces.connectors import ConnectorType
from src.domain.repositories.inventory_repository import InventoryRepository
from src.domain.repositories.server_repository import ServerRepository
from src.domain.repositories.telemetry_repository import TelemetryRepository
from src.infrastructure.persistence.mappers import MetricMapper
from src.infrastructure.telemetry.collector_registry import CollectorRegistry

logger = structlog.get_logger(__name__)


class TelemetryOrchestrator:
    """Orchestrator coordinating metric collection tasks across registered collectors."""

    def __init__(
        self,
        server_repository: ServerRepository,
        inventory_repository: InventoryRepository,
        connector_resolver: IConnectorResolver,
        telemetry_repository: TelemetryRepository,
    ):
        self.server_repository = server_repository
        self.inventory_repository = inventory_repository
        self.connector_resolver = connector_resolver
        self.telemetry_repository = telemetry_repository

    async def collect_telemetry(self, server_id: int) -> List[TelemetryMetric]:
        """Orchestrate a single-run collection of all telemetry metrics on the server."""
        logger.info("Starting orchestrated telemetry collection", server_id=server_id)

        # 1. Fetch server registration
        server = await self.server_repository.get_by_id(server_id)
        if not server:
            raise NotFoundError(f"Server with ID {server_id} not found.")

        # 2. Fetch inventory registration
        inventory = await self.inventory_repository.get_by_server_id(server_id)
        if not inventory:
            raise NotFoundError(
                f"Inventory record for server ID {server_id} not found."
            )

        # 3. Resolve connector configuration
        from src.infrastructure.config.settings import settings

        password_val = (
            settings.hostinger.ssh_password.get_secret_value()
            if settings.hostinger.ssh_password
            else None
        )
        connector = self.connector_resolver.resolve(
            ConnectorType.SSH,
            host=server.ip_address,
            username=settings.hostinger.ssh_username,
            password=password_val,
            key_path=settings.hostinger.ssh_key_path,
            port=settings.hostinger.ssh_port,
            timeout=settings.hostinger.ssh_timeout,
            retries=2,
            retry_delay=1.0,
        )

        # 4. Connect to remote target
        try:
            await connector.connect()
        except Exception as e:
            logger.error(
                "Telemetry collection connection failed",
                server_id=server_id,
                error=str(e),
            )
            raise ConnectionFailedError(
                f"Telemetry collection connection failed: {str(e)}"
            )

        # 5. Build context
        context = CollectionContext(
            server=server,
            inventory=inventory,
            connector=connector,
            timestamp=datetime.now(timezone.utc),
            metadata={},
        )

        collected_metrics: List[RawMetric] = []

        # 6. Execute all registered collectors
        try:
            metric_types = CollectorRegistry.get_all_types()
            for m_type in metric_types:
                collector = CollectorRegistry.get_collector(m_type)
                logger.debug("Executing collector", server_id=server_id, type=m_type)
                try:
                    metric = await collector.collect(context)
                    collected_metrics.append(metric)
                except Exception as ex:
                    logger.error(
                        "Individual collector failed",
                        server_id=server_id,
                        type=m_type,
                        error=str(ex),
                    )
        finally:
            await connector.disconnect()

        # 7. Persist metrics
        persisted_metrics: List[TelemetryMetric] = []
        for raw in collected_metrics:
            entity = MetricMapper.to_entity(raw)
            saved = await self.telemetry_repository.save(entity)
            persisted_metrics.append(saved)

        logger.info(
            "Telemetry collection completed",
            server_id=server_id,
            metrics_count=len(persisted_metrics),
        )
        return persisted_metrics

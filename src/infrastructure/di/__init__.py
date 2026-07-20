# src/infrastructure/di/__init__.py
"""Dependency Injection module for application repositories and services."""

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from src.application.services.discovery_service import DiscoveryService
from src.application.services.inventory_service import InventoryService
from src.application.services.metric_service import MetricService
from src.application.services.server_service import ServerService
from src.application.services.telemetry_orchestrator import TelemetryOrchestrator
from src.domain.interfaces.connector_resolver import IConnectorResolver
from src.domain.repositories.discovery_repository import DiscoveryRepository
from src.domain.repositories.inventory_repository import InventoryRepository
from src.domain.repositories.metric_repository import (
    MetricRepository as IMetricRepository,
)
from src.domain.repositories.server_repository import ServerRepository
from src.domain.repositories.telemetry_repository import TelemetryRepository
from src.infrastructure.connectors.connector_resolver import ConnectorResolver
from src.infrastructure.database import get_db
from src.infrastructure.persistence.repositories import MetricRepository
from src.infrastructure.repositories.postgres_discovery_repository import (
    PostgresDiscoveryRepository,
)
from src.infrastructure.repositories.postgres_inventory_repository import (
    PostgresInventoryRepository,
)
from src.infrastructure.repositories.postgres_server_repository import (
    PostgresServerRepository,
)
from src.infrastructure.repositories.postgres_telemetry_repository import (
    PostgresTelemetryRepository,
)


async def get_server_repository(
    db: AsyncSession = Depends(get_db),
) -> ServerRepository:
    """FastAPI dependency to retrieve the ServerRepository implementation."""
    return PostgresServerRepository(db)


async def get_server_service(
    repository: ServerRepository = Depends(get_server_repository),
) -> ServerService:
    """FastAPI dependency to retrieve the ServerService instance."""
    return ServerService(repository)


async def get_metric_repository(
    db: AsyncSession = Depends(get_db),
) -> IMetricRepository:
    """FastAPI dependency to retrieve the MetricRepository implementation."""
    return MetricRepository(db)


async def get_metric_service(
    repository: IMetricRepository = Depends(get_metric_repository),
) -> MetricService:
    """FastAPI dependency to retrieve the MetricService instance."""
    return MetricService(repository)


async def get_discovery_repository(
    db: AsyncSession = Depends(get_db),
) -> DiscoveryRepository:
    """FastAPI dependency to retrieve the DiscoveryRepository implementation."""
    return PostgresDiscoveryRepository(db)


async def get_connector_resolver() -> IConnectorResolver:
    """FastAPI dependency to retrieve the IConnectorResolver implementation."""
    return ConnectorResolver()


async def get_discovery_service(
    server_repo: ServerRepository = Depends(get_server_repository),
    discovery_repo: DiscoveryRepository = Depends(get_discovery_repository),
    connector_resolver: IConnectorResolver = Depends(get_connector_resolver),
) -> DiscoveryService:
    """FastAPI dependency to retrieve the DiscoveryService instance."""
    return DiscoveryService(server_repo, discovery_repo, connector_resolver)


async def get_inventory_repository(
    db: AsyncSession = Depends(get_db),
) -> InventoryRepository:
    """FastAPI dependency to retrieve the InventoryRepository implementation."""
    return PostgresInventoryRepository(db)


async def get_inventory_service(
    inventory_repo: InventoryRepository = Depends(get_inventory_repository),
    discovery_service: DiscoveryService = Depends(get_discovery_service),
) -> InventoryService:
    """FastAPI dependency to retrieve the InventoryService instance."""
    return InventoryService(inventory_repo, discovery_service)


async def get_telemetry_repository(
    db: AsyncSession = Depends(get_db),
) -> TelemetryRepository:
    """FastAPI dependency to retrieve the TelemetryRepository implementation."""
    return PostgresTelemetryRepository(db)


async def get_telemetry_orchestrator(
    server_repo: ServerRepository = Depends(get_server_repository),
    inventory_repo: InventoryRepository = Depends(get_inventory_repository),
    connector_resolver: IConnectorResolver = Depends(get_connector_resolver),
    telemetry_repo: TelemetryRepository = Depends(get_telemetry_repository),
) -> TelemetryOrchestrator:
    """FastAPI dependency to retrieve the TelemetryOrchestrator instance."""
    return TelemetryOrchestrator(
        server_repo, inventory_repo, connector_resolver, telemetry_repo
    )


# ---------- Phase 7 monitoring rules registration ----------
from src.application.services.rule_engine import RuleEngine
from src.domain.repositories.health_repository import HealthRepository
from src.infrastructure.repositories.postgres_health_repository import (
    PostgresHealthRepository,
)


async def get_health_repository(
    db: AsyncSession = Depends(get_db),
) -> HealthRepository:
    """FastAPI dependency to retrieve the HealthRepository implementation."""
    return PostgresHealthRepository(db)


async def get_rule_engine(
    server_repo: ServerRepository = Depends(get_server_repository),
    inventory_repo: InventoryRepository = Depends(get_inventory_repository),
    telemetry_repo: TelemetryRepository = Depends(get_telemetry_repository),
    health_repo: HealthRepository = Depends(get_health_repository),
) -> RuleEngine:
    """FastAPI dependency to retrieve the RuleEngine instance."""
    return RuleEngine(server_repo, inventory_repo, telemetry_repo, health_repo)


# ---------- Phase 8 incidents registration ----------
from src.application.services.incident_service import IncidentService
from src.domain.repositories.incident_repository import IncidentRepository
from src.domain.repositories.timeline_repository import TimelineRepository
from src.infrastructure.repositories.postgres_incident_repository import (
    PostgresIncidentRepository,
)
from src.infrastructure.repositories.postgres_timeline_repository import (
    PostgresTimelineRepository,
)


async def get_incident_repository(
    db: AsyncSession = Depends(get_db),
) -> IncidentRepository:
    """FastAPI dependency to retrieve the IncidentRepository implementation."""
    return PostgresIncidentRepository(db)


async def get_timeline_repository(
    db: AsyncSession = Depends(get_db),
) -> TimelineRepository:
    """FastAPI dependency to retrieve the TimelineRepository implementation."""
    return PostgresTimelineRepository(db)


async def get_incident_service(
    incident_repo: IncidentRepository = Depends(get_incident_repository),
    timeline_repo: TimelineRepository = Depends(get_timeline_repository),
    server_repo: ServerRepository = Depends(get_server_repository),
    health_repo: HealthRepository = Depends(get_health_repository),
) -> IncidentService:
    """FastAPI dependency to retrieve the IncidentService instance."""
    return IncidentService(incident_repo, timeline_repo, server_repo, health_repo)

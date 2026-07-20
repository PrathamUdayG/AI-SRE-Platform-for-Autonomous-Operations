# src/infrastructure/persistence/mappers.py
"""Mappers to convert between DTOs, domain aggregates, and persistence models."""

from src.domain.dtos.discovery_result import DiscoveryResult
from src.domain.dtos.telemetry import RawMetric
from src.domain.entities.discovery import (
    CPUInfo,
    DiscoverySnapshot,
    DiskInfo,
    MemoryInfo,
    NetworkInterfaceInfo,
)
from src.domain.entities.health import Finding, ServerHealth
from src.domain.entities.incident import Incident, TimelineEntry
from src.domain.entities.inventory import Inventory, InventoryMetadata
from src.domain.entities.telemetry import TelemetryMetric
from src.domain.interfaces.connectors import ConnectorType
from src.infrastructure.persistence.models import (
    DiscoverySnapshotModel,
    IncidentModel,
    InventoryModel,
    ServerHealthModel,
    TelemetryMetricModel,
    TimelineEntryModel,
)


class DiscoveryMapper:
    """Maps between DiscoveryResult DTOs and domain entities."""

    @staticmethod
    def to_snapshot(result: DiscoveryResult) -> DiscoverySnapshot:
        """Map DiscoveryResult to a persistable DiscoverySnapshot domain entity."""
        return DiscoverySnapshot(
            id=None,
            server_id=result.server_id,
            hostname=result.hostname,
            operating_system=result.operating_system,
            kernel_version=result.kernel_version,
            architecture=result.architecture,
            uptime=result.uptime,
            timezone=result.timezone,
            cpu=result.cpu,
            memory=result.memory,
            disks=result.disks,
            network_interfaces=result.network_interfaces,
            discovered_at=result.discovered_at,
        )

    @staticmethod
    def to_inventory(result: DiscoveryResult) -> Inventory:
        """Map DiscoveryResult to an Inventory aggregate root."""
        return Inventory(
            id=None,
            server_id=result.server_id,
            hostname=result.hostname,
            operating_system=result.operating_system,
            kernel_version=result.kernel_version,
            architecture=result.architecture,
            uptime=result.uptime,
            timezone=result.timezone,
            cpu=result.cpu,
            memory=result.memory,
            disks=result.disks,
            network_interfaces=result.network_interfaces,
            last_discovered_at=result.discovered_at,
            metadata=InventoryMetadata(),
            version=1,
        )


class InventoryMapper:
    """Maps between Domain Inventory aggregates and database persistence models."""

    @staticmethod
    def to_model(entity: Inventory) -> InventoryModel:
        """Map Inventory domain aggregate root to SQLAlchemy ORM model."""
        return InventoryModel(
            id=entity.id,
            server_id=entity.server_id,
            hostname=entity.hostname,
            operating_system=entity.operating_system,
            kernel_version=entity.kernel_version,
            architecture=entity.architecture,
            uptime=entity.uptime,
            timezone=entity.timezone,
            cpu=entity.cpu.model_dump(),
            memory=entity.memory.model_dump(),
            disks=[d.model_dump() for d in entity.disks],
            network_interfaces=[n.model_dump() for n in entity.network_interfaces],
            last_discovered_at=entity.last_discovered_at,
            environment=entity.metadata.environment,
            owner=entity.metadata.owner,
            project=entity.metadata.project,
            business_unit=entity.metadata.business_unit,
            region=entity.metadata.region,
            datacenter=entity.metadata.datacenter,
            role=entity.metadata.role,
            criticality=entity.metadata.criticality,
            connector_type=entity.metadata.connector_type,
            tags=entity.metadata.tags,
            version=entity.version,
        )

    @staticmethod
    def to_domain(model: InventoryModel) -> Inventory:
        """Map SQLAlchemy ORM model to Inventory domain aggregate root."""
        return Inventory(
            id=model.id,
            server_id=model.server_id,
            hostname=model.hostname,
            operating_system=model.operating_system,
            kernel_version=model.kernel_version,
            architecture=model.architecture,
            uptime=model.uptime,
            timezone=model.timezone,
            cpu=CPUInfo(**model.cpu),
            memory=MemoryInfo(**model.memory),
            disks=[DiskInfo(**d) for d in model.disks],
            network_interfaces=[
                NetworkInterfaceInfo(**n) for n in model.network_interfaces
            ],
            last_discovered_at=model.last_discovered_at,
            metadata=InventoryMetadata(
                environment=model.environment,
                owner=model.owner,
                project=model.project,
                business_unit=model.business_unit,
                region=model.region,
                datacenter=model.datacenter,
                role=model.role,
                criticality=model.criticality,
                connector_type=(
                    ConnectorType(model.connector_type)
                    if model.connector_type
                    else None
                ),
                tags=model.tags,
            ),
            version=model.version,
        )


class MetricMapper:
    """Maps between RawMetric DTOs, domain TelemetryMetric entities, and ORM Models."""

    @staticmethod
    def to_entity(raw: RawMetric) -> TelemetryMetric:
        """Map RawMetric DTO to TelemetryMetric domain entity."""
        return TelemetryMetric(
            id=None,
            server_id=raw.server_id,
            metric_type=raw.metric_type,
            timestamp=raw.timestamp,
            data=raw.data,
        )

    @staticmethod
    def to_model(entity: TelemetryMetric) -> TelemetryMetricModel:
        """Map TelemetryMetric domain entity to TelemetryMetricModel ORM model."""
        return TelemetryMetricModel(
            id=entity.id,
            server_id=entity.server_id,
            metric_type=entity.metric_type,
            timestamp=entity.timestamp,
            data=entity.data,
        )

    @staticmethod
    def to_domain(model: TelemetryMetricModel) -> TelemetryMetric:
        """Map TelemetryMetricModel ORM model to TelemetryMetric domain entity."""
        return TelemetryMetric(
            id=model.id,
            server_id=model.server_id,
            metric_type=model.metric_type,
            timestamp=model.timestamp,
            data=model.data,
        )


class HealthMapper:
    """Maps between ServerHealth domain aggregate and ServerHealthModel ORM model."""

    @staticmethod
    def to_model(entity: ServerHealth) -> ServerHealthModel:
        """Map ServerHealth domain aggregate to ServerHealthModel ORM model."""
        return ServerHealthModel(
            id=entity.id,
            server_id=entity.server_id,
            overall_status=entity.overall_status,
            health_score=entity.health_score,
            findings=[f.model_dump() for f in entity.findings],
            evaluation_timestamp=entity.evaluation_timestamp,
        )

    @staticmethod
    def to_domain(model: ServerHealthModel) -> ServerHealth:
        """Map ServerHealthModel ORM model to ServerHealth domain aggregate."""
        findings = [Finding(**f) for f in model.findings]
        return ServerHealth(
            id=model.id,
            server_id=model.server_id,
            overall_status=model.overall_status,
            health_score=model.health_score,
            findings=findings,
            evaluation_timestamp=model.evaluation_timestamp,
        )


class IncidentMapper:
    """Maps between Incident domain aggregates and IncidentModel ORM models."""

    @staticmethod
    def to_model(entity: Incident) -> IncidentModel:
        """Map Incident domain aggregate to IncidentModel ORM model."""
        return IncidentModel(
            id=entity.id,
            title=entity.title,
            description=entity.description,
            severity=entity.severity,
            status=entity.status,
            source=entity.source,
            server_id=entity.server_id,
            findings=[f.model_dump() for f in entity.findings],
            created_at=entity.created_at,
            acknowledged_at=entity.acknowledged_at,
            resolved_at=entity.resolved_at,
            closed_at=entity.closed_at,
            assigned_to=entity.assigned_to,
            resolution_notes=entity.resolution_notes,
        )

    @staticmethod
    def to_domain(model: IncidentModel) -> Incident:
        """Map IncidentModel ORM model to Incident domain aggregate."""
        findings = [Finding(**f) for f in model.findings]
        return Incident(
            id=model.id,
            title=model.title,
            description=model.description,
            severity=model.severity,
            status=model.status,
            source=model.source,
            server_id=model.server_id,
            findings=findings,
            created_at=model.created_at,
            acknowledged_at=model.acknowledged_at,
            resolved_at=model.resolved_at,
            closed_at=model.closed_at,
            assigned_to=model.assigned_to,
            resolution_notes=model.resolution_notes,
        )


class TimelineMapper:
    """Maps between TimelineEntry domain aggregates and TimelineEntryModel ORM models."""

    @staticmethod
    def to_model(entity: TimelineEntry) -> TimelineEntryModel:
        """Map TimelineEntry domain aggregate to TimelineEntryModel ORM model."""
        return TimelineEntryModel(
            id=entity.id,
            incident_id=entity.incident_id,
            event_type=entity.event_type,
            message=entity.message,
            timestamp=entity.timestamp,
            actor=entity.actor,
        )

    @staticmethod
    def to_domain(model: TimelineEntryModel) -> TimelineEntry:
        """Map TimelineEntryModel ORM model to TimelineEntry domain aggregate."""
        return TimelineEntry(
            id=model.id,
            incident_id=model.incident_id,
            event_type=model.event_type,
            message=model.message,
            timestamp=model.timestamp,
            actor=model.actor,
        )

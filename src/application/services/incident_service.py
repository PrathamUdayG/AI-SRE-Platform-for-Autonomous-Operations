# src/application/services/incident_service.py
"""Service implementing the business operations for operations incidents."""

from datetime import datetime, timezone
from typing import List, Optional

import structlog

from src.domain.entities.incident import Incident, TimelineEntry
from src.domain.exceptions import NotFoundError
from src.domain.factories.incident_factory import IncidentFactory
from src.domain.repositories.health_repository import HealthRepository
from src.domain.repositories.incident_repository import IncidentRepository
from src.domain.repositories.server_repository import ServerRepository
from src.domain.repositories.timeline_repository import TimelineRepository

logger = structlog.get_logger(__name__)


class IncidentService:
    """Orchestrates incident lifecycles, state machine validations, and timeline actions."""

    def __init__(
        self,
        incident_repository: IncidentRepository,
        timeline_repository: TimelineRepository,
        server_repository: ServerRepository,
        health_repository: HealthRepository,
    ):
        self.incident_repository = incident_repository
        self.timeline_repository = timeline_repository
        self.server_repository = server_repository
        self.health_repository = health_repository

    async def create_incident(
        self,
        title: str,
        description: str,
        severity: str,
        server_id: int,
        source: str = "MANUAL",
        findings: Optional[List] = None,
    ) -> Incident:
        """Create a manual operational incident and log the creation event."""
        # Validate server exists
        server = await self.server_repository.get_by_id(server_id)
        if not server:
            raise NotFoundError(f"Server with ID {server_id} not found.")

        incident = Incident(
            title=title,
            description=description,
            severity=severity,
            status="OPEN",
            source=source,
            server_id=server_id,
            findings=findings or [],
        )

        saved = await self.incident_repository.save(incident)
        assert saved.id is not None

        # Log timeline event
        await self._record_timeline(
            incident_id=saved.id,
            event_type="CREATED",
            message=f"Incident manually created.",
            actor="system",
        )
        return saved

    async def create_incident_from_health(self, health_id: int) -> Incident:
        """Evaluate a ServerHealth snapshot, generate and save an incident via the factory."""
        health = await self.health_repository.get_by_id(health_id)
        if not health:
            raise NotFoundError(f"Health record with ID {health_id} not found.")

        server = await self.server_repository.get_by_id(health.server_id)
        if not server:
            raise NotFoundError(f"Server with ID {health.server_id} not found.")

        # Instantiate via Factory
        incident = IncidentFactory.create_from_health(health, server.hostname)
        saved = await self.incident_repository.save(incident)
        assert saved.id is not None

        # Record timeline event
        await self._record_timeline(
            incident_id=saved.id,
            event_type="CREATED",
            message=f"Incident automatically created from health evaluation ID {health_id}.",
            actor="system",
        )
        return saved

    async def get_incident(self, incident_id: int) -> Incident:
        """Retrieve an incident record by ID or raise NotFoundError."""
        incident = await self.incident_repository.get_by_id(incident_id)
        if not incident:
            raise NotFoundError(f"Incident with ID {incident_id} not found.")
        return incident

    async def list_incidents(self, limit: int = 100, offset: int = 0) -> List[Incident]:
        """Fetch chronological list of incidents."""
        return await self.incident_repository.get_all(limit=limit, offset=offset)

    async def assign_incident(
        self, incident_id: int, assignee: str, actor: str = "system"
    ) -> Incident:
        """Assign ownership to an operator and record the assignment."""
        incident = await self.get_incident(incident_id)
        incident.assigned_to = assignee

        saved = await self.incident_repository.save(incident)

        await self._record_timeline(
            incident_id=incident_id,
            event_type="ASSIGNED",
            message=f"Incident assigned to owner '{assignee}'.",
            actor=actor,
        )
        return saved

    async def update_status(
        self, incident_id: int, new_status: str, actor: str = "system"
    ) -> Incident:
        """Transition incident status through state machine checks."""
        incident = await self.get_incident(incident_id)
        old_status = incident.status

        # Transition status
        incident.transition_to(new_status)
        saved = await self.incident_repository.save(incident)

        await self._record_timeline(
            incident_id=incident_id,
            event_type="STATUS_CHANGED",
            message=f"Incident status transitioned from {old_status} to {new_status}.",
            actor=actor,
        )
        return saved

    async def resolve_incident(
        self,
        incident_id: int,
        notes: str,
        resolved_by: str,
        actor: str = "system",
    ) -> Incident:
        """Transition status to RESOLVED, save resolution notes."""
        incident = await self.get_incident(incident_id)

        # Transition to RESOLVED
        incident.transition_to("RESOLVED")
        incident.resolution_notes = notes

        saved = await self.incident_repository.save(incident)

        await self._record_timeline(
            incident_id=incident_id,
            event_type="RESOLVED",
            message=f"Incident resolved by {resolved_by}. Notes: {notes}",
            actor=actor,
        )
        return saved

    async def close_incident(self, incident_id: int, actor: str = "system") -> Incident:
        """Transition status to CLOSED."""
        incident = await self.get_incident(incident_id)

        # Transition to CLOSED
        incident.transition_to("CLOSED")

        saved = await self.incident_repository.save(incident)

        await self._record_timeline(
            incident_id=incident_id,
            event_type="CLOSED",
            message=f"Incident closed.",
            actor=actor,
        )
        return saved

    async def get_timeline(self, incident_id: int) -> List[TimelineEntry]:
        """Fetch history timeline events for a given incident."""
        # Check incident exists
        await self.get_incident(incident_id)
        return await self.timeline_repository.get_by_incident_id(incident_id)

    async def _record_timeline(
        self, incident_id: int, event_type: str, message: str, actor: str
    ) -> TimelineEntry:
        """Private helper to save timeline entries."""
        entry = TimelineEntry(
            incident_id=incident_id,
            event_type=event_type,
            message=message,
            timestamp=datetime.now(timezone.utc),
            actor=actor,
        )
        return await self.timeline_repository.save(entry)

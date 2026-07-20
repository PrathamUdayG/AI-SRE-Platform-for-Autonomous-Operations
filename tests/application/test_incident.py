# tests/application/test_incident.py
"""Unit tests for incident state machine, factories, mappers, repositories, and services."""

from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock

import pytest

from src.application.services.incident_service import IncidentService
from src.domain.entities.health import Finding, ServerHealth
from src.domain.entities.incident import Incident, TimelineEntry
from src.domain.entities.server import Server
from src.domain.exceptions import NotFoundError
from src.domain.factories.incident_factory import IncidentFactory
from src.infrastructure.persistence.mappers import IncidentMapper, TimelineMapper
from src.infrastructure.persistence.models import IncidentModel, TimelineEntryModel
from src.infrastructure.repositories.postgres_incident_repository import (
    PostgresIncidentRepository,
)
from src.infrastructure.repositories.postgres_timeline_repository import (
    PostgresTimelineRepository,
)


@pytest.fixture
def sample_health():
    """Fixture returning ServerHealth with warning finding."""
    finding = Finding(
        category="CPU",
        severity="WARNING",
        metric="cpu.usage",
        threshold=80.0,
        actual_value=85.0,
        message="high CPU usage",
        recommendation="check processes",
    )
    return ServerHealth(
        id=55,
        server_id=1,
        overall_status="DEGRADED",
        health_score=80.0,
        findings=[finding],
        evaluation_timestamp=datetime.now(timezone.utc),
    )


# ---------- State Machine Tests ----------
def test_incident_state_machine_valid():
    """Verify linear state machine transitions occur correctly."""
    incident = Incident(
        title="Test Incident",
        description="Trouble",
        severity="WARNING",
        server_id=1,
    )
    assert incident.status == "OPEN"

    incident.transition_to("ACKNOWLEDGED")
    assert incident.status == "ACKNOWLEDGED"
    assert incident.acknowledged_at is not None

    incident.transition_to("IN_PROGRESS")
    assert incident.status == "IN_PROGRESS"

    incident.transition_to("RESOLVED")
    assert incident.status == "RESOLVED"
    assert incident.resolved_at is not None

    incident.transition_to("CLOSED")
    assert incident.status == "CLOSED"
    assert incident.closed_at is not None


def test_incident_state_machine_invalid():
    """Verify invalid state transitions are rejected."""
    incident = Incident(
        title="Test Incident",
        description="Trouble",
        severity="WARNING",
        server_id=1,
    )
    # Skipping ACKNOWLEDGED directly to RESOLVED must fail
    with pytest.raises(ValueError):
        incident.transition_to("RESOLVED")

    # Transitioning from CLOSED must fail
    incident.status = "CLOSED"
    with pytest.raises(ValueError):
        incident.transition_to("OPEN")


# ---------- Factory Tests ----------
def test_incident_factory_from_health(sample_health):
    """Verify IncidentFactory builds valid Incident aggregates from ServerHealth."""
    incident = IncidentFactory.create_from_health(sample_health, "db-host")
    assert incident.title == "Health degradation detected on host db-host"
    assert incident.severity == "WARNING"
    assert incident.status == "OPEN"
    assert incident.server_id == 1
    assert len(incident.findings) == 1
    assert incident.findings[0].category == "CPU"


def test_incident_factory_healthy_rejection():
    """Verify IncidentFactory rejects creating incidents from healthy ServerHealth snapshots."""
    healthy = ServerHealth(
        server_id=2,
        overall_status="HEALTHY",
        health_score=100.0,
        findings=[],
        evaluation_timestamp=datetime.now(timezone.utc),
    )
    with pytest.raises(ValueError):
        IncidentFactory.create_from_health(healthy, "web-host")


# ---------- Mapper Tests ----------
def test_incident_mapper(sample_health):
    """Verify IncidentMapper converts correctly bidirectionally."""
    incident = Incident(
        id=7,
        title="Mapper Test",
        description="Mapping issues",
        severity="CRITICAL",
        status="OPEN",
        source="MONITORING",
        server_id=4,
        findings=sample_health.findings,
        created_at=datetime.now(timezone.utc),
    )

    model = IncidentMapper.to_model(incident)
    assert isinstance(model, IncidentModel)
    assert model.id == 7
    assert len(model.findings) == 1
    assert model.findings[0]["category"] == "CPU"

    domain = IncidentMapper.to_domain(model)
    assert domain.title == "Mapper Test"
    assert len(domain.findings) == 1
    assert domain.findings[0].severity == "WARNING"


def test_timeline_mapper():
    """Verify TimelineMapper converts correctly bidirectionally."""
    entry = TimelineEntry(
        id=12,
        incident_id=7,
        event_type="ASSIGNED",
        message="Assigned to operator",
        timestamp=datetime.now(timezone.utc),
        actor="operator",
    )

    model = TimelineMapper.to_model(entry)
    assert isinstance(model, TimelineEntryModel)
    assert model.id == 12
    assert model.event_type == "ASSIGNED"

    domain = TimelineMapper.to_domain(model)
    assert domain.message == "Assigned to operator"
    assert domain.actor == "operator"


# ---------- Repository Tests ----------
@pytest.mark.asyncio
async def test_postgres_repositories():
    """Verify PostgreSQL repos trigger SQLAlchemy sessions."""
    mock_session = MagicMock()
    mock_session.add = MagicMock()
    mock_session.commit = AsyncMock()
    mock_session.refresh = AsyncMock()

    incident_repo = PostgresIncidentRepository(mock_session)
    timeline_repo = PostgresTimelineRepository(mock_session)

    # Incident save mock
    incident = Incident(
        title="Repo Test", description="Testing", severity="WARNING", server_id=2
    )
    await incident_repo.save(incident)
    mock_session.add.assert_called_once()
    mock_session.commit.assert_called_once()

    # Timeline save mock
    mock_session.add.reset_mock()
    mock_session.commit.reset_mock()

    entry = TimelineEntry(incident_id=1, event_type="CREATED", message="Test Created")
    await timeline_repo.save(entry)
    mock_session.add.assert_called_once()
    mock_session.commit.assert_called_once()


# ---------- Service Tests ----------
@pytest.mark.asyncio
async def test_incident_service(sample_health):
    """Verify IncidentService coordinates creation, updates, and timelines."""
    server = Server(
        id=1,
        hostname="db-host",
        ip_address="10.0.0.5",
        operating_system="Linux",
        cpu_cores=8,
        memory_gb=32.0,
    )

    mock_incident_repo = MagicMock()

    def mock_save_incident(inc):
        if inc.id is None:
            inc.id = 123
        return inc

    mock_incident_repo.save = AsyncMock(side_effect=mock_save_incident)

    mock_timeline_repo = MagicMock()

    def mock_save_timeline(t):
        if t.id is None:
            t.id = 456
        return t

    mock_timeline_repo.save = AsyncMock(side_effect=mock_save_timeline)

    mock_server_repo = MagicMock()
    mock_server_repo.get_by_id = AsyncMock(return_value=server)

    mock_health_repo = MagicMock()
    mock_health_repo.get_by_id = AsyncMock(return_value=sample_health)

    service = IncidentService(
        incident_repository=mock_incident_repo,
        timeline_repository=mock_timeline_repo,
        server_repository=mock_server_repo,
        health_repository=mock_health_repo,
    )

    # 1. Manual Creation
    incident = await service.create_incident(
        title="Disk Space low",
        description="Root partition low",
        severity="CRITICAL",
        server_id=1,
    )
    assert incident.title == "Disk Space low"
    mock_incident_repo.save.assert_called_once()
    mock_timeline_repo.save.assert_called_once()

    # 2. Status Updates & Transitions
    mock_incident_repo.get_by_id = AsyncMock(return_value=incident)
    updated = await service.update_status(1, "ACKNOWLEDGED", actor="operator")
    assert updated.status == "ACKNOWLEDGED"

    updated = await service.update_status(1, "IN_PROGRESS", actor="operator")
    assert updated.status == "IN_PROGRESS"

    # 3. Resolve
    resolved = await service.resolve_incident(
        1, notes="Freed up space", resolved_by="admin", actor="operator"
    )
    assert resolved.status == "RESOLVED"
    assert resolved.resolution_notes == "Freed up space"

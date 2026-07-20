# tests/presentation/test_incident_api.py
"""API endpoint unit tests for operational incident routes."""

from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock

import pytest
from fastapi.testclient import TestClient

from src.domain.entities.incident import Incident, TimelineEntry
from src.infrastructure.di import get_incident_service
from src.main import app

client = TestClient(app)


@pytest.fixture
def sample_incident():
    """Fixture returning a standard Incident domain entity."""
    return Incident(
        id=12,
        title="Mock Incident",
        description="CPU Spike detected",
        severity="CRITICAL",
        status="OPEN",
        source="MONITORING",
        server_id=1,
        created_at=datetime.now(timezone.utc),
    )


def test_create_incident_api(sample_incident):
    """Verify POST /api/v1/incidents raises an incident manually."""
    mock_service = MagicMock()
    mock_service.create_incident = AsyncMock(return_value=sample_incident)

    app.dependency_overrides[get_incident_service] = lambda: mock_service

    try:
        payload = {
            "title": "Manual Incident",
            "description": "Hardware fault",
            "severity": "CRITICAL",
            "server_id": 1,
            "source": "MANUAL",
        }
        response = client.post("/api/v1/incidents", json=payload)
        assert response.status_code == 201
        data = response.json()
        assert data["id"] == 12
        assert data["title"] == "Mock Incident"
        mock_service.create_incident.assert_called_once_with(
            title="Manual Incident",
            description="Hardware fault",
            severity="CRITICAL",
            server_id=1,
            source="MANUAL",
        )
    finally:
        app.dependency_overrides.clear()


def test_create_incident_from_health_api(sample_incident):
    """Verify POST /api/v1/incidents/from-health creates from health ID."""
    mock_service = MagicMock()
    mock_service.create_incident_from_health = AsyncMock(return_value=sample_incident)

    app.dependency_overrides[get_incident_service] = lambda: mock_service

    try:
        payload = {"health_id": 55}
        response = client.post("/api/v1/incidents/from-health", json=payload)
        assert response.status_code == 201
        data = response.json()
        assert data["id"] == 12
        mock_service.create_incident_from_health.assert_called_once_with(55)
    finally:
        app.dependency_overrides.clear()


def test_get_incident_api(sample_incident):
    """Verify GET /api/v1/incidents/{id} retrieves specific record."""
    mock_service = MagicMock()
    mock_service.get_incident = AsyncMock(return_value=sample_incident)

    app.dependency_overrides[get_incident_service] = lambda: mock_service

    try:
        response = client.get("/api/v1/incidents/12")
        assert response.status_code == 200
        assert response.json()["id"] == 12
        mock_service.get_incident.assert_called_once_with(12)
    finally:
        app.dependency_overrides.clear()


def test_update_status_api(sample_incident):
    """Verify PATCH /api/v1/incidents/{id}/status transitions state."""
    mock_service = MagicMock()
    sample_incident.status = "ACKNOWLEDGED"
    mock_service.update_status = AsyncMock(return_value=sample_incident)

    app.dependency_overrides[get_incident_service] = lambda: mock_service

    try:
        payload = {"status": "ACKNOWLEDGED"}
        response = client.patch("/api/v1/incidents/12/status", json=payload)
        assert response.status_code == 200
        assert response.json()["status"] == "ACKNOWLEDGED"
        mock_service.update_status.assert_called_once_with(
            incident_id=12, new_status="ACKNOWLEDGED", actor="operator"
        )
    finally:
        app.dependency_overrides.clear()


def test_assign_incident_api(sample_incident):
    """Verify PATCH /api/v1/incidents/{id}/assign sets owner."""
    mock_service = MagicMock()
    sample_incident.assigned_to = "sre-agent"
    mock_service.assign_incident = AsyncMock(return_value=sample_incident)

    app.dependency_overrides[get_incident_service] = lambda: mock_service

    try:
        payload = {"assignee": "sre-agent"}
        response = client.patch("/api/v1/incidents/12/assign", json=payload)
        assert response.status_code == 200
        assert response.json()["assigned_to"] == "sre-agent"
        mock_service.assign_incident.assert_called_once_with(
            incident_id=12, assignee="sre-agent", actor="operator"
        )
    finally:
        app.dependency_overrides.clear()


def test_resolve_incident_api(sample_incident):
    """Verify PATCH /api/v1/incidents/{id}/resolve transitions to RESOLVED with notes."""
    mock_service = MagicMock()
    sample_incident.status = "RESOLVED"
    sample_incident.resolution_notes = "Rebooted server"
    mock_service.resolve_incident = AsyncMock(return_value=sample_incident)

    app.dependency_overrides[get_incident_service] = lambda: mock_service

    try:
        payload = {"notes": "Rebooted server", "resolved_by": "operator-1"}
        response = client.patch("/api/v1/incidents/12/resolve", json=payload)
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "RESOLVED"
        assert data["resolution_notes"] == "Rebooted server"
        mock_service.resolve_incident.assert_called_once_with(
            incident_id=12,
            notes="Rebooted server",
            resolved_by="operator-1",
            actor="operator",
        )
    finally:
        app.dependency_overrides.clear()


def test_close_incident_api(sample_incident):
    """Verify PATCH /api/v1/incidents/{id}/close transitions state to CLOSED."""
    mock_service = MagicMock()
    sample_incident.status = "CLOSED"
    mock_service.close_incident = AsyncMock(return_value=sample_incident)

    app.dependency_overrides[get_incident_service] = lambda: mock_service

    try:
        response = client.patch("/api/v1/incidents/12/close")
        assert response.status_code == 200
        assert response.json()["status"] == "CLOSED"
        mock_service.close_incident.assert_called_once_with(
            incident_id=12, actor="operator"
        )
    finally:
        app.dependency_overrides.clear()


def test_get_incident_timeline_api():
    """Verify GET /api/v1/incidents/{id}/timeline retrieves history logs."""
    mock_service = MagicMock()
    entry = TimelineEntry(id=1, incident_id=12, event_type="CREATED", message="Created")
    mock_service.get_timeline = AsyncMock(return_value=[entry])

    app.dependency_overrides[get_incident_service] = lambda: mock_service

    try:
        response = client.get("/api/v1/incidents/12/timeline")
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 1
        assert data[0]["event_type"] == "CREATED"
        mock_service.get_timeline.assert_called_once_with(12)
    finally:
        app.dependency_overrides.clear()

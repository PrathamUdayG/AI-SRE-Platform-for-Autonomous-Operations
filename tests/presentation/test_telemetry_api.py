# tests/presentation/test_telemetry_api.py
"""API endpoint unit tests for telemetry collection routes."""

from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock

import pytest
from fastapi.testclient import TestClient

from src.domain.entities.telemetry import TelemetryMetric
from src.infrastructure.di import get_telemetry_orchestrator, get_telemetry_repository
from src.main import app

client = TestClient(app)


@pytest.fixture
def mock_telemetry_metric():
    """Fixture returning a standard TelemetryMetric entity."""
    return TelemetryMetric(
        id=42,
        server_id=1,
        metric_type="cpu",
        timestamp=datetime.now(timezone.utc),
        data={"usage_percent": 15.5},
    )


def test_collect_telemetry_api(mock_telemetry_metric):
    """Verify POST /api/v1/telemetry/collect/{server_id} triggers orchestration and returns collection list."""
    mock_orchestrator = MagicMock()
    mock_orchestrator.collect_telemetry = AsyncMock(
        return_value=[mock_telemetry_metric]
    )

    app.dependency_overrides[get_telemetry_orchestrator] = lambda: mock_orchestrator

    try:
        response = client.post("/api/v1/telemetry/collect/1")
        assert response.status_code == 201
        data = response.json()
        assert len(data) == 1
        assert data[0]["id"] == 42
        assert data[0]["metric_type"] == "cpu"
        assert data[0]["data"]["usage_percent"] == 15.5
        mock_orchestrator.collect_telemetry.assert_called_once_with(1)
    finally:
        app.dependency_overrides.clear()


def test_get_telemetry_history_api(mock_telemetry_metric):
    """Verify GET /api/v1/telemetry/{server_id} returns metrics list matching the type."""
    mock_repo = MagicMock()
    mock_repo.get_history_by_server_id = AsyncMock(return_value=[mock_telemetry_metric])

    app.dependency_overrides[get_telemetry_repository] = lambda: mock_repo

    try:
        response = client.get("/api/v1/telemetry/1?metric_type=cpu&limit=10")
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 1
        assert data[0]["id"] == 42
        mock_repo.get_history_by_server_id.assert_called_once_with(1, "cpu", limit=10)
    finally:
        app.dependency_overrides.clear()


def test_get_latest_telemetry_api(mock_telemetry_metric):
    """Verify GET /api/v1/telemetry/latest/{server_id} fetches the most recent metric entry."""
    mock_repo = MagicMock()
    mock_repo.get_latest_by_server_id = AsyncMock(return_value=mock_telemetry_metric)

    app.dependency_overrides[get_telemetry_repository] = lambda: mock_repo

    try:
        response = client.get("/api/v1/telemetry/latest/1?metric_type=cpu")
        assert response.status_code == 200
        data = response.json()
        assert data["id"] == 42
        assert data["metric_type"] == "cpu"
        mock_repo.get_latest_by_server_id.assert_called_once_with(1, "cpu")
    finally:
        app.dependency_overrides.clear()


def test_get_latest_telemetry_api_not_found():
    """Verify GET /api/v1/telemetry/latest/{server_id} returns 404 if no sample exists."""
    mock_repo = MagicMock()
    mock_repo.get_latest_by_server_id = AsyncMock(return_value=None)

    app.dependency_overrides[get_telemetry_repository] = lambda: mock_repo

    try:
        response = client.get("/api/v1/telemetry/latest/1?metric_type=memory")
        assert response.status_code == 404
        assert "No telemetry found" in response.json()["detail"]
    finally:
        app.dependency_overrides.clear()

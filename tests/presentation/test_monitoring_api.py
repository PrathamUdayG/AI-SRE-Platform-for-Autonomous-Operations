# tests/presentation/test_monitoring_api.py
"""API endpoint unit tests for monitoring and rules evaluation routes."""

from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock

import pytest
from fastapi.testclient import TestClient

from src.domain.entities.health import Finding, ServerHealth
from src.infrastructure.di import get_health_repository, get_rule_engine
from src.main import app

client = TestClient(app)


@pytest.fixture
def sample_health():
    """Fixture returning a standard ServerHealth domain aggregate."""
    finding = Finding(
        category="Memory",
        severity="WARNING",
        metric="memory.usage_percent",
        threshold=85.0,
        actual_value=87.5,
        message="Memory usage is slightly elevated.",
        recommendation="Monitor process memory consumption.",
    )
    return ServerHealth(
        id=99,
        server_id=1,
        overall_status="DEGRADED",
        health_score=90.0,
        findings=[finding],
        evaluation_timestamp=datetime.now(timezone.utc),
    )


def test_evaluate_server_api(sample_health):
    """Verify POST /api/v1/monitoring/evaluate/{server_id} triggers the evaluation pipeline."""
    mock_engine = MagicMock()
    mock_engine.evaluate_server = AsyncMock(return_value=sample_health)

    app.dependency_overrides[get_rule_engine] = lambda: mock_engine

    try:
        response = client.post("/api/v1/monitoring/evaluate/1")
        assert response.status_code == 201
        data = response.json()
        assert data["id"] == 99
        assert data["server_id"] == 1
        assert data["overall_status"] == "DEGRADED"
        assert len(data["findings"]) == 1
        assert data["findings"][0]["category"] == "Memory"
        mock_engine.evaluate_server.assert_called_once_with(1)
    finally:
        app.dependency_overrides.clear()


def test_get_latest_health_api(sample_health):
    """Verify GET /api/v1/monitoring/health/{server_id} retrieves the latest health record."""
    mock_repo = MagicMock()
    mock_repo.get_latest_by_server_id = AsyncMock(return_value=sample_health)

    app.dependency_overrides[get_health_repository] = lambda: mock_repo

    try:
        response = client.get("/api/v1/monitoring/health/1")
        assert response.status_code == 200
        data = response.json()
        assert data["id"] == 99
        assert data["overall_status"] == "DEGRADED"
        mock_repo.get_latest_by_server_id.assert_called_once_with(1)
    finally:
        app.dependency_overrides.clear()


def test_get_latest_health_api_not_found():
    """Verify GET /api/v1/monitoring/health/{server_id} returns 404 if no evaluation exists."""
    mock_repo = MagicMock()
    mock_repo.get_latest_by_server_id = AsyncMock(return_value=None)

    app.dependency_overrides[get_health_repository] = lambda: mock_repo

    try:
        response = client.get("/api/v1/monitoring/health/1")
        assert response.status_code == 404
        assert "No health evaluations found" in response.json()["detail"]
    finally:
        app.dependency_overrides.clear()


def test_get_health_history_api(sample_health):
    """Verify GET /api/v1/monitoring/history/{server_id} retrieves health assessment logs."""
    mock_repo = MagicMock()
    mock_repo.get_history_by_server_id = AsyncMock(return_value=[sample_health])

    app.dependency_overrides[get_health_repository] = lambda: mock_repo

    try:
        response = client.get("/api/v1/monitoring/history/1?limit=10")
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 1
        assert data[0]["id"] == 99
        mock_repo.get_history_by_server_id.assert_called_once_with(1, limit=10)
    finally:
        app.dependency_overrides.clear()

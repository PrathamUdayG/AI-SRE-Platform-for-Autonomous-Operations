# tests/presentation/test_inventory_api.py
"""API endpoint integration/unit tests for inventory routes."""

from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock

import pytest
from fastapi.testclient import TestClient

from src.domain.entities.discovery import (
    CPUInfo,
    DiskInfo,
    MemoryInfo,
    NetworkInterfaceInfo,
)
from src.domain.entities.inventory import Inventory, InventoryMetadata
from src.domain.exceptions import NotFoundError
from src.infrastructure.di import get_inventory_service
from src.main import app

client = TestClient(app)


@pytest.fixture
def mock_inventory():
    """Fixture returning a mock Inventory domain entity."""
    return Inventory(
        id=77,
        server_id=5,
        hostname="api-server",
        operating_system="Debian 11",
        kernel_version="5.10.0-18",
        architecture="amd64",
        uptime="30 days",
        timezone="America/New_York",
        cpu=CPUInfo(
            model="EPYC",
            cores=16,
            sockets=1,
            threads_per_core=2,
            architecture="amd64",
        ),
        memory=MemoryInfo(
            total_mb=32768.0,
            used_mb=16384.0,
            free_mb=16384.0,
            shared_mb=0.0,
            buff_cache_mb=0.0,
            available_mb=16384.0,
        ),
        disks=[
            DiskInfo(
                device="/dev/nvme0n1p1",
                mount_point="/",
                fstype="ext4",
                total_gb=250.0,
                used_gb=100.0,
                free_gb=150.0,
                percentage=40.0,
            )
        ],
        network_interfaces=[
            NetworkInterfaceInfo(
                name="enp3s0",
                ip_addresses=["10.0.1.15"],
                mac_address="aa:bb:cc:dd:ee:ff",
                state="UP",
            )
        ],
        last_discovered_at=datetime.now(timezone.utc),
        metadata=InventoryMetadata(
            environment="staging",
            owner="infra",
            tags={"project": "sre"},
        ),
        version=1,
    )


def test_create_from_discovery_api(mock_inventory):
    """Verify POST /api/v1/inventory/from-discovery/{server_id} promotion trigger."""
    mock_service = MagicMock()
    mock_service.create_from_discovery = AsyncMock(return_value=mock_inventory)

    app.dependency_overrides[get_inventory_service] = lambda: mock_service

    try:
        response = client.post("/api/v1/inventory/from-discovery/5")
        assert response.status_code == 201
        data = response.json()
        assert data["id"] == 77
        assert data["hostname"] == "api-server"
        assert data["metadata"]["environment"] == "staging"
        mock_service.create_from_discovery.assert_called_once_with(5)
    finally:
        app.dependency_overrides.clear()


def test_get_inventory_by_id_api(mock_inventory):
    """Verify GET /api/v1/inventory/{inventory_id} fetches the asset details."""
    mock_service = MagicMock()
    mock_service.get_inventory_by_id = AsyncMock(return_value=mock_inventory)

    app.dependency_overrides[get_inventory_service] = lambda: mock_service

    try:
        response = client.get("/api/v1/inventory/77")
        assert response.status_code == 200
        data = response.json()
        assert data["hostname"] == "api-server"
        assert data["cpu"]["cores"] == 16
        mock_service.get_inventory_by_id.assert_called_once_with(77)
    finally:
        app.dependency_overrides.clear()


def test_get_inventory_by_id_not_found():
    """Verify GET /api/v1/inventory/{id} returns 404 for missing asset."""
    mock_service = MagicMock()
    mock_service.get_inventory_by_id = AsyncMock(
        side_effect=NotFoundError("Inventory asset with ID 99 not found.")
    )

    app.dependency_overrides[get_inventory_service] = lambda: mock_service

    try:
        response = client.get("/api/v1/inventory/99")
        assert response.status_code == 404
        assert "not found" in response.json()["message"]
    finally:
        app.dependency_overrides.clear()


def test_search_inventory_api(mock_inventory):
    """Verify GET /api/v1/inventory/search works correctly."""
    mock_service = MagicMock()
    mock_service.search_inventory = AsyncMock(return_value=[mock_inventory])

    app.dependency_overrides[get_inventory_service] = lambda: mock_service

    try:
        response = client.get("/api/v1/inventory/search?q=api-server")
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 1
        assert data[0]["hostname"] == "api-server"
        mock_service.search_inventory.assert_called_once_with("api-server")
    finally:
        app.dependency_overrides.clear()


def test_update_inventory_metadata_api(mock_inventory):
    """Verify PUT /api/v1/inventory/{id} updates and returns the object."""
    mock_service = MagicMock()
    mock_service.update_metadata = AsyncMock(return_value=mock_inventory)

    app.dependency_overrides[get_inventory_service] = lambda: mock_service

    try:
        payload = {
            "environment": "production",
            "owner": "sre-core",
            "tags": {"critical": "true"},
        }
        response = client.put("/api/v1/inventory/77", json=payload)
        assert response.status_code == 200
        data = response.json()
        assert data["hostname"] == "api-server"
        mock_service.update_metadata.assert_called_once_with(
            inventory_id=77,
            environment="production",
            owner="sre-core",
            project=None,
            business_unit=None,
            region=None,
            datacenter=None,
            role=None,
            criticality=None,
            tags={"critical": "true"},
        )
    finally:
        app.dependency_overrides.clear()


def test_delete_inventory_api():
    """Verify DELETE /api/v1/inventory/{id} returns 204."""
    mock_service = MagicMock()
    mock_service.delete_inventory = AsyncMock(return_value=True)

    app.dependency_overrides[get_inventory_service] = lambda: mock_service

    try:
        response = client.delete("/api/v1/inventory/77")
        assert response.status_code == 204
        mock_service.delete_inventory.assert_called_once_with(77)
    finally:
        app.dependency_overrides.clear()

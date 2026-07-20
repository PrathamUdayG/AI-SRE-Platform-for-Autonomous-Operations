# tests/application/test_inventory.py
"""Unit tests for the Inventory Aggregate, Service, Mappers, and Repository."""

from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.application.services.inventory_service import InventoryService
from src.domain.dtos.discovery_result import DiscoveryResult
from src.domain.entities.discovery import (
    CPUInfo,
    DiskInfo,
    MemoryInfo,
    NetworkInterfaceInfo,
)
from src.domain.entities.inventory import Inventory, InventoryMetadata
from src.domain.exceptions import NotFoundError
from src.domain.interfaces.connectors import ConnectorType
from src.infrastructure.persistence.mappers import DiscoveryMapper, InventoryMapper
from src.infrastructure.persistence.models import InventoryModel
from src.infrastructure.repositories.postgres_inventory_repository import (
    PostgresInventoryRepository,
)


@pytest.fixture
def sample_discovery_result():
    """Fixture returning a standard DiscoveryResult DTO."""
    return DiscoveryResult(
        server_id=1,
        hostname="prod-web-01",
        operating_system="Ubuntu 22.04 LTS",
        kernel_version="5.15.0-generic",
        architecture="x86_64",
        uptime="5 days",
        timezone="UTC",
        cpu=CPUInfo(
            model="Intel Gold",
            cores=8,
            sockets=2,
            threads_per_core=2,
            architecture="x86_64",
        ),
        memory=MemoryInfo(
            total_mb=16384.0,
            used_mb=4096.0,
            free_mb=12288.0,
            shared_mb=0.0,
            buff_cache_mb=0.0,
            available_mb=12288.0,
        ),
        disks=[
            DiskInfo(
                device="/dev/sda1",
                mount_point="/",
                fstype="ext4",
                total_gb=50.0,
                used_gb=10.0,
                free_gb=40.0,
                percentage=20.0,
            )
        ],
        network_interfaces=[
            NetworkInterfaceInfo(
                name="eth0",
                ip_addresses=["192.168.1.50"],
                mac_address="00:11:22:33:44:55",
                state="UP",
            )
        ],
        discovered_at=datetime.now(timezone.utc),
    )


# ---------- Mapper Tests ----------
def test_discovery_mapper_to_inventory(sample_discovery_result):
    """Verify DiscoveryResult to Inventory mapping."""
    inventory = DiscoveryMapper.to_inventory(sample_discovery_result)
    assert isinstance(inventory, Inventory)
    assert inventory.id is None
    assert inventory.server_id == 1
    assert inventory.hostname == "prod-web-01"
    assert inventory.cpu.cores == 8
    assert len(inventory.disks) == 1
    assert len(inventory.network_interfaces) == 1
    assert inventory.version == 1
    assert isinstance(inventory.metadata, InventoryMetadata)


def test_inventory_mapper_orm_roundtrip(sample_discovery_result):
    """Verify bidirectional mapping between Inventory entity and DB Model."""
    inventory = DiscoveryMapper.to_inventory(sample_discovery_result)
    inventory.id = 99
    inventory.metadata.environment = "production"
    inventory.metadata.tags = {"owner": "sre-team"}

    db_model = InventoryMapper.to_model(inventory)
    assert isinstance(db_model, InventoryModel)
    assert db_model.id == 99
    assert db_model.environment == "production"
    assert db_model.tags == {"owner": "sre-team"}

    # Map back
    domain_obj = InventoryMapper.to_domain(db_model)
    assert isinstance(domain_obj, Inventory)
    assert domain_obj.id == 99
    assert domain_obj.metadata.environment == "production"
    assert domain_obj.metadata.tags == {"owner": "sre-team"}
    assert domain_obj.cpu.cores == 8


# ---------- InventoryService Tests ----------
@pytest.mark.asyncio
async def test_inventory_service_create_from_discovery(sample_discovery_result):
    """Verify promotion of discovery result into inventory."""
    mock_discovery_service = MagicMock()
    mock_discovery_service.discover_server = AsyncMock(
        return_value=sample_discovery_result
    )

    mock_inventory_repo = MagicMock()
    mock_inventory_repo.get_by_server_id = AsyncMock(return_value=None)
    mock_inventory_repo.save = AsyncMock(side_effect=lambda s: s)

    service = InventoryService(mock_inventory_repo, mock_discovery_service)
    inventory = await service.create_from_discovery(server_id=1)

    assert inventory.server_id == 1
    assert inventory.hostname == "prod-web-01"
    mock_discovery_service.discover_server.assert_called_once_with(1)
    mock_inventory_repo.get_by_server_id.assert_called_once_with(1)
    mock_inventory_repo.save.assert_called_once()


@pytest.mark.asyncio
async def test_inventory_service_get_by_id():
    """Verify retrieval by ID raises NotFoundError if absent."""
    mock_discovery_service = MagicMock()
    mock_inventory_repo = MagicMock()
    mock_inventory_repo.get_by_id = AsyncMock(return_value=None)

    service = InventoryService(mock_inventory_repo, mock_discovery_service)

    with pytest.raises(NotFoundError):
        await service.get_inventory_by_id(999)


@pytest.mark.asyncio
async def test_inventory_service_update_metadata(sample_discovery_result):
    """Verify update_metadata correctly merges metadata and increments version."""
    inventory = DiscoveryMapper.to_inventory(sample_discovery_result)
    inventory.id = 10
    inventory.version = 1

    mock_discovery_service = MagicMock()
    mock_inventory_repo = MagicMock()
    mock_inventory_repo.get_by_id = AsyncMock(return_value=inventory)
    mock_inventory_repo.save = AsyncMock(side_effect=lambda s: s)

    service = InventoryService(mock_inventory_repo, mock_discovery_service)
    updated = await service.update_metadata(
        inventory_id=10,
        environment="staging",
        role="api-gateway",
        tags={"tier": "back"},
    )

    assert updated.metadata.environment == "staging"
    assert updated.metadata.role == "api-gateway"
    assert updated.metadata.tags == {"tier": "back"}
    assert updated.version == 2
    mock_inventory_repo.save.assert_called_once_with(updated)


# ---------- Repository Tests ----------
@pytest.mark.asyncio
async def test_postgres_inventory_repository_save():
    """Verify PostgresInventoryRepository save mapping calls database session."""
    mock_session = MagicMock()
    mock_session.add = MagicMock()
    mock_session.commit = AsyncMock()
    mock_session.refresh = AsyncMock()

    repo = PostgresInventoryRepository(mock_session)

    # Mock entity
    inventory = Inventory(
        id=None,
        server_id=1,
        hostname="host-1",
        operating_system="Linux",
        kernel_version="5.0",
        architecture="arm64",
        uptime="10m",
        timezone="UTC",
        cpu=CPUInfo(
            model="ARM", cores=4, sockets=1, threads_per_core=1, architecture="arm64"
        ),
        memory=MemoryInfo(
            total_mb=4096.0,
            used_mb=100.0,
            free_mb=3996.0,
            shared_mb=0.0,
            buff_cache_mb=0.0,
            available_mb=3996.0,
        ),
        disks=[],
        network_interfaces=[],
        last_discovered_at=datetime.now(timezone.utc),
    )

    # Set mock db model callback
    def mock_refresh(model):
        model.id = 55

    mock_session.refresh.side_effect = mock_refresh

    saved = await repo.save(inventory)
    assert saved.id == 55
    mock_session.add.assert_called_once()
    mock_session.commit.assert_called_once()

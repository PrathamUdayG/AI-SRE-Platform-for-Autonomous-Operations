# tests/application/test_server_service.py
"""Unit tests for the ServerService class."""

from unittest.mock import AsyncMock, MagicMock

import pytest

from src.application.services.server_service import ServerService
from src.domain.entities.server import Server
from src.domain.exceptions import ConflictError, ValidationError


@pytest.mark.asyncio
async def test_register_server_success():
    """Verify that a valid server registers successfully."""
    repo = MagicMock()
    repo.exists = AsyncMock(return_value=False)

    def mock_save(s):
        s.id = 42
        return s

    repo.save = AsyncMock(side_effect=mock_save)

    service = ServerService(repo)
    server = await service.register_server(
        hostname="test-host.example.com",
        ip_address="192.168.1.100",
        operating_system="Ubuntu 22.04",
        cpu_cores=8,
        memory_gb=32.0,
    )

    assert server.id == 42
    assert server.hostname == "test-host.example.com"
    assert server.ip_address == "192.168.1.100"
    repo.exists.assert_called_once_with("test-host.example.com", "192.168.1.100")
    repo.save.assert_called_once()


@pytest.mark.asyncio
async def test_register_server_validation_failures():
    """Verify registration fails with invalid hostnames, IPs or resources."""
    repo = MagicMock()
    service = ServerService(repo)

    # Invalid hostname format
    with pytest.raises(ValidationError) as exc:
        await service.register_server(
            hostname="-invalid-start",
            ip_address="192.168.1.100",
            operating_system="Ubuntu 22.04",
            cpu_cores=4,
            memory_gb=16.0,
        )
    assert "Invalid hostname format" in str(exc.value)

    # Invalid IP address format
    with pytest.raises(ValidationError) as exc:
        await service.register_server(
            hostname="valid-host.com",
            ip_address="999.999.999.999",
            operating_system="Ubuntu 22.04",
            cpu_cores=4,
            memory_gb=16.0,
        )
    assert "Invalid IP address format" in str(exc.value)

    # Invalid CPU count
    with pytest.raises(ValidationError) as exc:
        await service.register_server(
            hostname="valid-host.com",
            ip_address="192.168.1.100",
            operating_system="Ubuntu 22.04",
            cpu_cores=0,
            memory_gb=16.0,
        )
    assert "CPU cores must be greater than 0" in str(exc.value)


@pytest.mark.asyncio
async def test_register_server_conflict():
    """Verify registration fails if a server already exists with same hostname or IP."""
    repo = MagicMock()
    repo.exists = AsyncMock(return_value=True)

    service = ServerService(repo)
    with pytest.raises(ConflictError) as exc:
        await service.register_server(
            hostname="duplicate.com",
            ip_address="192.168.1.1",
            operating_system="Linux",
            cpu_cores=4,
            memory_gb=8.0,
        )
    assert "already exists" in str(exc.value)

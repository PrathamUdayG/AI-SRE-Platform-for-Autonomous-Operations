"""
-------------------------------------------------------
File:
test_docker_collector.py

Purpose:
Unit tests for the DockerCollector in the Infrastructure Layer.

Why this file exists:
Verifies that DockerCollector runs the expected commands, handles offline Docker states gracefully, and structures results.

Responsibilities:
- Verify properties (name, metric_type).
- Mock CommandExecutor to return success results and verify parsing integration.
- Verify fallback behavior when Docker daemon is not active.
- Verify behavior when Docker is not installed.

Used By:
- pytest runner

Depends On:
- src.infrastructure.collectors.docker_collector
- src.domain.executor.command_executor.CommandExecutor
-------------------------------------------------------
"""

from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock
import pytest

from src.domain.collectors.collector_status import CollectorStatus
from src.domain.collectors.metric_type import MetricType
from src.domain.executor.command_executor import CommandExecutor
from src.domain.executor.command_result import CommandResult
from src.infrastructure.collectors.docker_collector import DockerCollector


@pytest.fixture
def mock_executor():
    return MagicMock(spec=CommandExecutor)


@pytest.fixture
def collector(mock_executor):
    return DockerCollector(executor=mock_executor)


@pytest.mark.asyncio
async def test_collector_properties(collector):
    """Verify DockerCollector properties."""
    assert collector.name == "DockerCollector"
    assert collector.metric_type == MetricType.DOCKER


@pytest.mark.asyncio
async def test_collect_docker_daemon_down(collector, mock_executor):
    """Verify collector fails gracefully if docker daemon is down."""
    now = datetime.now(timezone.utc)
    
    hostname_res = CommandResult(
        command="hostname",
        arguments=[],
        stdout="my-host",
        stderr="",
        exit_code=0,
        execution_time_ms=1,
        timed_out=False,
        success=True,
        timestamp=now
    )
    
    ps_res = CommandResult(
        command="docker",
        arguments=["ps", "--no-trunc"],
        stdout="",
        stderr="Cannot connect to the Docker daemon",
        exit_code=1,
        execution_time_ms=5,
        timed_out=False,
        success=False,
        timestamp=now
    )

    async def mock_execute(command, arguments=None):
        if command == "hostname":
            return hostname_res
        elif command == "docker":
            return ps_res
        raise ValueError(f"Unexpected: {command}")

    mock_executor.execute = AsyncMock(side_effect=mock_execute)
    result = await collector.collect()
    
    assert result.status == CollectorStatus.FAILED
    assert "Docker daemon is unavailable" in result.errors[0]
    assert result.payload == {}


@pytest.mark.asyncio
async def test_collect_docker_not_installed(collector, mock_executor):
    """Verify collector fails gracefully if docker is not installed."""
    now = datetime.now(timezone.utc)
    
    hostname_res = CommandResult(
        command="hostname",
        arguments=[],
        stdout="my-host",
        stderr="",
        exit_code=0,
        execution_time_ms=1,
        timed_out=False,
        success=True,
        timestamp=now
    )

    async def mock_execute(command, arguments=None):
        if command == "hostname":
            return hostname_res
        elif command == "docker":
            raise FileNotFoundError("docker not found")
        raise ValueError(f"Unexpected: {command}")

    mock_executor.execute = AsyncMock(side_effect=mock_execute)
    result = await collector.collect()
    
    assert result.status == CollectorStatus.FAILED
    assert "Docker not installed" in result.errors[0]
    assert result.payload == {}


@pytest.mark.asyncio
async def test_collect_success(collector, mock_executor):
    """Verify successful collection when Docker is running."""
    now = datetime.now(timezone.utc)
    
    hostname_res = CommandResult(
        command="hostname",
        arguments=[],
        stdout="my-host",
        stderr="",
        exit_code=0,
        execution_time_ms=1,
        timed_out=False,
        success=True,
        timestamp=now
    )
    
    ps_res = CommandResult(
        command="docker",
        arguments=["ps", "--no-trunc"],
        stdout="CONTAINER ID   IMAGE     COMMAND   CREATED   STATUS    PORTS     NAMES\nd3a82643a6d7   nginx     cmd       2 hours   Up        80/tcp    my-nginx\n",
        stderr="",
        exit_code=0,
        execution_time_ms=5,
        timed_out=False,
        success=True,
        timestamp=now
    )
    
    inspect_res = CommandResult(
        command="docker",
        arguments=["inspect", "d3a82643a6d7"],
        stdout='[{"Id": "d3a82643a6d7", "Name": "/my-nginx", "Config": {"Image": "nginx"}, "State": {"Status": "running"}}]',
        stderr="",
        exit_code=0,
        execution_time_ms=5,
        timed_out=False,
        success=True,
        timestamp=now
    )
    
    stats_res = CommandResult(
        command="docker",
        arguments=["stats", "--no-stream", "--no-trunc"],
        stdout="CONTAINER ID   NAME      CPU %     MEM USAGE / LIMIT     MEM %     NET I/O           BLOCK I/O         PIDS\nd3a82643a6d7   my-nginx  0.1%      10MiB / 1GiB          1.0%      1kB / 0B          0B / 0B           1\n",
        stderr="",
        exit_code=0,
        execution_time_ms=5,
        timed_out=False,
        success=True,
        timestamp=now
    )
    
    network_res = CommandResult(
        command="docker",
        arguments=["network", "ls"],
        stdout="NETWORK ID     NAME      DRIVER    SCOPE\nbridge-id      bridge    bridge    local\n",
        stderr="",
        exit_code=0,
        execution_time_ms=5,
        timed_out=False,
        success=True,
        timestamp=now
    )
    
    volume_res = CommandResult(
        command="docker",
        arguments=["volume", "ls"],
        stdout="DRIVER    VOLUME NAME\nlocal     vol1\n",
        stderr="",
        exit_code=0,
        execution_time_ms=5,
        timed_out=False,
        success=True,
        timestamp=now
    )

    async def mock_execute(command, arguments=None):
        if command == "hostname":
            return hostname_res
        elif command == "docker":
            if arguments == ["ps", "--no-trunc"]:
                return ps_res
            elif arguments == ["inspect", "d3a82643a6d7"]:
                return inspect_res
            elif arguments == ["stats", "--no-stream", "--no-trunc"]:
                return stats_res
            elif arguments == ["network", "ls"]:
                return network_res
            elif arguments == ["volume", "ls"]:
                return volume_res
        raise ValueError(f"Unexpected: {command} {arguments}")

    mock_executor.execute = AsyncMock(side_effect=mock_execute)
    result = await collector.collect()
    
    assert result.status == CollectorStatus.SUCCESS
    assert result.errors == []
    assert len(result.payload["containers"]) == 1
    assert result.payload["containers"][0]["name"] == "my-nginx"
    assert len(result.payload["stats"]) == 1
    assert result.payload["stats"][0]["cpu_percentage"] == 0.1
    assert len(result.payload["networks"]) == 1
    assert len(result.payload["volumes"]) == 1

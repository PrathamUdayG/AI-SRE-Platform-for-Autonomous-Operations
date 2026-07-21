"""
-------------------------------------------------------
File:
test_network_collector.py

Purpose:
Unit tests for the NetworkCollector in the Infrastructure Layer.

Why this file exists:
Verifies that the NetworkCollector coordinates command executions, passes outputs to NetworkParser, and returns structured CollectorResults.

Responsibilities:
- Verify properties (name, metric_type).
- Mock CommandExecutor to return success results and verify parsing integration.
- Verify error capturing when command execution fails.
- Verify error capturing when parser fails.

Used By:
- pytest runner

Depends On:
- src.infrastructure.collectors.network_collector
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
from src.infrastructure.collectors.network_collector import NetworkCollector


@pytest.fixture
def mock_executor():
    return MagicMock(spec=CommandExecutor)


@pytest.fixture
def collector(mock_executor):
    return NetworkCollector(executor=mock_executor)


@pytest.mark.asyncio
async def test_collector_properties(collector):
    """Verify NetworkCollector properties."""
    assert collector.name == "NetworkCollector"
    assert collector.metric_type == MetricType.NETWORK


@pytest.mark.asyncio
async def test_collect_success(collector, mock_executor):
    """Verify collector output structure on successful executions."""
    now = datetime.now(timezone.utc)

    hostname_res = CommandResult(
        command="hostname",
        arguments=[],
        stdout="my-net-host",
        stderr="",
        exit_code=0,
        execution_time_ms=1,
        timed_out=False,
        success=True,
        timestamp=now
    )

    dev_res = CommandResult(
        command="cat",
        arguments=["/proc/net/dev"],
        stdout="""
Inter-|   Receive                                                |  Transmit
 face |bytes    packets errs drop fifo frame compressed multicast|bytes    packets errs drop fifo colls carrier compressed
    lo: 100 1 0 0 0 0 0 0 100 1 0 0 0 0 0 0
        """,
        stderr="",
        exit_code=0,
        execution_time_ms=3,
        timed_out=False,
        success=True,
        timestamp=now
    )

    addr_res = CommandResult(
        command="ip",
        arguments=["-o", "addr", "show"],
        stdout="1: lo    inet 127.0.0.1/8 scope host lo\\",
        stderr="",
        exit_code=0,
        execution_time_ms=3,
        timed_out=False,
        success=True,
        timestamp=now
    )

    route_res = CommandResult(
        command="ip",
        arguments=["route", "show"],
        stdout="default via 192.168.1.1 dev eth0 proto dhcp metric 100",
        stderr="",
        exit_code=0,
        execution_time_ms=3,
        timed_out=False,
        success=True,
        timestamp=now
    )

    tcp_res = CommandResult(
        command="cat",
        arguments=["/proc/net/tcp"],
        stdout="  sl  local_address rem_address   st tx_queue rx_queue tr tm->when retrnsmt   uid  timeout inode\n   0: 0100007F:0050 00000000:0000 0A 00000000:00000000 00:00000000 00000000  1000        0 12345 1",
        stderr="",
        exit_code=0,
        execution_time_ms=3,
        timed_out=False,
        success=True,
        timestamp=now
    )

    udp_res = CommandResult(
        command="cat",
        arguments=["/proc/net/udp"],
        stdout="  sl  local_address rem_address   st tx_queue rx_queue tr tm->when retrnsmt   uid  timeout inode\n   0: 0100007F:0035 00000000:0000 07 00000000:00000000 00:00000000 00000000  1000        0 12347 1",
        stderr="",
        exit_code=0,
        execution_time_ms=3,
        timed_out=False,
        success=True,
        timestamp=now
    )

    async def mock_execute(command, arguments=None):
        if command == "hostname":
            return hostname_res
        elif command == "cat" and arguments == ["/proc/net/dev"]:
            return dev_res
        elif command == "ip" and arguments == ["-o", "addr", "show"]:
            return addr_res
        elif command == "ip" and arguments == ["route", "show"]:
            return route_res
        elif command == "cat" and arguments == ["/proc/net/tcp"]:
            return tcp_res
        elif command == "cat" and arguments == ["/proc/net/udp"]:
            return udp_res
        raise ValueError(f"Unexpected command: {command}")

    mock_executor.execute = AsyncMock(side_effect=mock_execute)

    result = await collector.collect()

    assert result.collector_name == "NetworkCollector"
    assert result.metric_type == MetricType.NETWORK
    assert result.status == CollectorStatus.SUCCESS
    assert result.hostname == "my-net-host"
    assert result.errors == []
    
    assert len(result.payload["interfaces"]) == 1
    assert result.payload["interfaces"][0]["interface_name"] == "lo"
    assert len(result.payload["configurations"]) == 1
    assert result.payload["configurations"][0]["ip_address"] == "127.0.0.1"


@pytest.mark.asyncio
async def test_collect_command_failure(collector, mock_executor):
    """Verify collector handles non-zero exit codes during collection."""
    now = datetime.now(timezone.utc)

    hostname_res = CommandResult(
        command="hostname", arguments=[], stdout="host", stderr="", exit_code=0, execution_time_ms=1, timed_out=False, success=True, timestamp=now
    )

    error_res = CommandResult(
        command="cat",
        arguments=["/proc/net/dev"],
        stdout="",
        stderr="No such file",
        exit_code=1,
        execution_time_ms=2,
        timed_out=False,
        success=False,
        timestamp=now
    )

    async def mock_execute(command, arguments=None):
        if command == "hostname":
            return hostname_res
        return error_res

    mock_executor.execute = AsyncMock(side_effect=mock_execute)

    result = await collector.collect()

    assert result.status == CollectorStatus.FAILED
    assert len(result.errors) == 1
    assert "Failed to gather network" in result.errors[0]
    assert result.payload == {}


@pytest.mark.asyncio
async def test_collect_parsing_failure(collector, mock_executor):
    """Verify collector logs parser errors when outputs are corrupted."""
    now = datetime.now(timezone.utc)

    hostname_res = CommandResult(
        command="hostname", arguments=[], stdout="host", stderr="", exit_code=0, execution_time_ms=1, timed_out=False, success=True, timestamp=now
    )

    garbage_res = CommandResult(
        command="cat",
        arguments=[],
        stdout="",
        stderr="",
        exit_code=0,
        execution_time_ms=2,
        timed_out=False,
        success=True,
        timestamp=now
    )

    async def mock_execute(command, arguments=None):
        if command == "hostname":
            return hostname_res
        return garbage_res

    mock_executor.execute = AsyncMock(side_effect=mock_execute)

    result = await collector.collect()

    assert result.status == CollectorStatus.FAILED
    assert len(result.errors) == 1
    assert "Parsing failed" in result.errors[0]
    assert result.payload == {}


"""
-------------------------------------------------------
File:
test_system_collector.py

Purpose:
Unit tests for the SystemCollector in the Infrastructure Layer.

Why this file exists:
Verifies that SystemCollector coordinates static system commands and builds CollectorResults.

Responsibilities:
- Verify properties (name, metric_type).
- Mock CommandExecutor to return success results and verify parsing integration.
- Verify error capturing when command execution fails.
- Verify error capturing when parser fails.

Used By:
- pytest runner

Depends On:
- src.infrastructure.collectors.system_collector
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
from src.infrastructure.collectors.system_collector import SystemCollector


@pytest.fixture
def mock_executor():
    return MagicMock(spec=CommandExecutor)


@pytest.fixture
def collector(mock_executor):
    return SystemCollector(executor=mock_executor)


@pytest.mark.asyncio
async def test_collector_properties(collector):
    """Verify SystemCollector properties."""
    assert collector.name == "SystemCollector"
    assert collector.metric_type == MetricType.SYSTEM


@pytest.mark.asyncio
async def test_collect_success(collector, mock_executor):
    """Verify collector output structure on successful executions."""
    now = datetime.now(timezone.utc)

    hostname_res = CommandResult(
        command="hostname",
        arguments=[],
        stdout="my-sys-host",
        stderr="",
        exit_code=0,
        execution_time_ms=1,
        timed_out=False,
        success=True,
        timestamp=now
    )

    hctl_res = CommandResult(
        command="hostnamectl",
        arguments=[],
        stdout="Static hostname: my-sys-host\nMachine ID: 123\nBoot ID: 456\nVirtualization: kvm",
        stderr="",
        exit_code=0,
        execution_time_ms=3,
        timed_out=False,
        success=True,
        timestamp=now
    )

    uname_res = CommandResult(
        command="uname",
        arguments=["-a"],
        stdout="Linux my-sys-host 5.15.0-88-generic #98-Ubuntu SMP Mon Oct 2 x86_64 GNU/Linux",
        stderr="",
        exit_code=0,
        execution_time_ms=3,
        timed_out=False,
        success=True,
        timestamp=now
    )

    osrel_res = CommandResult(
        command="cat",
        arguments=["/etc/os-release"],
        stdout="NAME=\"Ubuntu\"\nVERSION_ID=\"22.04\"\nPRETTY_NAME=\"Ubuntu 22.04.3 LTS\"",
        stderr="",
        exit_code=0,
        execution_time_ms=3,
        timed_out=False,
        success=True,
        timestamp=now
    )

    lscpu_res = CommandResult(
        command="lscpu",
        arguments=[],
        stdout="Architecture: x86_64\nCPU(s): 4\nVendor ID: GenuineIntel\nModel name: Intel Core\nThread(s) per core: 2\nCore(s) per socket: 2\nSocket(s): 1",
        stderr="",
        exit_code=0,
        execution_time_ms=3,
        timed_out=False,
        success=True,
        timestamp=now
    )

    uptime_res = CommandResult(
        command="uptime",
        arguments=[],
        stdout=" 14:22:00 up 12 days,  3:15,  1 user",
        stderr="",
        exit_code=0,
        execution_time_ms=3,
        timed_out=False,
        success=True,
        timestamp=now
    )

    tz_res = CommandResult(
        command="cat",
        arguments=["/etc/timezone"],
        stdout="Europe/London\n",
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
        elif command == "hostnamectl":
            return hctl_res
        elif command == "uname":
            return uname_res
        elif command == "cat" and arguments == ["/etc/os-release"]:
            return osrel_res
        elif command == "lscpu":
            return lscpu_res
        elif command == "uptime":
            return uptime_res
        elif command == "cat" and arguments == ["/etc/timezone"]:
            return tz_res
        raise ValueError(f"Unexpected command: {command} {arguments}")

    mock_executor.execute = AsyncMock(side_effect=mock_execute)

    result = await collector.collect()

    assert result.collector_name == "SystemCollector"
    assert result.metric_type == MetricType.SYSTEM
    assert result.status == CollectorStatus.SUCCESS
    assert result.hostname == "my-sys-host"
    assert result.errors == []
    
    assert result.payload["host_identity"]["hostname"] == "my-sys-host"
    assert result.payload["os_info"]["distribution_name"] == "Ubuntu"
    assert result.payload["cpu_info"]["logical_cpu_count"] == 4


@pytest.mark.asyncio
async def test_collect_command_failure(collector, mock_executor):
    """Verify collector handles command failure gracefully."""
    now = datetime.now(timezone.utc)

    hostname_res = CommandResult(
        command="hostname", arguments=[], stdout="host", stderr="", exit_code=0, execution_time_ms=1, timed_out=False, success=True, timestamp=now
    )

    error_res = CommandResult(
        command="uname",
        arguments=["-a"],
        stdout="",
        stderr="uname error",
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
    assert "Failed to gather system metadata" in result.errors[0]
    assert result.payload == {}


@pytest.mark.asyncio
async def test_collect_parsing_failure(collector, mock_executor):
    """Verify collector handles parser validation failures gracefully."""
    now = datetime.now(timezone.utc)

    hostname_res = CommandResult(
        command="hostname", arguments=[], stdout="host", stderr="", exit_code=0, execution_time_ms=1, timed_out=False, success=True, timestamp=now
    )

    garbage_res = CommandResult(
        command="uname",
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

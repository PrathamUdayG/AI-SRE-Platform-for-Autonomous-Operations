"""
-------------------------------------------------------
File:
test_cpu_collector.py

Purpose:
Unit tests for the CPUCollector in the Infrastructure Layer.

Why this file exists:
Verifies that the CPUCollector integrates command execution and parsing workflows. It ensures successful collections return a validated CPU telemetry payload, and command execution or parsing failures are isolated and returned as failures.

Responsibilities:
- Verify collector properties (name, metric_type).
- Mock CommandExecutor to return success results and verify parsing integration.
- Verify error capturing when command execution fails.
- Verify error capturing when parser fails.

Used By:
- pytest runner

Depends On:
- src.infrastructure.collectors.cpu_collector
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
from src.infrastructure.collectors.cpu_collector import CPUCollector


@pytest.fixture
def mock_executor():
    return MagicMock(spec=CommandExecutor)


@pytest.fixture
def collector(mock_executor):
    return CPUCollector(executor=mock_executor)


@pytest.mark.asyncio
async def test_collector_properties(collector):
    """Verify CPUCollector static properties."""
    assert collector.name == "CPUCollector"
    assert collector.metric_type == MetricType.CPU


@pytest.mark.asyncio
async def test_collect_success(collector, mock_executor):
    """Verify collector output structure and parsing flow on successful commands."""
    now = datetime.now(timezone.utc)

    hostname_res = CommandResult(
        command="hostname",
        arguments=[],
        stdout="my-cpu-host",
        stderr="",
        exit_code=0,
        execution_time_ms=1,
        timed_out=False,
        success=True,
        timestamp=now
    )

    stat_res = CommandResult(
        command="cat",
        arguments=["/proc/stat"],
        stdout="cpu  2255 34 2290 22625563 6290 127 456 0 0 0",
        stderr="",
        exit_code=0,
        execution_time_ms=3,
        timed_out=False,
        success=True,
        timestamp=now
    )

    loadavg_res = CommandResult(
        command="cat",
        arguments=["/proc/loadavg"],
        stdout="0.20 0.18 0.12 1/450 12345",
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
        elif command == "cat" and arguments == ["/proc/stat"]:
            return stat_res
        elif command == "cat" and arguments == ["/proc/loadavg"]:
            return loadavg_res
        raise ValueError(f"Unexpected command: {command}")

    mock_executor.execute = AsyncMock(side_effect=mock_execute)

    result = await collector.collect()

    assert result.collector_name == "CPUCollector"
    assert result.metric_type == MetricType.CPU
    assert result.status == CollectorStatus.SUCCESS
    assert result.hostname == "my-cpu-host"
    assert result.errors == []
    assert result.payload["user_ticks"] == 2255
    assert result.payload["system_ticks"] == 2290
    assert result.payload["load_average_1m"] == 0.20
    assert result.payload["logical_cpu_count"] == 1


@pytest.mark.asyncio
async def test_collect_command_failure(collector, mock_executor):
    """Verify collector handles non-zero exit codes or execution failures."""
    now = datetime.now(timezone.utc)

    hostname_res = CommandResult(
        command="hostname", arguments=[], stdout="host", stderr="", exit_code=0, execution_time_ms=1, timed_out=False, success=True, timestamp=now
    )

    stat_res = CommandResult(
        command="cat",
        arguments=["/proc/stat"],
        stdout="",
        stderr="Permission denied",
        exit_code=1,
        execution_time_ms=2,
        timed_out=False,
        success=False,
        timestamp=now
    )

    async def mock_execute(command, arguments=None):
        if command == "hostname":
            return hostname_res
        elif command == "cat" and arguments == ["/proc/stat"]:
            return stat_res
        # loadavg is not queryable since the first execution failed
        return stat_res

    mock_executor.execute = AsyncMock(side_effect=mock_execute)

    result = await collector.collect()

    assert result.status == CollectorStatus.FAILED
    assert len(result.errors) == 1
    assert "Failed to read /proc/stat" in result.errors[0]
    assert result.payload == {}


@pytest.mark.asyncio
async def test_collect_parsing_failure(collector, mock_executor):
    """Verify collector captures parsing exceptions when output is invalid."""
    now = datetime.now(timezone.utc)

    hostname_res = CommandResult(
        command="hostname", arguments=[], stdout="host", stderr="", exit_code=0, execution_time_ms=1, timed_out=False, success=True, timestamp=now
    )

    stat_res = CommandResult(
        command="cat",
        arguments=["/proc/stat"],
        stdout="completely garbage output",
        stderr="",
        exit_code=0,
        execution_time_ms=2,
        timed_out=False,
        success=True,
        timestamp=now
    )

    loadavg_res = CommandResult(
        command="cat",
        arguments=["/proc/loadavg"],
        stdout="0.20 0.18 0.12 1/450 12345",
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
        elif command == "cat" and arguments == ["/proc/stat"]:
            return stat_res
        elif command == "cat" and arguments == ["/proc/loadavg"]:
            return loadavg_res
        raise ValueError(f"Unexpected command: {command}")

    mock_executor.execute = AsyncMock(side_effect=mock_execute)

    result = await collector.collect()

    assert result.status == CollectorStatus.FAILED
    assert len(result.errors) == 1
    assert "Parsing failed" in result.errors[0]
    assert result.payload == {}

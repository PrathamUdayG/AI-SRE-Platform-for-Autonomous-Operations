"""
-------------------------------------------------------
File:
test_memory_collector.py

Purpose:
Unit tests for the MemoryCollector in the Infrastructure Layer.

Why this file exists:
Verifies that the collector integrates command execution and parsing flows. It ensures successful collections return a validated CollectorResult, while command failures or parsing errors are captured as structured errors without raising unhandled exceptions.

Responsibilities:
- Verify collector properties (name, metric_type).
- Mock CommandExecutor to return success results and verify parsing integration.
- Verify hostname command is queried correctly.
- Verify error capturing when the command fails.
- Verify error capturing when command output is malformed.

Used By:
- pytest runner

Depends On:
- src.infrastructure.collectors.memory_collector
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
from src.infrastructure.collectors.memory_collector import MemoryCollector


@pytest.fixture
def mock_executor():
    return MagicMock(spec=CommandExecutor)


@pytest.fixture
def collector(mock_executor):
    return MemoryCollector(executor=mock_executor)


@pytest.mark.asyncio
async def test_collector_properties(collector):
    """Verify that name and metric_type properties are correctly set."""
    assert collector.name == "MemoryCollector"
    assert collector.metric_type == MetricType.MEMORY


@pytest.mark.asyncio
async def test_collect_success(collector, mock_executor):
    """Verify collector output structure and parsing flow on successful commands."""
    now = datetime.now(timezone.utc)
    
    # Mock hostname execution
    hostname_res = CommandResult(
        command="hostname",
        arguments=[],
        stdout="my-test-host",
        stderr="",
        exit_code=0,
        execution_time_ms=2,
        timed_out=False,
        success=True,
        timestamp=now
    )
    
    # Mock cat /proc/meminfo execution
    meminfo_res = CommandResult(
        command="cat",
        arguments=["/proc/meminfo"],
        stdout="""
        MemTotal:       16388432 kB
        MemFree:         4321098 kB
        MemAvailable:   10098432 kB
        """,
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
        elif command == "cat" and arguments == ["/proc/meminfo"]:
            return meminfo_res
        raise ValueError(f"Unexpected command call: {command}")

    mock_executor.execute = AsyncMock(side_effect=mock_execute)

    result = await collector.collect()

    assert result.collector_name == "MemoryCollector"
    assert result.metric_type == MetricType.MEMORY
    assert result.status == CollectorStatus.SUCCESS
    assert result.hostname == "my-test-host"
    assert result.errors == []
    
    # Verify payload contents mapped from MemoryMetrics
    assert result.payload["total_memory_kb"] == 16388432
    assert result.payload["free_memory_kb"] == 4321098
    assert result.payload["available_memory_kb"] == 10098432
    assert result.payload["swap_total_kb"] == 0  # Missing, defaults to 0


@pytest.mark.asyncio
async def test_collect_command_failure(collector, mock_executor):
    """Verify collector handles non-zero exit codes or command failures gracefully."""
    now = datetime.now(timezone.utc)
    
    hostname_res = CommandResult(
        command="hostname",
        arguments=[],
        stdout="",
        stderr="Failed to retrieve host name",
        exit_code=1,
        execution_time_ms=1,
        timed_out=False,
        success=False,
        timestamp=now
    )
    
    meminfo_res = CommandResult(
        command="cat",
        arguments=["/proc/meminfo"],
        stdout="",
        stderr="Permission denied",
        exit_code=1,
        execution_time_ms=3,
        timed_out=False,
        success=False,
        timestamp=now
    )

    async def mock_execute(command, arguments=None):
        if command == "hostname":
            return hostname_res
        elif command == "cat":
            return meminfo_res
        raise ValueError(f"Unexpected command call: {command}")

    mock_executor.execute = AsyncMock(side_effect=mock_execute)

    result = await collector.collect()

    assert result.status == CollectorStatus.FAILED
    assert result.hostname == "unknown"  # Hostname command failed
    assert len(result.errors) == 1
    assert "Command execution failed" in result.errors[0]
    assert result.payload == {}


@pytest.mark.asyncio
async def test_collect_parsing_failure(collector, mock_executor):
    """Verify collector captures parsing errors from malformed command output."""
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
    
    meminfo_res = CommandResult(
        command="cat",
        arguments=["/proc/meminfo"],
        stdout="completely garbage text output",
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
        elif command == "cat":
            return meminfo_res
        raise ValueError(f"Unexpected command: {command}")

    mock_executor.execute = AsyncMock(side_effect=mock_execute)

    result = await collector.collect()

    assert result.status == CollectorStatus.FAILED
    assert result.hostname == "my-host"
    assert len(result.errors) == 1
    assert "Parsing failed" in result.errors[0]
    assert result.payload == {}

"""
-------------------------------------------------------
File:
test_disk_collector.py

Purpose:
Unit tests for the DiskCollector in the Infrastructure Layer.

Why this file exists:
Verifies that the DiskCollector coordinates df execution and proc queries, calling DiskParser, and returns structured CollectorResults.

Responsibilities:
- Verify collector properties (name, metric_type).
- Mock CommandExecutor to return success results and verify parsing integration.
- Verify error capturing when command execution fails.
- Verify error capturing when parser fails.

Used By:
- pytest runner

Depends On:
- src.infrastructure.collectors.disk_collector
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
from src.infrastructure.collectors.disk_collector import DiskCollector


@pytest.fixture
def mock_executor():
    return MagicMock(spec=CommandExecutor)


@pytest.fixture
def collector(mock_executor):
    return DiskCollector(executor=mock_executor)


@pytest.mark.asyncio
async def test_collector_properties(collector):
    """Verify DiskCollector properties."""
    assert collector.name == "DiskCollector"
    assert collector.metric_type == MetricType.DISK


@pytest.mark.asyncio
async def test_collect_success(collector, mock_executor):
    """Verify collector output structure on successful executions."""
    now = datetime.now(timezone.utc)

    hostname_res = CommandResult(
        command="hostname",
        arguments=[],
        stdout="my-disk-host",
        stderr="",
        exit_code=0,
        execution_time_ms=1,
        timed_out=False,
        success=True,
        timestamp=now
    )

    df_res = CommandResult(
        command="df",
        arguments=["-B1", "--output=source,fstype,size,used,avail,pcent,target"],
        stdout="""
        Filesystem     Type        1B-blocks         Used    Available Use% Mounted on
        /dev/sda1      ext4      31260487680  10485760000  19178967040  36% /
        """,
        stderr="",
        exit_code=0,
        execution_time_ms=5,
        timed_out=False,
        success=True,
        timestamp=now
    )

    stats_res = CommandResult(
        command="cat",
        arguments=["/proc/diskstats"],
        stdout="   8       0 sda 102434 23098 5439812 129384 54318 29018 4392811 543921 0 129848 643928",
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
        elif command == "df" and arguments == ["-B1", "--output=source,fstype,size,used,avail,pcent,target"]:
            return df_res
        elif command == "cat" and arguments == ["/proc/diskstats"]:
            return stats_res
        raise ValueError(f"Unexpected command: {command}")

    mock_executor.execute = AsyncMock(side_effect=mock_execute)

    result = await collector.collect()

    assert result.collector_name == "DiskCollector"
    assert result.metric_type == MetricType.DISK
    assert result.status == CollectorStatus.SUCCESS
    assert result.hostname == "my-disk-host"
    assert result.errors == []
    
    # Check payload fields
    assert len(result.payload["filesystems"]) == 1
    assert result.payload["filesystems"][0]["filesystem"] == "/dev/sda1"
    assert result.payload["filesystems"][0]["total_bytes"] == 31260487680
    
    assert len(result.payload["disk_io"]) == 1
    assert result.payload["disk_io"][0]["device_name"] == "sda"
    assert result.payload["disk_io"][0]["reads_completed"] == 102434


@pytest.mark.asyncio
async def test_collect_df_command_failure(collector, mock_executor):
    """Verify collector logs error when df execution fails."""
    now = datetime.now(timezone.utc)

    hostname_res = CommandResult(
        command="hostname", arguments=[], stdout="host", stderr="", exit_code=0, execution_time_ms=1, timed_out=False, success=True, timestamp=now
    )

    df_res = CommandResult(
        command="df",
        arguments=["-B1", "--output=source,fstype,size,used,avail,pcent,target"],
        stdout="",
        stderr="df error",
        exit_code=1,
        execution_time_ms=2,
        timed_out=False,
        success=False,
        timestamp=now
    )

    async def mock_execute(command, arguments=None):
        if command == "hostname":
            return hostname_res
        return df_res

    mock_executor.execute = AsyncMock(side_effect=mock_execute)

    result = await collector.collect()

    assert result.status == CollectorStatus.FAILED
    assert len(result.errors) == 1
    assert "Failed to execute df" in result.errors[0]
    assert result.payload == {}


@pytest.mark.asyncio
async def test_collect_parsing_failure(collector, mock_executor):
    """Verify collector handles parser crashes gracefully."""
    now = datetime.now(timezone.utc)

    hostname_res = CommandResult(
        command="hostname", arguments=[], stdout="host", stderr="", exit_code=0, execution_time_ms=1, timed_out=False, success=True, timestamp=now
    )

    df_res = CommandResult(
        command="df",
        arguments=["-B1", "--output=source,fstype,size,used,avail,pcent,target"],
        stdout="completely garbage output",
        stderr="",
        exit_code=0,
        execution_time_ms=2,
        timed_out=False,
        success=True,
        timestamp=now
    )

    stats_res = CommandResult(
        command="cat",
        arguments=["/proc/diskstats"],
        stdout="completely garbage output",
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
        elif command == "df":
            return df_res
        elif command == "cat":
            return stats_res
        raise ValueError(f"Unexpected: {command}")

    mock_executor.execute = AsyncMock(side_effect=mock_execute)

    result = await collector.collect()

    assert result.status == CollectorStatus.FAILED
    assert len(result.errors) == 1
    assert "Parsing failed" in result.errors[0]
    assert result.payload == {}

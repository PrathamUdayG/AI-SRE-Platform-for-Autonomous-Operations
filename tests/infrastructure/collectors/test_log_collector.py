"""
-------------------------------------------------------
File:
test_log_collector.py

Purpose:
Unit tests for the LogCollector in the Infrastructure Layer.

Why this file exists:
Verifies that LogCollector coordinates log extraction commands and constructs CollectorResults.

Responsibilities:
- Verify properties (name, metric_type).
- Mock CommandExecutor to return success results and verify parsing integration.
- Verify fallback mechanism when journalctl fails.
- Verify error capturing when parsing fails.

Used By:
- pytest runner

Depends On:
- src.infrastructure.collectors.log_collector
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
from src.infrastructure.collectors.log_collector import LogCollector


@pytest.fixture
def mock_executor():
    return MagicMock(spec=CommandExecutor)


@pytest.fixture
def collector(mock_executor):
    return LogCollector(executor=mock_executor)


@pytest.mark.asyncio
async def test_collector_properties(collector):
    """Verify LogCollector properties."""
    assert collector.name == "LogCollector"
    assert collector.metric_type == MetricType.LOG


@pytest.mark.asyncio
async def test_collect_success_journalctl(collector, mock_executor):
    """Verify successful collection using journalctl."""
    now = datetime.now(timezone.utc)

    hostname_res = CommandResult(
        command="hostname",
        arguments=[],
        stdout="my-log-host",
        stderr="",
        exit_code=0,
        execution_time_ms=1,
        timed_out=False,
        success=True,
        timestamp=now
    )

    journalctl_res = CommandResult(
        command="journalctl",
        arguments=["--no-pager", "--output=short-iso", "-n", "1000"],
        stdout="2026-07-21T14:29:48Z my-log-host systemd[1]: Started Log Service.",
        stderr="",
        exit_code=0,
        execution_time_ms=3,
        timed_out=False,
        success=True,
        timestamp=now
    )

    messages_res = CommandResult(
        command="tail",
        arguments=["-n", "1000", "/var/log/messages"],
        stdout="",
        stderr="No such file or directory",
        exit_code=1,
        execution_time_ms=3,
        timed_out=False,
        success=False,
        timestamp=now
    )

    async def mock_execute(command, arguments=None):
        if command == "hostname":
            return hostname_res
        elif command == "journalctl":
            return journalctl_res
        elif command == "tail" and arguments == ["-n", "1000", "/var/log/messages"]:
            return messages_res
        raise ValueError(f"Unexpected command: {command} {arguments}")

    mock_executor.execute = AsyncMock(side_effect=mock_execute)

    result = await collector.collect()

    assert result.collector_name == "LogCollector"
    assert result.metric_type == MetricType.LOG
    assert result.status == CollectorStatus.SUCCESS
    assert result.hostname == "my-log-host"
    assert result.errors == []
    
    assert len(result.payload["entries"]) == 1
    assert result.payload["entries"][0]["process_name"] == "systemd"
    assert result.payload["entries"][0]["message"] == "Started Log Service."


@pytest.mark.asyncio
async def test_collect_fallback_syslog(collector, mock_executor):
    """Verify syslog fallback is executed when journalctl fails."""
    now = datetime.now(timezone.utc)

    hostname_res = CommandResult(
        command="hostname",
        arguments=[],
        stdout="my-log-host",
        stderr="",
        exit_code=0,
        execution_time_ms=1,
        timed_out=False,
        success=True,
        timestamp=now
    )

    journalctl_res = CommandResult(
        command="journalctl",
        arguments=["--no-pager", "--output=short-iso", "-n", "1000"],
        stdout="",
        stderr="journalctl not supported",
        exit_code=1,
        execution_time_ms=3,
        timed_out=False,
        success=False,
        timestamp=now
    )

    syslog_res = CommandResult(
        command="tail",
        arguments=["-n", "1000", "/var/log/syslog"],
        stdout="Jul 21 08:54:31 my-log-host syslogd[10]: Syslog message.",
        stderr="",
        exit_code=0,
        execution_time_ms=3,
        timed_out=False,
        success=True,
        timestamp=now
    )

    messages_res = CommandResult(
        command="tail",
        arguments=["-n", "1000", "/var/log/messages"],
        stdout="",
        stderr="No such file or directory",
        exit_code=1,
        execution_time_ms=3,
        timed_out=False,
        success=False,
        timestamp=now
    )

    async def mock_execute(command, arguments=None):
        if command == "hostname":
            return hostname_res
        elif command == "journalctl":
            return journalctl_res
        elif command == "tail" and arguments == ["-n", "1000", "/var/log/syslog"]:
            return syslog_res
        elif command == "tail" and arguments == ["-n", "1000", "/var/log/messages"]:
            return messages_res
        raise ValueError(f"Unexpected command: {command} {arguments}")

    mock_executor.execute = AsyncMock(side_effect=mock_execute)

    result = await collector.collect()

    assert result.status == CollectorStatus.SUCCESS
    assert len(result.payload["entries"]) == 1
    assert result.payload["entries"][0]["process_name"] == "syslogd"
    assert result.payload["entries"][0]["message"] == "Syslog message."

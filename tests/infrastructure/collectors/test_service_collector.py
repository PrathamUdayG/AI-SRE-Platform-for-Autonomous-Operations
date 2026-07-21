"""
-------------------------------------------------------
File:
test_service_collector.py

Purpose:
Unit tests for the ServiceCollector in the Infrastructure Layer.

Why this file exists:
Verifies that the ServiceCollector coordinates command executions, passes outputs to ServiceParser, and returns structured CollectorResults.

Responsibilities:
- Verify properties (name, metric_type).
- Mock CommandExecutor to return success results and verify parsing integration.
- Verify error capturing when command execution fails.
- Verify error capturing when parser fails.

Used By:
- pytest runner

Depends On:
- src.infrastructure.collectors.service_collector
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
from src.infrastructure.collectors.service_collector import ServiceCollector


@pytest.fixture
def mock_executor():
    return MagicMock(spec=CommandExecutor)


@pytest.fixture
def collector(mock_executor):
    return ServiceCollector(executor=mock_executor)


@pytest.mark.asyncio
async def test_collector_properties(collector):
    """Verify ServiceCollector properties."""
    assert collector.name == "ServiceCollector"
    assert collector.metric_type == MetricType.SERVICE


@pytest.mark.asyncio
async def test_collect_success(collector, mock_executor):
    """Verify collector output structure on successful executions."""
    now = datetime.now(timezone.utc)

    hostname_res = CommandResult(
        command="hostname",
        arguments=[],
        stdout="my-service-host",
        stderr="",
        exit_code=0,
        execution_time_ms=1,
        timed_out=False,
        success=True,
        timestamp=now
    )

    list_res = CommandResult(
        command="systemctl",
        arguments=["list-units", "--type=service", "--all", "--no-pager", "--no-legend"],
        stdout="cron.service          loaded active running Regular background program processing daemon",
        stderr="",
        exit_code=0,
        execution_time_ms=3,
        timed_out=False,
        success=True,
        timestamp=now
    )

    show_res = CommandResult(
        command="systemctl",
        arguments=["show", "cron.service"],
        stdout="Id=cron.service\nDescription=Regular background program\nLoadState=loaded\nActiveState=active\nSubState=running\nUnitFileState=enabled\nMainPID=1200",
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
        elif command == "systemctl" and "list-units" in arguments:
            return list_res
        elif command == "systemctl" and "show" in arguments:
            return show_res
        raise ValueError(f"Unexpected command: {command}")

    mock_executor.execute = AsyncMock(side_effect=mock_execute)

    result = await collector.collect()

    assert result.collector_name == "ServiceCollector"
    assert result.metric_type == MetricType.SERVICE
    assert result.status == CollectorStatus.SUCCESS
    assert result.hostname == "my-service-host"
    assert result.errors == []
    
    assert len(result.payload["services"]) == 1
    assert result.payload["services"][0]["name"] == "cron.service"
    assert result.payload["services"][0]["is_enabled"] is True
    assert result.payload["services"][0]["main_pid"] == 1200


@pytest.mark.asyncio
async def test_collect_command_failure(collector, mock_executor):
    """Verify collector handles non-zero exit codes during collection."""
    now = datetime.now(timezone.utc)

    hostname_res = CommandResult(
        command="hostname", arguments=[], stdout="host", stderr="", exit_code=0, execution_time_ms=1, timed_out=False, success=True, timestamp=now
    )

    error_res = CommandResult(
        command="systemctl",
        arguments=["list-units", "--type=service", "--all", "--no-pager", "--no-legend"],
        stdout="",
        stderr="systemd error",
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
    assert "Failed to execute systemctl list-units" in result.errors[0]
    assert result.payload == {}


@pytest.mark.asyncio
async def test_collect_parsing_failure(collector, mock_executor):
    """Verify collector logs parser errors when outputs are corrupted."""
    now = datetime.now(timezone.utc)

    hostname_res = CommandResult(
        command="hostname", arguments=[], stdout="host", stderr="", exit_code=0, execution_time_ms=1, timed_out=False, success=True, timestamp=now
    )

    garbage_res = CommandResult(
        command="systemctl",
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

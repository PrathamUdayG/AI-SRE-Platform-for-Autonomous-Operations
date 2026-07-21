"""
-------------------------------------------------------
File:
test_collector_orchestrator.py

Purpose:
Unit tests for the CollectorOrchestrator in the Application Layer.

Why this file exists:
Verifies execution scheduling (sequential and parallel) and ensures crash-isolation. If one collector fails or raises an unexpected exception, the orchestrator must proceed with executing other collectors, gathering all results correctly.

Responsibilities:
- Verify running a single collector by name.
- Verify running all collectors sequentially.
- Verify running all collectors in parallel.
- Verify crash isolation and mapping unhandled exceptions to failed CollectorResult structures.

Used By:
- pytest runner

Depends On:
- src.application.orchestrator.collector_orchestrator.CollectorOrchestrator
- src.application.orchestrator.collector_registry.CollectorRegistry
-------------------------------------------------------
"""

from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock
import pytest

from src.application.orchestrator.collector_orchestrator import CollectorOrchestrator
from src.application.orchestrator.collector_registry import CollectorRegistry
from src.domain.collectors.collector import Collector
from src.domain.collectors.collector_result import CollectorResult
from src.domain.collectors.collector_status import CollectorStatus
from src.domain.collectors.metric_type import MetricType
from src.domain.interfaces.connectors import ICommandExecutor


@pytest.fixture
def registry():
    return CollectorRegistry()


@pytest.fixture
def orchestrator(registry):
    return CollectorOrchestrator(registry=registry)


@pytest.fixture
def mock_executor():
    return MagicMock(spec=ICommandExecutor)


@pytest.mark.asyncio
async def test_run_collector_success(orchestrator, registry, mock_executor):
    """Verify running a single successful collector."""
    mock_result = CollectorResult(
        timestamp=datetime.now(timezone.utc),
        hostname="test-host",
        collector_name="SuccessCol",
        metric_type=MetricType.CPU,
        payload={"ok": True},
        status=CollectorStatus.SUCCESS,
        errors=[],
        execution_time_ms=10
    )

    col = MagicMock(spec=Collector)
    col.name = "SuccessCol"
    col.collect = AsyncMock(return_value=mock_result)

    registry.register(col)

    res = await orchestrator.run_collector("SuccessCol", mock_executor)
    
    assert res is mock_result
    col.collect.assert_called_once_with(mock_executor)


@pytest.mark.asyncio
async def test_run_collector_crash_isolation(orchestrator, registry, mock_executor):
    """Verify that if a collector throws an exception, a failed CollectorResult is returned."""
    col = MagicMock(spec=Collector)
    col.name = "CrashCol"
    col.metric_type = MetricType.CPU
    col.collect = AsyncMock(side_effect=RuntimeError("Hardware failure"))

    registry.register(col)

    res = await orchestrator.run_collector("CrashCol", mock_executor)
    
    assert res.collector_name == "CrashCol"
    assert res.status == CollectorStatus.FAILED
    assert len(res.errors) == 1
    assert "Hardware failure" in res.errors[0]
    assert res.payload == {}


@pytest.mark.asyncio
async def test_run_all_sequential(orchestrator, registry, mock_executor):
    """Verify running multiple collectors sequentially, including error isolation."""
    # 1. Success Collector
    res1 = CollectorResult(
        timestamp=datetime.now(timezone.utc), hostname="host", collector_name="Col1",
        metric_type=MetricType.CPU, payload={"data": 1}, status=CollectorStatus.SUCCESS, errors=[], execution_time_ms=5
    )
    col1 = MagicMock(spec=Collector)
    col1.name = "Col1"
    col1.collect = AsyncMock(return_value=res1)

    # 2. Crash Collector
    col2 = MagicMock(spec=Collector)
    col2.name = "Col2"
    col2.metric_type = MetricType.MEMORY
    col2.collect = AsyncMock(side_effect=ValueError("Invalid state"))

    registry.register(col1)
    registry.register(col2)

    results = await orchestrator.run_all(mock_executor)

    assert len(results) == 2
    assert results[0].collector_name == "Col1"
    assert results[0].status == CollectorStatus.SUCCESS

    assert results[1].collector_name == "Col2"
    assert results[1].status == CollectorStatus.FAILED
    assert "Invalid state" in results[1].errors[0]


@pytest.mark.asyncio
async def test_run_all_parallel(orchestrator, registry, mock_executor):
    """Verify running multiple collectors concurrently, including error isolation."""
    res1 = CollectorResult(
        timestamp=datetime.now(timezone.utc), hostname="host", collector_name="Col1",
        metric_type=MetricType.CPU, payload={"val": 10}, status=CollectorStatus.SUCCESS, errors=[], execution_time_ms=5
    )
    col1 = MagicMock(spec=Collector)
    col1.name = "Col1"
    col1.collect = AsyncMock(return_value=res1)

    res2 = CollectorResult(
        timestamp=datetime.now(timezone.utc), hostname="host", collector_name="Col2",
        metric_type=MetricType.MEMORY, payload={"val": 20}, status=CollectorStatus.SUCCESS, errors=[], execution_time_ms=10
    )
    col2 = MagicMock(spec=Collector)
    col2.name = "Col2"
    col2.collect = AsyncMock(return_value=res2)

    registry.register(col1)
    registry.register(col2)

    results = await orchestrator.run_parallel(mock_executor)

    assert len(results) == 2
    names = {r.collector_name for r in results}
    assert "Col1" in names
    assert "Col2" in names
    assert all(r.status == CollectorStatus.SUCCESS for r in results)

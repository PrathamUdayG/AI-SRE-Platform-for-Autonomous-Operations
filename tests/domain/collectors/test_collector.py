"""
-------------------------------------------------------
File:
test_collector.py

Purpose:
Tests for the Collector abstract base class in the Domain layer.

Why this file exists:
Verifies that concrete collector subclasses are forced to implement all required interface methods and properties.

Responsibilities:
- Verify ABC properties (name, metric_type) are enforced
- Verify collect method is enforced

Used By:
- pytest runner

Depends On:
- src.domain.collectors.collector
-------------------------------------------------------
"""

import pytest
from datetime import datetime, timezone
from src.domain.collectors.collector import Collector
from src.domain.collectors.collector_result import CollectorResult
from src.domain.collectors.collector_status import CollectorStatus
from src.domain.collectors.metric_type import MetricType
from src.domain.interfaces.connectors import ICommandExecutor


class DummyCollector(Collector):
    """A concrete dummy implementation of Collector for testing."""

    @property
    def name(self) -> str:
        return "Dummy"

    @property
    def metric_type(self) -> str:
        return MetricType.CPU

    async def collect(self, executor: ICommandExecutor) -> CollectorResult:
        return CollectorResult(
            timestamp=datetime.now(timezone.utc),
            hostname="dummy-host",
            collector_name=self.name,
            metric_type=self.metric_type,
            payload={"dummy": True},
            status=CollectorStatus.SUCCESS,
            errors=[],
            execution_time_ms=1
        )


@pytest.mark.asyncio
async def test_collector_interface_enforcement():
    """Verify that a class inheriting from Collector must implement name, metric_type, and collect."""
    
    # Try instantiating class with missing implementations
    class IncompleteCollector(Collector):
        pass

    with pytest.raises(TypeError):
        IncompleteCollector()  # type: ignore


@pytest.mark.asyncio
async def test_dummy_collector_execution():
    """Verify that a complete subclass of Collector can be instantiated and executed."""
    class MockExecutor(ICommandExecutor):
        async def execute(self, command: str, timeout=None) -> str:
            return "mock"

    collector = DummyCollector()
    assert collector.name == "Dummy"
    assert collector.metric_type == MetricType.CPU

    mock_executor = MockExecutor()
    result = await collector.collect(mock_executor)
    
    assert isinstance(result, CollectorResult)
    assert result.collector_name == "Dummy"
    assert result.payload == {"dummy": True}
    assert result.status == CollectorStatus.SUCCESS

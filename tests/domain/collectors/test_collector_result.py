"""
-------------------------------------------------------
File:
test_collector_result.py

Purpose:
Tests for the CollectorResult data model in the Domain layer.

Why this file exists:
Ensures that the schema returned by all collectors can be validated, serialized, and handled correctly under different scenarios (valid data, missing data, and serialization to JSON).

Responsibilities:
- Verify Pydantic validation on valid inputs
- Verify validation failure on missing fields
- Verify serialization output matches requirements

Used By:
- pytest runner

Depends On:
- src.domain.collectors.collector_result
-------------------------------------------------------
"""

from datetime import datetime, timezone
import pytest
from pydantic import ValidationError

from src.domain.collectors.collector_result import CollectorResult
from src.domain.collectors.collector_status import CollectorStatus
from src.domain.collectors.metric_type import MetricType


def test_collector_result_valid():
    """Verify that a valid CollectorResult instantiates correctly and preserves types."""
    now = datetime.now(timezone.utc)
    payload = {"usage_percent": 45.5, "cores": 4}
    
    result = CollectorResult(
        timestamp=now,
        hostname="test-host-01",
        collector_name="CPUCollector",
        metric_type=MetricType.CPU,
        payload=payload,
        status=CollectorStatus.SUCCESS,
        errors=[],
        execution_time_ms=12
    )

    assert result.timestamp == now
    assert result.hostname == "test-host-01"
    assert result.collector_name == "CPUCollector"
    assert result.metric_type == MetricType.CPU
    assert result.payload == payload
    assert result.status == CollectorStatus.SUCCESS
    assert result.errors == []
    assert result.execution_time_ms == 12


def test_collector_result_serialization():
    """Verify that CollectorResult serializes to dict and JSON correctly."""
    now = datetime(2026, 7, 21, 12, 0, 0, tzinfo=timezone.utc)
    result = CollectorResult(
        timestamp=now,
        hostname="test-host-01",
        collector_name="CPUCollector",
        metric_type=MetricType.CPU,
        payload={"usage": 10},
        status=CollectorStatus.SUCCESS,
        errors=[],
        execution_time_ms=5
    )

    serialized = result.model_dump()
    assert serialized["hostname"] == "test-host-01"
    assert serialized["metric_type"] == "CPU"
    assert serialized["status"] == "SUCCESS"

    json_str = result.model_dump_json()
    assert '"hostname":"test-host-01"' in json_str
    assert '"metric_type":"CPU"' in json_str
    assert '"status":"SUCCESS"' in json_str


def test_collector_result_validation_error():
    """Verify that missing required fields raises a Pydantic ValidationError."""
    with pytest.raises(ValidationError):
        # Missing required execution_time_ms and status
        CollectorResult(
            timestamp=datetime.now(timezone.utc),
            hostname="test-host-01",
            collector_name="CPUCollector",
            metric_type=MetricType.CPU,
            payload={}
        )

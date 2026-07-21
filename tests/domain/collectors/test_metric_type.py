"""
-------------------------------------------------------
File:
test_metric_type.py

Purpose:
Tests for the MetricType enum in the Domain layer.

Why this file exists:
Verifies that all supported metric types (CPU, MEMORY, DISK, etc.) are correctly defined, serializable, and have expected string representations.

Responsibilities:
- Verify defined enum values
- Verify enum string conversion

Used By:
- pytest runner

Depends On:
- src.domain.collectors.metric_type
-------------------------------------------------------
"""

import pytest
from src.domain.collectors.metric_type import MetricType


def test_metric_type_values():
    """Verify that all required metric types exist and map to correct values."""
    assert MetricType.CPU == "CPU"
    assert MetricType.MEMORY == "MEMORY"
    assert MetricType.DISK == "DISK"
    assert MetricType.NETWORK == "NETWORK"
    assert MetricType.PROCESS == "PROCESS"
    assert MetricType.SERVICE == "SERVICE"
    assert MetricType.LOG == "LOG"
    assert MetricType.DOCKER == "DOCKER"
    assert MetricType.KUBERNETES == "KUBERNETES"
    assert MetricType.SYSTEM == "SYSTEM"


def test_metric_type_iteration():
    """Verify all enums can be iterated and have string values."""
    enum_list = list(MetricType)
    assert len(enum_list) == 10
    for m in enum_list:
        assert isinstance(m, str)


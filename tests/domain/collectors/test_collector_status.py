"""
-------------------------------------------------------
File:
test_collector_status.py

Purpose:
Tests for the CollectorStatus enum in the Domain layer.

Why this file exists:
Verifies that all supported collector status outcomes (SUCCESS, FAILED, etc.) are correctly defined and have expected string representations.

Responsibilities:
- Verify defined status enum values

Used By:
- pytest runner

Depends On:
- src.domain.collectors.collector_status
-------------------------------------------------------
"""

import pytest
from src.domain.collectors.collector_status import CollectorStatus


def test_collector_status_values():
    """Verify that all required collector status values exist and map to correct values."""
    assert CollectorStatus.SUCCESS == "SUCCESS"
    assert CollectorStatus.FAILED == "FAILED"
    assert CollectorStatus.UNAVAILABLE == "UNAVAILABLE"
    assert CollectorStatus.PARTIAL == "PARTIAL"


def test_collector_status_iteration():
    """Verify all enums can be iterated and have string values."""
    enum_list = list(CollectorStatus)
    assert len(enum_list) == 4
    for s in enum_list:
        assert isinstance(s, str)

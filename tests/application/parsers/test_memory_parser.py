"""
-------------------------------------------------------
File:
test_memory_parser.py

Purpose:
Unit tests for the MemoryParser in the Application Layer.

Why this file exists:
Verifies that raw /proc/meminfo text strings are parsed correctly, invalid integers are handled safely, missing fields fall back to default values, and malformed strings raise validation exceptions.

Responsibilities:
- Verify standard parsing outputs.
- Verify handling of missing keys.
- Verify handling of non-integer tokens.
- Verify validation failures on empty outputs.

Used By:
- pytest runner

Depends On:
- src.application.parsers.memory_parser
- src.domain.exceptions.ValidationError
-------------------------------------------------------
"""

from datetime import datetime, timezone
import pytest

from src.application.parsers.memory_parser import MemoryParser
from src.domain.exceptions import ValidationError


def test_parse_normal_meminfo():
    """Verify that a valid /proc/meminfo output parses successfully into MemoryMetrics."""
    raw_data = """
    MemTotal:       16388432 kB
    MemFree:         4321098 kB
    MemAvailable:   10098432 kB
    Buffers:          123456 kB
    Cached:          5432109 kB
    SwapTotal:       2097152 kB
    SwapFree:        1048576 kB
    Dirty:               128 kB
    """
    now = datetime.now(timezone.utc)
    metrics = MemoryParser.parse(raw_data, now)

    assert metrics.total_memory_kb == 16388432
    assert metrics.free_memory_kb == 4321098
    assert metrics.available_memory_kb == 10098432
    assert metrics.buffers_kb == 123456
    assert metrics.cached_kb == 5432109
    assert metrics.swap_total_kb == 2097152
    assert metrics.swap_free_kb == 1048576
    assert metrics.dirty_kb == 128
    assert metrics.timestamp == now


def test_parse_missing_fields_defaults_to_zero():
    """Verify that missing fields default to 0 and do not cause parsing to fail."""
    raw_data = """
    MemTotal:       16388432 kB
    MemFree:         4321098 kB
    """
    now = datetime.now(timezone.utc)
    metrics = MemoryParser.parse(raw_data, now)

    assert metrics.total_memory_kb == 16388432
    assert metrics.free_memory_kb == 4321098
    assert metrics.available_memory_kb == 0  # Missing, should default to 0
    assert metrics.buffers_kb == 0
    assert metrics.cached_kb == 0


def test_parse_invalid_values_are_ignored():
    """Verify that non-numeric values are safely skipped or ignored."""
    raw_data = """
    MemTotal:       invalid_number kB
    MemFree:         4321098 kB
    """
    now = datetime.now(timezone.utc)
    metrics = MemoryParser.parse(raw_data, now)

    assert metrics.total_memory_kb == 0  # Invalid, defaults to 0
    assert metrics.free_memory_kb == 4321098


def test_parse_empty_input_raises_validation_error():
    """Verify that empty inputs raise a ValidationError."""
    now = datetime.now(timezone.utc)
    
    with pytest.raises(ValidationError) as excinfo:
        MemoryParser.parse("", now)
    assert "empty or whitespace" in str(excinfo.value)

    with pytest.raises(ValidationError):
        MemoryParser.parse("   \n   ", now)


def test_parse_completely_malformed_input_raises_validation_error():
    """Verify that inputs with no valid key-value pairs raise a ValidationError."""
    now = datetime.now(timezone.utc)
    raw_data = "some random text with no colons or metrics"

    with pytest.raises(ValidationError) as excinfo:
        MemoryParser.parse(raw_data, now)
    assert "Could not parse any valid key-value pairs" in str(excinfo.value)

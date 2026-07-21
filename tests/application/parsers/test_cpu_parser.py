"""
-------------------------------------------------------
File:
test_cpu_parser.py

Purpose:
Unit tests for the CPUParser in the Application Layer.

Why this file exists:
Verifies that CPU ticks and load averages are parsed accurately, and edge cases such as missing files, invalid integers, or empty files raise ValidationError.

Responsibilities:
- Verify standard parsing outputs.
- Verify core counting logic.
- Verify missing optional tokens.
- Verify empty inputs.
- Verify malformed columns.

Used By:
- pytest runner

Depends On:
- src.application.parsers.cpu_parser
- src.domain.exceptions.ValidationError
-------------------------------------------------------
"""

from datetime import datetime, timezone
import pytest

from src.application.parsers.cpu_parser import CPUParser
from src.domain.exceptions import ValidationError


def test_parse_normal_cpu_info():
    """Verify that valid /proc/stat and /proc/loadavg outputs parse successfully."""
    stat_data = """
    cpu  2255 34 2290 22625563 6290 127 456 0 0 0
    cpu0 1127 17 1145 11312781 3145 63 228 0 0 0
    cpu1 1128 17 1145 11312782 3145 64 228 0 0 0
    intr 314528 10 0 0 2
    """
    load_data = "0.20 0.18 0.12 1/450 12345"
    now = datetime.now(timezone.utc)

    metrics = CPUParser.parse(stat_data, load_data, now)

    assert metrics.user_ticks == 2255
    assert metrics.system_ticks == 2290
    assert metrics.idle_ticks == 22625563
    assert metrics.iowait_ticks == 6290
    assert metrics.irq_ticks == 127
    assert metrics.softirq_ticks == 456
    assert metrics.steal_ticks == 0
    assert metrics.guest_ticks == 0
    assert metrics.logical_cpu_count == 2
    assert metrics.load_average_1m == 0.20
    assert metrics.load_average_5m == 0.18
    assert metrics.load_average_15m == 0.12
    assert metrics.timestamp == now


def test_parse_defaults_logical_cpu_when_missing():
    """Verify logical CPU count defaults to at least 1 if no CPU core sublines are found."""
    stat_data = "cpu  2255 34 2290 22625563 6290 127 456 0 0 0"
    load_data = "0.10 0.05 0.01 1/150 5432"
    now = datetime.now(timezone.utc)

    metrics = CPUParser.parse(stat_data, load_data, now)
    assert metrics.logical_cpu_count == 1


def test_parse_invalid_integers_fallbacks():
    """Verify non-numeric ticks fall back to 0 without throwing an exception."""
    stat_data = "cpu  invalid_tick 34 2290 22625563 6290 127 456 0 0 0"
    load_data = "0.20 0.18 0.12 1/450 12345"
    now = datetime.now(timezone.utc)

    metrics = CPUParser.parse(stat_data, load_data, now)
    assert metrics.user_ticks == 0
    assert metrics.system_ticks == 2290


def test_parse_empty_input_raises_validation_error():
    """Verify empty inputs raise ValidationError."""
    now = datetime.now(timezone.utc)

    with pytest.raises(ValidationError):
        CPUParser.parse("", "0.10 0.05 0.01", now)

    with pytest.raises(ValidationError):
        CPUParser.parse("cpu  123 456", "", now)


def test_parse_malformed_columns_raises_validation_error():
    """Verify malformed stats or loadavg values raise ValidationError."""
    now = datetime.now(timezone.utc)

    # Missing CPU columns (less than 9)
    with pytest.raises(ValidationError) as exc:
        CPUParser.parse("cpu  123 456", "0.10 0.05 0.01", now)
    assert "Unexpected CPU aggregate line column count" in str(exc.value)

    # Missing load avg columns (less than 3)
    with pytest.raises(ValidationError) as exc:
        CPUParser.parse("cpu  2255 34 2290 22625563 6290 127 456 0 0 0", "0.10", now)
    assert "Unexpected column count in /proc/loadavg" in str(exc.value)

"""
-------------------------------------------------------
File:
test_command_result.py

Purpose:
Tests for the CommandResult data model in the Domain Layer.

Why this file exists:
Verifies that the structured output returned from command executions satisfies Pydantic validation constraints and serialization requirements.

Responsibilities:
- Verify instantiation with valid data.
- Verify validation failures for missing values.
- Verify JSON serialization matches expected schema.

Used By:
- pytest runner

Depends On:
- src.domain.executor.command_result
-------------------------------------------------------
"""

from datetime import datetime, timezone
import pytest
from pydantic import ValidationError
from src.domain.executor.command_result import CommandResult


def test_command_result_valid_instantiation():
    """Verify that a valid CommandResult instantiates correctly."""
    now = datetime.now(timezone.utc)
    result = CommandResult(
        command="df",
        arguments=["-h"],
        stdout="/dev/sda1  40G  20G  20G  50% /",
        stderr="",
        exit_code=0,
        execution_time_ms=15,
        timed_out=False,
        success=True,
        timestamp=now
    )

    assert result.command == "df"
    assert result.arguments == ["-h"]
    assert result.stdout == "/dev/sda1  40G  20G  20G  50% /"
    assert result.stderr == ""
    assert result.exit_code == 0
    assert result.execution_time_ms == 15
    assert not result.timed_out
    assert result.success
    assert result.timestamp == now


def test_command_result_missing_fields_validation():
    """Verify validation error raises on missing fields."""
    with pytest.raises(ValidationError):
        CommandResult(
            command="df",
            stdout="some output"
            # Missing exit_code, success, timestamp, etc.
        )


def test_command_result_serialization():
    """Verify serialization to dictionary and JSON formats."""
    now = datetime(2026, 7, 21, 12, 0, 0, tzinfo=timezone.utc)
    result = CommandResult(
        command="uptime",
        arguments=[],
        stdout="12:00:00 up 10 days",
        stderr="",
        exit_code=0,
        execution_time_ms=5,
        timed_out=False,
        success=True,
        timestamp=now
    )

    serialized = result.model_dump()
    assert serialized["command"] == "uptime"
    assert serialized["exit_code"] == 0
    assert serialized["success"] is True

    json_str = result.model_dump_json()
    assert '"command":"uptime"' in json_str
    assert '"exit_code":0' in json_str

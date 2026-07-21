"""
-------------------------------------------------------
File:
test_service_parser.py

Purpose:
Unit tests for the ServiceParser in the Application Layer.

Why this file exists:
Verifies that systemctl list-units output and show details are correctly parsed and enriched.

Responsibilities:
- Verify standard parsing outputs.
- Verify missing show parameters default to None/False.
- Verify ValidationError triggers when no units are matched.

Used By:
- pytest runner

Depends On:
- src.application.parsers.service_parser
- src.domain.exceptions.ValidationError
-------------------------------------------------------
"""

from datetime import datetime, timezone
import pytest

from src.application.parsers.service_parser import ServiceParser
from src.domain.exceptions import ValidationError


def test_parse_normal_services():
    """Verify systemctl list-units and show output parsing succeeds."""
    list_units = """
    cron.service          loaded active running Regular background program processing daemon
    docker.service        loaded active running Docker Application Container Engine
    non-service.device    loaded active plugged Non-service unit type
    """

    show_data = """
Id=cron.service
Description=Regular background program processing daemon
LoadState=loaded
ActiveState=active
SubState=running
UnitFileState=enabled
MainPID=1200
Type=simple
Restart=on-failure
FragmentPath=/lib/systemd/system/cron.service

Id=docker.service
Description=Docker Application Container Engine
LoadState=loaded
ActiveState=active
SubState=running
UnitFileState=enabled
MainPID=1450
Type=notify
Restart=always
FragmentPath=/lib/systemd/system/docker.service
    """
    now = datetime.now(timezone.utc)

    metrics = ServiceParser.parse(list_units, show_data, now)

    assert len(metrics.services) == 2

    s1 = metrics.services[0]
    assert s1.name == "cron.service"
    assert s1.description == "Regular background program processing daemon"
    assert s1.load_state == "loaded"
    assert s1.active_state == "active"
    assert s1.sub_state == "running"
    assert s1.unit_file_state == "enabled"
    assert s1.main_pid == 1200
    assert s1.service_type == "simple"
    assert s1.restart_policy == "on-failure"
    assert s1.fragment_path == "/lib/systemd/system/cron.service"
    assert s1.is_enabled is True

    s2 = metrics.services[1]
    assert s2.name == "docker.service"
    assert s2.main_pid == 1450
    assert s2.service_type == "notify"
    assert s2.restart_policy == "always"
    assert s2.is_enabled is True


def test_parse_missing_show_data_defaults():
    """Verify that absent show details result in default or None values."""
    list_units = "cron.service          loaded active running cron daemon"
    now = datetime.now(timezone.utc)

    metrics = ServiceParser.parse(list_units, None, now)

    assert len(metrics.services) == 1
    s = metrics.services[0]
    assert s.name == "cron.service"
    assert s.unit_file_state is None
    assert s.main_pid is None
    assert s.service_type is None
    assert s.restart_policy is None
    assert s.is_enabled is False


def test_parse_empty_input_raises_validation_error():
    """Verify that completely empty inputs raise ValidationError."""
    now = datetime.now(timezone.utc)
    with pytest.raises(ValidationError):
        ServiceParser.parse("", None, now)

    with pytest.raises(ValidationError):
        ServiceParser.parse(None, None, now)

"""
-------------------------------------------------------
File:
test_log_parser.py

Purpose:
Unit tests for the LogParser in the Application Layer.

Why this file exists:
Verifies that various Linux log formats (journalctl, syslog, messages) are correctly parsed and normalized.

Responsibilities:
- Verify parsing of journalctl short-iso format lines.
- Verify parsing of standard RFC3164 Syslog lines.
- Verify parsing of lines without explicit process name or PID.
- Verify robust handling of timestamp formats (ISO, RFC3164).
- Verify normalization of severity and facility (none / un-inferred).

Used By:
- pytest runner

Depends On:
- src.application.parsers.log_parser
-------------------------------------------------------
"""

from datetime import datetime, timezone
import pytest

from src.application.parsers.log_parser import LogParser


def test_parse_journalctl_short_iso():
    """Verify parsing journalctl short-iso log lines works."""
    line = "2026-07-21T14:29:48+0530 hostname process[1234]: The log message contents"
    entry = LogParser.parse_line(line, source_file="journalctl", source_type="journalctl")
    
    assert entry is not None
    assert entry.timestamp.hour == 14
    assert entry.timestamp.minute == 29
    assert entry.hostname == "hostname"
    assert entry.process_name == "process"
    assert entry.pid == 1234
    assert entry.message == "The log message contents"
    assert entry.source_file == "journalctl"
    assert entry.source_type == "journalctl"
    assert entry.severity is None
    assert entry.facility is None


def test_parse_syslog_rfc3164():
    """Verify parsing RFC3164 standard syslog lines works."""
    line = "Jul 21 08:54:31 my-host systemd[1]: Started System Logging Service."
    entry = LogParser.parse_line(line, source_file="/var/log/syslog", source_type="syslog")
    
    assert entry is not None
    assert entry.timestamp.month == 7
    assert entry.timestamp.day == 21
    assert entry.hostname == "my-host"
    assert entry.process_name == "systemd"
    assert entry.pid == 1
    assert entry.message == "Started System Logging Service."
    assert entry.source_file == "/var/log/syslog"
    assert entry.source_type == "syslog"


def test_parse_no_process_or_pid():
    """Verify parsing lines without process info or PID works."""
    line1 = "2026-07-21T14:29:48Z my-host: Message without process"
    entry1 = LogParser.parse_line(line1, source_file="/var/log/messages", source_type="messages")
    
    assert entry1 is not None
    assert entry1.hostname == "my-host"
    assert entry1.process_name == "unknown"
    assert entry1.pid is None
    assert entry1.message == "Message without process"

    line2 = "Jul 21 08:54:31 my-host: Message without process in syslog"
    entry2 = LogParser.parse_line(line2, source_file="/var/log/syslog", source_type="syslog")
    
    assert entry2 is not None
    assert entry2.hostname == "my-host"
    assert entry2.process_name == "unknown"
    assert entry2.pid is None
    assert entry2.message == "Message without process in syslog"


def test_parse_multi_source():
    """Verify parsing multiple sources combining in LogMetrics."""
    journalctl_output = "2026-07-21T14:29:48Z host1 procA[11]: msgA\n"
    syslog_output = "Jul 21 08:54:31 host2 procB[22]: msgB\n"
    messages_output = "Jul 21 08:54:31 host3 procC[33]: msgC\n"
    
    now = datetime.now(timezone.utc)
    metrics = LogParser.parse(
        journalctl_output=journalctl_output,
        syslog_output=syslog_output,
        messages_output=messages_output,
        timestamp=now
    )
    
    assert len(metrics.entries) == 3
    assert metrics.entries[0].process_name == "procA"
    assert metrics.entries[1].process_name == "procB"
    assert metrics.entries[2].process_name == "procC"
    assert metrics.timestamp == now

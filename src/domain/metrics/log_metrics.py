"""
-------------------------------------------------------
File:
log_metrics.py

Purpose:
Domain model representing normalized system log events.

Why this file exists:
Provides a strongly typed, OS-agnostic representation of host OS logs from journalctl, syslog, and messages.

Responsibilities:
- Encapsulate log event metadata: timestamp, process name, PID, severity, facility, and message text.

Used By:
- LogParser
- LogCollector

Notes:
This file belongs to the Domain Layer as it defines a core telemetry data structure.
-------------------------------------------------------
"""

from datetime import datetime
from typing import List, Optional
from pydantic import BaseModel, Field


class LogEntry(BaseModel):
    """
    Why this class exists:
    Encapsulates normalized attributes of a single system log event.
    """

    timestamp: datetime = Field(description="Log event timestamp")
    hostname: str = Field(description="Host identifier")
    process_name: str = Field(description="Name of emitting process")
    pid: Optional[int] = Field(None, description="Process identifier")
    severity: Optional[str] = Field(None, description="Log event severity level")
    facility: Optional[str] = Field(None, description="Syslog facility classification")
    message: str = Field(description="Raw log event message text")
    source_file: str = Field(description="Name/path of the source log file")
    source_type: str = Field(description="Source type (journalctl, syslog, messages)")


class LogMetrics(BaseModel):
    """
    Why this class exists:
    Main container model for all collected log entries.
    """

    entries: List[LogEntry] = Field(
        default_factory=list, description="List of normalized log entries"
    )
    timestamp: datetime = Field(description="UTC timestamp of when the metrics were captured")

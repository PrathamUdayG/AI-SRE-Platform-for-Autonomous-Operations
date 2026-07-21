"""
-------------------------------------------------------
File:
log_parser.py

Purpose:
Parses Linux log formats into normalized domain models.

Why this file exists:
Decouples log string parsing (regex/token splitting, ISO 8601 parsing, RFC3164 Syslog parsing) from log collector execution.

Responsibilities:
- Parse journalctl (short-iso output format) lines.
- Parse syslog (RFC3164 or ISO format) files.
- Parse messages files.
- Handle malformed lines defensively (skipping or extracting partial data).
- Map to normalized LogEntry domain objects.

Used By:
- LogCollector

Depends On:
- src.domain.metrics.log_metrics.LogEntry
- src.domain.metrics.log_metrics.LogMetrics
-------------------------------------------------------
"""

from datetime import datetime, timezone
from typing import List, Optional
import structlog

from src.domain.metrics.log_metrics import LogEntry, LogMetrics

logger = structlog.get_logger(__name__)

MONTHS = {
    "jan",
    "feb",
    "mar",
    "apr",
    "may",
    "jun",
    "jul",
    "aug",
    "sep",
    "oct",
    "nov",
    "dec",
}


class LogParser:
    """
    Why this class exists:
    A utility class containing static methods for parsing host logs.

    Responsibility:
    Converts raw CLI/file logs to structured LogMetrics.

    Who uses it:
    LogCollector.
    """

    @classmethod
    def parse_line(
        cls, line: str, source_file: str, source_type: str
    ) -> Optional[LogEntry]:
        """
        Parses a single log line defensively and maps it to a LogEntry.

        Args:
            line (str): Raw string line from a log source.
            source_file (str): The filename/source where this log originated.
            source_type (str): Type classification (journalctl, syslog, messages).

        Returns:
            Optional[LogEntry]: Stably parsed LogEntry or None if parsing is impossible.
        """
        line = line.strip()
        if not line:
            return None

        parts = line.split()
        if len(parts) < 2:
            return None

        # Determine log layout pattern
        is_syslog = False
        if parts[0].lower().rstrip(":") in MONTHS:
            is_syslog = True

        try:
            if is_syslog:
                if len(parts) < 4:
                    return None
                ts_str = " ".join(parts[0:3])
                if parts[3].endswith(":"):
                    hostname = parts[3].rstrip(":")
                    proc_token = "unknown"
                    prefix_end = line.find(parts[3]) + len(parts[3])
                    message = line[prefix_end:].strip()
                else:
                    hostname = parts[3]
                    proc_token = parts[4] if len(parts) > 4 else "unknown"
                    if len(parts) > 4:
                        prefix_end = line.find(parts[4]) + len(parts[4])
                        message = line[prefix_end:].lstrip(":").strip()
                    else:
                        message = ""
            else:
                # ISO Format / journalctl
                ts_str = parts[0]
                if parts[1].endswith(":"):
                    hostname = parts[1].rstrip(":")
                    proc_token = "unknown"
                    prefix_end = line.find(parts[1]) + len(parts[1])
                    message = line[prefix_end:].strip()
                else:
                    hostname = parts[1]
                    proc_token = parts[2] if len(parts) > 2 else "unknown"
                    if len(parts) > 2:
                        prefix_end = line.find(parts[2]) + len(parts[2])
                        message = line[prefix_end:].lstrip(":").strip()
                    else:
                        message = ""

            # Standardize process name and PID
            proc_info = proc_token.rstrip(":")
            proc_name = proc_info
            pid = None

            if "[" in proc_info and proc_info.endswith("]"):
                try:
                    name_part, pid_part = proc_info.split("[", 1)
                    proc_name = name_part
                    pid = int(pid_part.rstrip("]"))
                except ValueError:
                    pass

            # Timestamp parsing
            ts_val = None
            if is_syslog:
                try:
                    current_year = datetime.now(timezone.utc).year
                    ts_val = datetime.strptime(
                        f"{current_year} {ts_str}", "%Y %b %d %H:%M:%S"
                    )
                    ts_val = ts_val.replace(tzinfo=timezone.utc)
                except ValueError:
                    pass
            else:
                try:
                    # fromisoformat handles +0000 or Z
                    ts_str_clean = ts_str.replace("Z", "+00:00")
                    # Handle formats like 2026-07-21T14:29:48+0530 (without colon in timezone offset)
                    if "+" in ts_str_clean and ":" not in ts_str_clean.split("+")[-1]:
                        tz_part = ts_str_clean.split("+")[-1]
                        if len(tz_part) == 4:
                            ts_str_clean = ts_str_clean[:-4] + tz_part[:2] + ":" + tz_part[2:]
                    elif "-" in ts_str_clean and ":" not in ts_str_clean.split("-")[-1] and "T" in ts_str_clean:
                        # Ensure we don't split the date part (which contains '-')
                        right_part = ts_str_clean.split("T")[-1]
                        if "-" in right_part:
                            tz_part = right_part.split("-")[-1]
                            if len(tz_part) == 4:
                                ts_str_clean = ts_str_clean[:-4] + tz_part[:2] + ":" + tz_part[2:]
                    ts_val = datetime.fromisoformat(ts_str_clean)
                except ValueError:
                    pass

            if not ts_val:
                ts_val = datetime.now(timezone.utc)

            # Severity and facility are left None as they are not explicitly exposed
            # by short-iso or raw syslog line headers. We do not infer.
            return LogEntry(
                timestamp=ts_val,
                hostname=hostname,
                process_name=proc_name,
                pid=pid,
                severity=None,
                facility=None,
                message=message,
                source_file=source_file,
                source_type=source_type,
            )

        except Exception as err:
            logger.debug("Failed parsing individual log line", error=str(err), line=line)
            return None

    @classmethod
    def parse(
        cls,
        journalctl_output: str,
        syslog_output: str,
        messages_output: str,
        timestamp: datetime,
    ) -> LogMetrics:
        """
        Parses all log outputs into unified LogMetrics.

        Args:
            journalctl_output (str): Stdout of journalctl command.
            syslog_output (str): Content/Stdout of /var/log/syslog.
            messages_output (str): Content/Stdout of /var/log/messages.
            timestamp (datetime): UTC capture timestamp.

        Returns:
            LogMetrics: Strongly typed list of unified LogEntry objects.
        """
        entries: List[LogEntry] = []

        # 1. Parse journalctl logs
        for line in journalctl_output.splitlines():
            entry = cls.parse_line(line, source_file="journalctl", source_type="journalctl")
            if entry:
                entries.append(entry)

        # 2. Parse syslog logs
        for line in syslog_output.splitlines():
            entry = cls.parse_line(line, source_file="/var/log/syslog", source_type="syslog")
            if entry:
                entries.append(entry)

        # 3. Parse messages logs
        for line in messages_output.splitlines():
            entry = cls.parse_line(line, source_file="/var/log/messages", source_type="messages")
            if entry:
                entries.append(entry)

        return LogMetrics(entries=entries, timestamp=timestamp)

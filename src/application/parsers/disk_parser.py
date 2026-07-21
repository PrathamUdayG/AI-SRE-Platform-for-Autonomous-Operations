"""
-------------------------------------------------------
File:
disk_parser.py

Purpose:
Parses Linux df filesystem and /proc/diskstats I/O text output.

Why this file exists:
Isolates complex string tokenization and multi-line parsing logic from the collector classes, ensuring DiskMetrics parsing is highly testable and robust.

Responsibilities:
- Parse df output using whitespace columns.
- Skip df header row by catching parsing conversions.
- Parse /proc/diskstats columns to extract low-level device counters.
- Validate values and return DiskMetrics model.

Used By:
- DiskCollector

Depends On:
- src.domain.metrics.disk_metrics.DiskMetrics
- src.domain.exceptions.ValidationError
-------------------------------------------------------
"""

from datetime import datetime
import structlog

from src.domain.exceptions import ValidationError
from src.domain.metrics.disk_metrics import DiskIOMetrics, DiskMetrics, FilesystemMetrics

logger = structlog.get_logger(__name__)


class DiskParser:
    """
    Why this class exists:
    A utility class containing static methods for parsing disk stats.

    Responsibility:
    Converts df output and /proc/diskstats lines into DiskMetrics.

    Who uses it:
    DiskCollector and diagnostic parsers.
    """

    @staticmethod
    def parse(
        df_output: str,
        proc_diskstats_output: str,
        timestamp: datetime
    ) -> DiskMetrics:
        """
        Parse df and diskstats outputs to create a DiskMetrics domain model.

        Args:
            df_output (str): Stdout string of df.
            proc_diskstats_output (str): Stdout string of /proc/diskstats.
            timestamp (datetime): UTC collection timestamp.

        Returns:
            DiskMetrics: Structured, type-validated disk metrics.

        Raises:
            ValidationError: If both inputs fail to yield any valid parsed items.
        """
        if df_output is None or proc_diskstats_output is None:
            raise ValidationError("Stdout inputs for df and diskstats cannot be None.")

        # 1. Parse df output
        filesystems = []
        for line in df_output.splitlines():
            line = line.strip()
            if not line:
                continue
            parts = line.split()
            if len(parts) < 7:
                continue

            try:
                # First two parts are string identifiers, next three are sizes
                total_bytes = int(parts[2])
                used_bytes = int(parts[3])
                available_bytes = int(parts[4])

                # Extract integer percentage, stripping '%' if present
                pcent_str = parts[5].rstrip("%")
                use_percent = int(pcent_str) if pcent_str.isdigit() else 0
                mount_point = " ".join(parts[6:])

                filesystems.append(
                    FilesystemMetrics(
                        filesystem=parts[0],
                        fstype=parts[1],
                        total_bytes=total_bytes,
                        used_bytes=used_bytes,
                        available_bytes=available_bytes,
                        use_percent=use_percent,
                        mount_point=mount_point,
                    )
                )
            except ValueError:
                # Skips header row or any corrupted lines
                continue

        # 2. Parse /proc/diskstats
        disk_io = []
        for line in proc_diskstats_output.splitlines():
            line = line.strip()
            if not line:
                continue
            parts = line.split()
            if len(parts) < 14:
                continue

            try:
                disk_io.append(
                    DiskIOMetrics(
                        major_number=int(parts[0]),
                        minor_number=int(parts[1]),
                        device_name=parts[2],
                        reads_completed=int(parts[3]),
                        reads_merged=int(parts[4]),
                        sectors_read=int(parts[5]),
                        read_time_ms=int(parts[6]),
                        writes_completed=int(parts[7]),
                        writes_merged=int(parts[8]),
                        sectors_written=int(parts[9]),
                        write_time_ms=int(parts[10]),
                        io_in_progress=int(parts[11]),
                        io_time_ms=int(parts[12]),
                        weighted_io_time_ms=int(parts[13]),
                    )
                )
            except ValueError:
                # Skip malformed controller counters
                continue

        # Check if both lists are empty (completely failed to parse)
        if not filesystems and not disk_io:
            raise ValidationError("Could not parse any filesystem mount or disk I/O metrics.")

        return DiskMetrics(
            filesystems=filesystems,
            disk_io=disk_io,
            timestamp=timestamp,
        )


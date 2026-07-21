"""
-------------------------------------------------------
File:
cpu_parser.py

Purpose:
Parses raw Linux CPU statistics from /proc/stat and /proc/loadavg.

Why this file exists:
Keeps string tokenization and text pattern-matching logic separate from the collector, ensuring CPU metrics parsing is independently mockable and testable.

Responsibilities:
- Parse CPU aggregate ticks from /proc/stat.
- Calculate CPU core counts by counting individual lines.
- Parse load averages from /proc/loadavg.
- Gracefully handle malformed or unexpected column count layouts.

Used By:
- CPUCollector

Depends On:
- src.domain.metrics.cpu_metrics.CPUMetrics
- src.domain.exceptions.ValidationError
-------------------------------------------------------
"""

from datetime import datetime
import re
import structlog

from src.domain.exceptions import ValidationError
from src.domain.metrics.cpu_metrics import CPUMetrics

logger = structlog.get_logger(__name__)


class CPUParser:
    """
    Why this class exists:
    A utility class containing static methods for parsing CPU logs.

    Responsibility:
    Converts proc outputs into strongly-typed CPUMetrics.

    Who uses it:
    CPUCollector.
    """

    @staticmethod
    def parse(
        proc_stat_output: str,
        proc_loadavg_output: str,
        timestamp: datetime
    ) -> CPUMetrics:
        """
        Parse outputs from '/proc/stat' and '/proc/loadavg' into a CPUMetrics model.

        Args:
            proc_stat_output (str): Raw string output of /proc/stat.
            proc_loadavg_output (str): Raw string output of /proc/loadavg.
            timestamp (datetime): UTC collection timestamp.

        Returns:
            CPUMetrics: Strongly-typed, validated CPU metrics.

        Raises:
            ValidationError: If required data is missing or completely malformed.
        """
        if not proc_stat_output or not proc_stat_output.strip():
            raise ValidationError("Raw /proc/stat output is empty or whitespace.")
        if not proc_loadavg_output or not proc_loadavg_output.strip():
            raise ValidationError("Raw /proc/loadavg output is empty or whitespace.")

        # 1. Parse /proc/stat ticks and count cores
        aggregate_line = None
        logical_cpu_count = 0

        for line in proc_stat_output.splitlines():
            line = line.strip()
            if not line:
                continue

            if line.startswith("cpu "):
                aggregate_line = line
            elif re.match(r"^cpu\d+", line):
                logical_cpu_count += 1

        if not aggregate_line:
            raise ValidationError("Could not find aggregate CPU ticks ('cpu ') line in /proc/stat.")

        tokens = aggregate_line.split()
        # tokens[0] is 'cpu'
        # tokens[1..] are: user, nice, system, idle, iowait, irq, softirq, steal, guest, guest_nice
        if len(tokens) < 9:
            raise ValidationError(f"Unexpected CPU aggregate line column count in /proc/stat: {aggregate_line}")

        def safe_int(token: str) -> int:
            try:
                return int(token)
            except ValueError:
                logger.debug("Failed to parse integer from CPU tick token", token=token)
                return 0

        user_ticks = safe_int(tokens[1])
        # nice is tokens[2]
        system_ticks = safe_int(tokens[3])
        idle_ticks = safe_int(tokens[4])
        iowait_ticks = safe_int(tokens[5])
        irq_ticks = safe_int(tokens[6])
        softirq_ticks = safe_int(tokens[7])
        steal_ticks = safe_int(tokens[8])
        
        # guest ticks are optional depending on older Linux kernels
        guest_ticks = safe_int(tokens[9]) if len(tokens) > 9 else 0

        # Default logical count to 1 if no sub-CPU lines were found
        if logical_cpu_count == 0:
            logical_cpu_count = 1

        # 2. Parse /proc/loadavg
        loadavg_tokens = proc_loadavg_output.strip().split()
        if len(loadavg_tokens) < 3:
            raise ValidationError(f"Unexpected column count in /proc/loadavg: {proc_loadavg_output}")

        try:
            load_average_1m = float(loadavg_tokens[0])
            load_average_5m = float(loadavg_tokens[1])
            load_average_15m = float(loadavg_tokens[2])
        except ValueError as e:
            raise ValidationError(f"Failed to parse float values from /proc/loadavg: {str(e)}")

        return CPUMetrics(
            user_ticks=user_ticks,
            system_ticks=system_ticks,
            idle_ticks=idle_ticks,
            iowait_ticks=iowait_ticks,
            irq_ticks=irq_ticks,
            softirq_ticks=softirq_ticks,
            steal_ticks=steal_ticks,
            guest_ticks=guest_ticks,
            load_average_1m=load_average_1m,
            load_average_5m=load_average_5m,
            load_average_15m=load_average_15m,
            logical_cpu_count=logical_cpu_count,
            timestamp=timestamp,
        )

"""
-------------------------------------------------------
File:
disk_collector.py

Purpose:
Infrastructure collector implementation for gathering Linux disk utilization and I/O metrics.

Why this file exists:
Implements the abstract Collector interface for disk storage telemetry. It executes safe commands to fetch partition table space and I/O scheduler operations, passing them to the parser.

Responsibilities:
- Implement the abstract Collector interface.
- Execute df and cat /proc/diskstats commands via the injected CommandExecutor.
- Invoke DiskParser to translate outputs to DiskMetrics.
- Return structured CollectorResult.

Used By:
- Telemetry Orchestrators
- Agent Runner

Depends On:
- src.domain.collectors.collector.Collector
- src.domain.collectors.collector_result.CollectorResult
- src.domain.collectors.collector_status.CollectorStatus
- src.domain.collectors.metric_type.MetricType
- src.domain.executor.command_executor.CommandExecutor
- src.application.parsers.disk_parser.DiskParser
-------------------------------------------------------
"""

from datetime import datetime, timezone
import time
from typing import Optional
import structlog

from src.application.parsers.disk_parser import DiskParser
from src.domain.collectors.collector import Collector
from src.domain.collectors.collector_result import CollectorResult
from src.domain.collectors.collector_status import CollectorStatus
from src.domain.collectors.metric_type import MetricType
from src.domain.executor.command_executor import CommandExecutor

logger = structlog.get_logger(__name__)


class DiskCollector(Collector):
    """
    Why this class exists:
    Gathers Linux system partition and block device stats inside the Infrastructure layer.

    Responsibility:
    Executes 'df -B1' and 'cat /proc/diskstats' read commands, passes outputs to DiskParser,
    and returns a structured CollectorResult.

    Who uses it:
    Orchestrators and agent run-loops.
    """

    def __init__(self, executor: CommandExecutor) -> None:
        """
        Initialize DiskCollector with a command executor.

        Args:
            executor (CommandExecutor): Executor used to run command pipelines.
        """
        self._executor = executor

    @property
    def name(self) -> str:
        """
        Return the collector name.

        Returns:
            str: Name of this collector.
        """
        return "DiskCollector"

    @property
    def metric_type(self) -> str:
        """
        Return the metric type name.

        Returns:
            str: Metric type classification.
        """
        return MetricType.DISK

    async def collect(self, executor: Optional[CommandExecutor] = None) -> CollectorResult:
        """
        Asynchronously collect disk metrics and return a standardized result.

        Args:
            executor (Optional[CommandExecutor]): Optional override for the executor.

        Returns:
            CollectorResult: The standardized collection result wrapper.
        """
        exec_to_use = executor or self._executor
        start_time = time.perf_counter()
        timestamp = datetime.now(timezone.utc)

        errors = []
        payload = {}
        status = CollectorStatus.SUCCESS

        # Resolve hostname
        hostname = "unknown"
        try:
            hostname_res = await exec_to_use.execute("hostname", [])
            if hostname_res.success:
                hostname = hostname_res.stdout.strip()
            else:
                logger.warning("Failed to resolve hostname via command", error=hostname_res.stderr)
        except Exception as host_err:
            logger.debug("Failed to resolve hostname", error=str(host_err))

        # Query disk space and I/O block counters
        try:
            # df returns bytes with block capacity -B1
            df_res = await exec_to_use.execute(
                "df",
                ["-B1", "--output=source,fstype,size,used,avail,pcent,target"],
            )
            # diskstats returns low level IO sectors
            stats_res = await exec_to_use.execute("cat", ["/proc/diskstats"])

            if not df_res.success:
                status = CollectorStatus.FAILED
                errors.append(f"Failed to execute df: {df_res.stderr}")
            elif not stats_res.success:
                status = CollectorStatus.FAILED
                errors.append(f"Failed to read /proc/diskstats: {stats_res.stderr}")
            else:
                try:
                    # Parse command outputs
                    metrics = DiskParser.parse(
                        df_output=df_res.stdout,
                        proc_diskstats_output=stats_res.stdout,
                        timestamp=timestamp,
                    )
                    payload = metrics.model_dump()
                except Exception as parse_err:
                    status = CollectorStatus.FAILED
                    errors.append(f"Parsing failed: {str(parse_err)}")

        except Exception as e:
            status = CollectorStatus.FAILED
            errors.append(f"Collector execution encountered unexpected error: {str(e)}")

        execution_time_ms = int((time.perf_counter() - start_time) * 1000)

        return CollectorResult(
            timestamp=timestamp,
            hostname=hostname,
            collector_name=self.name,
            metric_type=self.metric_type,
            payload=payload,
            status=status,
            errors=errors,
            execution_time_ms=execution_time_ms,
        )


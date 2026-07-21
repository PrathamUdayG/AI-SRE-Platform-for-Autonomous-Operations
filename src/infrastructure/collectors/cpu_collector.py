"""
-------------------------------------------------------
File:
cpu_collector.py

Purpose:
Infrastructure collector implementation for gathering Linux CPU metrics.

Why this file exists:
Implements the abstract Collector interface for CPU telemetry. It executes proc system reads and maps parsed outputs to structured CollectorResults.

Responsibilities:
- Implement the abstract Collector interface.
- Execute cat /proc/stat and cat /proc/loadavg via the injected CommandExecutor.
- Invoke CPUParser to translate outputs to CPUMetrics.
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
- src.application.parsers.cpu_parser.CPUParser
-------------------------------------------------------
"""

from datetime import datetime, timezone
import time
from typing import Optional
import structlog

from src.application.parsers.cpu_parser import CPUParser
from src.domain.collectors.collector import Collector
from src.domain.collectors.collector_result import CollectorResult
from src.domain.collectors.collector_status import CollectorStatus
from src.domain.collectors.metric_type import MetricType
from src.domain.executor.command_executor import CommandExecutor

logger = structlog.get_logger(__name__)


class CPUCollector(Collector):
    """
    Why this class exists:
    Gathers Linux CPU telemetry inside the Infrastructure layer.

    Responsibility:
    Executes 'cat /proc/stat', 'cat /proc/loadavg', and 'hostname' calls,
    invokes the parser, and returns structured CollectorResults.

    Who uses it:
    Orchestration engines and agent schedules.
    """

    def __init__(self, executor: CommandExecutor) -> None:
        """
        Initialize CPUCollector with a command executor.

        Args:
            executor (CommandExecutor): Executor used to execute commands.
        """
        self._executor = executor

    @property
    def name(self) -> str:
        """
        Return collector name.

        Returns:
            str: Name of this collector.
        """
        return "CPUCollector"

    @property
    def metric_type(self) -> str:
        """
        Return metric type name.

        Returns:
            str: Metric type classification.
        """
        return MetricType.CPU

    async def collect(self, executor: Optional[CommandExecutor] = None) -> CollectorResult:
        """
        Asynchronously collect CPU metrics and return a standardized result.

        Args:
            executor (Optional[CommandExecutor]): Optional override for the executor.

        Returns:
            CollectorResult: Standardized collection result wrapper.
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

        # Query /proc/stat and /proc/loadavg
        try:
            stat_res = await exec_to_use.execute("cat", ["/proc/stat"])
            loadavg_res = await exec_to_use.execute("cat", ["/proc/loadavg"])

            if not stat_res.success:
                status = CollectorStatus.FAILED
                errors.append(f"Failed to read /proc/stat: {stat_res.stderr}")
            elif not loadavg_res.success:
                status = CollectorStatus.FAILED
                errors.append(f"Failed to read /proc/loadavg: {loadavg_res.stderr}")
            else:
                try:
                    # Parse both command outputs together
                    metrics = CPUParser.parse(
                        proc_stat_output=stat_res.stdout,
                        proc_loadavg_output=loadavg_res.stdout,
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

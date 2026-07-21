"""
-------------------------------------------------------
File:
memory_collector.py

Purpose:
Infrastructure collector implementation for gathering Linux memory metrics.

Why this file exists:
Implements the abstract Collector interface for memory telemetry. It coordinates command execution and calls the parser to convert raw shell data into structured CollectorResults.

Responsibilities:
- Implement the abstract Collector interface.
- Execute cat /proc/meminfo safely using CommandExecutor.
- Invoke MemoryParser to translate output to MemoryMetrics.
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
- src.application.parsers.memory_parser.MemoryParser
-------------------------------------------------------
"""

from datetime import datetime, timezone
import time
from typing import Optional
import structlog

from src.application.parsers.memory_parser import MemoryParser
from src.domain.collectors.collector import Collector
from src.domain.collectors.collector_result import CollectorResult
from src.domain.collectors.collector_status import CollectorStatus
from src.domain.collectors.metric_type import MetricType
from src.domain.executor.command_executor import CommandExecutor

logger = structlog.get_logger(__name__)


class MemoryCollector(Collector):
    """
    Why this class exists:
    Gathers Linux system memory metrics inside the Infrastructure layer.

    Responsibility:
    Executes 'cat /proc/meminfo' and 'hostname' queries, invokes the parser,
    and returns a structured CollectorResult with nested MemoryMetrics.

    Who uses it:
    Orchestration engines and host health monitors.
    """

    def __init__(self, executor: CommandExecutor) -> None:
        """
        Initialize MemoryCollector with a command executor.

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
        return "MemoryCollector"

    @property
    def metric_type(self) -> str:
        """
        Return the metric type name.

        Returns:
            str: Metric type classification.
        """
        return MetricType.MEMORY

    async def collect(self, executor: Optional[CommandExecutor] = None) -> CollectorResult:
        """
        Asynchronously collect memory metrics and return a standardized result.

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

        # Query /proc/meminfo
        try:
            cmd_result = await exec_to_use.execute("cat", ["/proc/meminfo"])

            if not cmd_result.success:
                status = CollectorStatus.FAILED
                errors.append(f"Command execution failed: {cmd_result.stderr}")
            else:
                try:
                    # Parse the command output
                    metrics = MemoryParser.parse(cmd_result.stdout, timestamp)
                    # Convert Pydantic model directly to dictionary payload
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

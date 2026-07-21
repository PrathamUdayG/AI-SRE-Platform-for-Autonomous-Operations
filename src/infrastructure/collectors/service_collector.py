"""
-------------------------------------------------------
File:
service_collector.py

Purpose:
Infrastructure collector implementation for gathering Linux service state telemetry.

Why this file exists:
Implements the abstract Collector interface to execute systemctl queries for managing and listing services, returning them structured through ServiceParser.

Responsibilities:
- Implement the abstract Collector interface.
- Execute systemctl list-units --type=service to grab initial list.
- Execute systemctl show with service arguments to fetch detailed metadata.
- Handle exceptions and map into CollectorResult.

Used By:
- Telemetry Orchestrators
- Agent Runner

Depends On:
- src.domain.collectors.collector.Collector
- src.domain.collectors.collector_result.CollectorResult
- src.domain.collectors.collector_status.CollectorStatus
- src.domain.collectors.metric_type.MetricType
- src.domain.executor.command_executor.CommandExecutor
- src.application.parsers.service_parser.ServiceParser
-------------------------------------------------------
"""

from datetime import datetime, timezone
import time
from typing import Optional
import structlog

from src.application.parsers.service_parser import ServiceParser
from src.domain.collectors.collector import Collector
from src.domain.collectors.collector_result import CollectorResult
from src.domain.collectors.collector_status import CollectorStatus
from src.domain.collectors.metric_type import MetricType
from src.domain.executor.command_executor import CommandExecutor

logger = structlog.get_logger(__name__)


class ServiceCollector(Collector):
    """
    Why this class exists:
    Gathers Linux system service states inside the Infrastructure layer.

    Responsibility:
    Executes systemctl commands, feeds output to ServiceParser, and returns a structured CollectorResult.

    Who uses it:
    Orchestration engines and scheduling loops.
    """

    def __init__(self, executor: CommandExecutor) -> None:
        """
        Initialize ServiceCollector with a command executor.

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
        return "ServiceCollector"

    @property
    def metric_type(self) -> str:
        """
        Return the metric type name.

        Returns:
            str: Metric type classification.
        """
        return MetricType.SERVICE

    async def collect(self, executor: Optional[CommandExecutor] = None) -> CollectorResult:
        """
        Asynchronously collect service metrics and return a standardized result.

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

        # Query services
        try:
            # 1. Run systemctl list-units
            list_res = await exec_to_use.execute(
                "systemctl",
                ["list-units", "--type=service", "--all", "--no-pager", "--no-legend"],
            )

            if not list_res.success:
                status = CollectorStatus.FAILED
                errors.append(f"Failed to execute systemctl list-units: {list_res.stderr}")
            else:
                # Parse service names to limit the scope of detail query
                parsed_names = []
                for line in list_res.stdout.splitlines():
                    line = line.strip()
                    if not line:
                        continue
                    parts = line.split()
                    if parts and parts[0].endswith(".service"):
                        parsed_names.append(parts[0])

                # 2. Run systemctl show for the parsed units (if any exist)
                show_stdout = None
                if parsed_names:
                    # Request specific properties to minimize output payload
                    show_args = ["show"] + parsed_names
                    show_res = await exec_to_use.execute("systemctl", show_args)
                    if show_res.success:
                        show_stdout = show_res.stdout
                    else:
                        logger.warning("Failed to execute systemctl show", error=show_res.stderr)

                try:
                    metrics = ServiceParser.parse(
                        list_units_output=list_res.stdout,
                        show_output=show_stdout,
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

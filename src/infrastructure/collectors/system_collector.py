"""
-------------------------------------------------------
File:
system_collector.py

Purpose:
Infrastructure collector implementation for gathering Linux host static metadata.

Why this file exists:
Implements the abstract Collector interface to run commands like hostnamectl, uname, os-release, lscpu, uptime, and timezone.

Responsibilities:
- Implement the abstract Collector interface.
- Execute hostnamectl, uname -a, os-release, lscpu, uptime, and cat /etc/timezone.
- Feed output strings into SystemParser.
- Handle exceptions and return a structured CollectorResult.

Used By:
- Telemetry Orchestrators
- Agent Runner

Depends On:
- src.domain.collectors.collector.Collector
- src.domain.collectors.collector_result.CollectorResult
- src.domain.collectors.collector_status.CollectorStatus
- src.domain.collectors.metric_type.MetricType
- src.domain.executor.command_executor.CommandExecutor
- src.application.parsers.system_parser.SystemParser
-------------------------------------------------------
"""

from datetime import datetime, timezone
import time
from typing import Optional
import structlog

from src.application.parsers.system_parser import SystemParser
from src.domain.collectors.collector import Collector
from src.domain.collectors.collector_result import CollectorResult
from src.domain.collectors.collector_status import CollectorStatus
from src.domain.collectors.metric_type import MetricType
from src.domain.executor.command_executor import CommandExecutor

logger = structlog.get_logger(__name__)


class SystemCollector(Collector):
    """
    Why this class exists:
    Gathers Linux host metadata and static hardware info inside the Infrastructure layer.

    Responsibility:
    Executes static query commands, invokes SystemParser, and returns structured CollectorResult.

    Who uses it:
    Orchestration engines and scheduling loops.
    """

    def __init__(self, executor: CommandExecutor) -> None:
        """
        Initialize SystemCollector with a command executor.

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
        return "SystemCollector"

    @property
    def metric_type(self) -> str:
        """
        Return the metric type name.

        Returns:
            str: Metric type classification.
        """
        return MetricType.SYSTEM

    async def collect(self, executor: Optional[CommandExecutor] = None) -> CollectorResult:
        """
        Asynchronously collect static system metrics and return a standardized result.

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

        # Query all system files and commands
        try:
            hctl_res = await exec_to_use.execute("hostnamectl", [])
            uname_res = await exec_to_use.execute("uname", ["-a"])
            osrel_res = await exec_to_use.execute("cat", ["/etc/os-release"])
            lscpu_res = await exec_to_use.execute("lscpu", [])
            uptime_res = await exec_to_use.execute("uptime", [])
            tz_res = await exec_to_use.execute("cat", ["/etc/timezone"])

            # Verify command results
            failed_commands = []
            if not hctl_res.success:
                # Hostnamectl might not exist in tiny containers, log warning but don't strictly fail yet
                logger.warning("hostnamectl command failed", error=hctl_res.stderr)
            if not uname_res.success:
                failed_commands.append(f"uname -a: {uname_res.stderr}")
            if not osrel_res.success:
                failed_commands.append(f"/etc/os-release: {osrel_res.stderr}")
            if not lscpu_res.success:
                failed_commands.append(f"lscpu: {lscpu_res.stderr}")
            if not uptime_res.success:
                failed_commands.append(f"uptime: {uptime_res.stderr}")

            if failed_commands:
                status = CollectorStatus.FAILED
                errors.append(f"Failed to gather system metadata: {', '.join(failed_commands)}")
            else:
                # Extract timezone, fallback to UTC if command failed
                tz_stdout = tz_res.stdout.strip() if tz_res.success else "UTC"
                hctl_stdout = hctl_res.stdout if hctl_res.success else ""

                try:
                    metrics = SystemParser.parse(
                        hostnamectl_output=hctl_stdout,
                        uname_output=uname_res.stdout,
                        os_release_output=osrel_res.stdout,
                        lscpu_output=lscpu_res.stdout,
                        uptime_output=uptime_res.stdout,
                        timezone_output=tz_stdout,
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

        # Ensure hostname is updated from payload if resolved
        if payload and "host_identity" in payload:
            parsed_hostname = payload["host_identity"].get("hostname")
            if parsed_hostname and parsed_hostname != "unknown":
                hostname = parsed_hostname

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



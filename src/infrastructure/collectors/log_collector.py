"""
-------------------------------------------------------
File:
log_collector.py

Purpose:
Infrastructure collector implementation for gathering system log telemetry.

Why this file exists:
Implements the abstract Collector interface to securely query host logs using journalctl and tail.

Responsibilities:
- Implement the abstract Collector interface.
- Execute journalctl --no-pager --output=short-iso -n 1000.
- Fallback to tail -n 1000 /var/log/syslog if journalctl is unavailable/failed.
- Extract tail -n 1000 /var/log/messages when available.
- Feed output strings into LogParser.
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
- src.application.parsers.log_parser.LogParser
-------------------------------------------------------
"""

from datetime import datetime, timezone
import time
from typing import Optional
import structlog

from src.application.parsers.log_parser import LogParser
from src.domain.collectors.collector import Collector
from src.domain.collectors.collector_result import CollectorResult
from src.domain.collectors.collector_status import CollectorStatus
from src.domain.collectors.metric_type import MetricType
from src.domain.executor.command_executor import CommandExecutor

logger = structlog.get_logger(__name__)


class LogCollector(Collector):
    """
    Why this class exists:
    Gathers Linux host log telemetry inside the Infrastructure layer.

    Responsibility:
    Executes log extraction commands, invokes LogParser, and returns structured CollectorResult.

    Who uses it:
    Orchestration engines and scheduling loops.
    """

    def __init__(self, executor: CommandExecutor) -> None:
        """
        Initialize LogCollector with a command executor.

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
        return "LogCollector"

    @property
    def metric_type(self) -> str:
        """
        Return the metric type name.

        Returns:
            str: Metric type classification.
        """
        return MetricType.LOG

    async def collect(self, executor: Optional[CommandExecutor] = None) -> CollectorResult:
        """
        Asynchronously collect host logs and return a standardized result.

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

        journalctl_output = ""
        syslog_output = ""
        messages_output = ""

        # 1. Try journalctl
        try:
            journal_res = await exec_to_use.execute(
                "journalctl", ["--no-pager", "--output=short-iso", "-n", "1000"]
            )
            if journal_res.success:
                journalctl_output = journal_res.stdout
            else:
                logger.info(
                    "journalctl failed or not supported, attempting syslog fallback",
                    stderr=journal_res.stderr,
                )
        except Exception as journal_err:
            logger.info("journalctl collection failed", error=str(journal_err))

        # 2. Try syslog fallback if journalctl produced no logs
        if not journalctl_output:
            try:
                syslog_res = await exec_to_use.execute(
                    "tail", ["-n", "1000", "/var/log/syslog"]
                )
                if syslog_res.success:
                    syslog_output = syslog_res.stdout
                else:
                    logger.info("syslog tail failed", stderr=syslog_res.stderr)
            except Exception as syslog_err:
                logger.info("syslog fallback failed", error=str(syslog_err))

        # 3. Try messages additional source
        try:
            messages_res = await exec_to_use.execute(
                "tail", ["-n", "1000", "/var/log/messages"]
            )
            if messages_res.success:
                messages_output = messages_res.stdout
            else:
                logger.info("messages tail failed", stderr=messages_res.stderr)
        except Exception as messages_err:
            logger.info("messages collection failed", error=str(messages_err))

        # If all sources failed to get any data, log warning but don't crash
        if not any([journalctl_output, syslog_output, messages_output]):
            logger.warning("No log sources succeeded or had content")

        try:
            metrics = LogParser.parse(
                journalctl_output=journalctl_output,
                syslog_output=syslog_output,
                messages_output=messages_output,
                timestamp=timestamp,
            )
            payload = metrics.model_dump()
        except Exception as parse_err:
            status = CollectorStatus.FAILED
            errors.append(f"Parsing failed: {str(parse_err)}")

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

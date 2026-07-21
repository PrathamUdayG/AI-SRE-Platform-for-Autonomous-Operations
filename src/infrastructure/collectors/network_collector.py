"""
-------------------------------------------------------
File:
network_collector.py

Purpose:
Infrastructure collector implementation for gathering Linux network metrics.

Why this file exists:
Implements the abstract Collector interface for network telemetry, coordinating executions of cat /proc/net/dev, ip addr, ip route, tcp and udp stats.

Responsibilities:
- Implement the abstract Collector interface.
- Execute net/dev, ip addr, ip route, net/tcp, net/udp reads.
- Pass raw strings to NetworkParser and return a CollectorResult.

Used By:
- Telemetry Orchestrators
- Agent Runner

Depends On:
- src.domain.collectors.collector.Collector
- src.domain.collectors.collector_result.CollectorResult
- src.domain.collectors.collector_status.CollectorStatus
- src.domain.collectors.metric_type.MetricType
- src.domain.executor.command_executor.CommandExecutor
- src.application.parsers.network_parser.NetworkParser
-------------------------------------------------------
"""

from datetime import datetime, timezone
import time
from typing import Optional
import structlog

from src.application.parsers.network_parser import NetworkParser
from src.domain.collectors.collector import Collector
from src.domain.collectors.collector_result import CollectorResult
from src.domain.collectors.collector_status import CollectorStatus
from src.domain.collectors.metric_type import MetricType
from src.domain.executor.command_executor import CommandExecutor

logger = structlog.get_logger(__name__)


class NetworkCollector(Collector):
    """
    Why this class exists:
    Gathers Linux network metrics inside the Infrastructure layer.

    Responsibility:
    Executes networking query commands, invokes NetworkParser, and returns structured CollectorResult.

    Who uses it:
    Orchestration engines and scheduling loops.
    """

    def __init__(self, executor: CommandExecutor) -> None:
        """
        Initialize NetworkCollector with a command executor.

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
        return "NetworkCollector"

    @property
    def metric_type(self) -> str:
        """
        Return the metric type name.

        Returns:
            str: Metric type classification.
        """
        return MetricType.NETWORK

    async def collect(self, executor: Optional[CommandExecutor] = None) -> CollectorResult:
        """
        Asynchronously collect network metrics and return a standardized result.

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

        # Query all network files and CLI outputs
        try:
            dev_res = await exec_to_use.execute("cat", ["/proc/net/dev"])
            addr_res = await exec_to_use.execute("ip", ["-o", "addr", "show"])
            route_res = await exec_to_use.execute("ip", ["route", "show"])
            tcp_res = await exec_to_use.execute("cat", ["/proc/net/tcp"])
            udp_res = await exec_to_use.execute("cat", ["/proc/net/udp"])

            # Verify all command results
            failed_commands = []
            if not dev_res.success:
                failed_commands.append(f"/proc/net/dev: {dev_res.stderr}")
            if not addr_res.success:
                failed_commands.append(f"ip addr: {addr_res.stderr}")
            if not route_res.success:
                failed_commands.append(f"ip route: {route_res.stderr}")
            if not tcp_res.success:
                failed_commands.append(f"/proc/net/tcp: {tcp_res.stderr}")
            if not udp_res.success:
                failed_commands.append(f"/proc/net/udp: {udp_res.stderr}")

            if failed_commands:
                status = CollectorStatus.FAILED
                errors.append(f"Failed to gather network raw source data: {', '.join(failed_commands)}")
            else:
                try:
                    metrics = NetworkParser.parse(
                        proc_net_dev_output=dev_res.stdout,
                        ip_addr_output=addr_res.stdout,
                        ip_route_output=route_res.stdout,
                        proc_tcp_output=tcp_res.stdout,
                        proc_udp_output=udp_res.stdout,
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

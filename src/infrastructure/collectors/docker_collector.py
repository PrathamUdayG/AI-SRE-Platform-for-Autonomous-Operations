"""
-------------------------------------------------------
File:
docker_collector.py

Purpose:
Infrastructure collector implementation for gathering Docker runtime telemetry.

Why this file exists:
Implements the abstract Collector interface to run commands like docker ps, inspect, stats, network, and volume.

Responsibilities:
- Implement the abstract Collector interface.
- Execute docker ps --no-trunc to find running containers.
- Execute docker inspect on all active container IDs in a single batch.
- Execute docker stats --no-stream --no-trunc for resource telemetry.
- Execute docker network ls and docker volume ls.
- Feed output strings into DockerParser.
- Handle systems without Docker or daemon failures gracefully.

Used By:
- Telemetry Orchestrators
- Agent Runner

Depends On:
- src.domain.collectors.collector.Collector
- src.domain.collectors.collector_result.CollectorResult
- src.domain.collectors.collector_status.CollectorStatus
- src.domain.collectors.metric_type.MetricType
- src.domain.executor.command_executor.CommandExecutor
- src.application.parsers.docker_parser.DockerParser
-------------------------------------------------------
"""

from datetime import datetime, timezone
import time
from typing import Optional
import structlog

from src.application.parsers.docker_parser import DockerParser
from src.domain.collectors.collector import Collector
from src.domain.collectors.collector_result import CollectorResult
from src.domain.collectors.collector_status import CollectorStatus
from src.domain.collectors.metric_type import MetricType
from src.domain.executor.command_executor import CommandExecutor

logger = structlog.get_logger(__name__)


class DockerCollector(Collector):
    """
    Why this class exists:
    Gathers Docker virtualization and runtime metrics inside the Infrastructure layer.

    Responsibility:
    Executes Docker CLI commands, handles missing daemon gracefully, and returns structured CollectorResult.

    Who uses it:
    Orchestration engines and scheduling loops.
    """

    def __init__(self, executor: CommandExecutor) -> None:
        """
        Initialize DockerCollector with a command executor.

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
        return "DockerCollector"

    @property
    def metric_type(self) -> str:
        """
        Return the metric type name.

        Returns:
            str: Metric type classification.
        """
        return MetricType.DOCKER

    async def collect(self, executor: Optional[CommandExecutor] = None) -> CollectorResult:
        """
        Asynchronously collect Docker runtime metrics and return a standardized result.

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

        # 1. Probe if Docker is installed and the daemon is active
        try:
            ps_res = await exec_to_use.execute("docker", ["ps", "--no-trunc"])
            if not ps_res.success:
                logger.warning("Docker daemon is not running or available", stderr=ps_res.stderr)
                execution_time_ms = int((time.perf_counter() - start_time) * 1000)
                return CollectorResult(
                    timestamp=timestamp,
                    hostname=hostname,
                    collector_name=self.name,
                    metric_type=self.metric_type,
                    payload={},
                    status=CollectorStatus.FAILED,
                    errors=[f"Docker daemon is unavailable: {ps_res.stderr.strip()}"],
                    execution_time_ms=execution_time_ms,
                )
        except Exception as daemon_err:
            logger.warning("Docker executable not found or execution failed", error=str(daemon_err))
            execution_time_ms = int((time.perf_counter() - start_time) * 1000)
            return CollectorResult(
                timestamp=timestamp,
                hostname=hostname,
                collector_name=self.name,
                metric_type=self.metric_type,
                payload={},
                status=CollectorStatus.FAILED,
                errors=[f"Docker not installed or execution failed: {str(daemon_err)}"],
                execution_time_ms=execution_time_ms,
            )

        # 2. Extract container IDs from docker ps output
        container_ids = []
        lines = ps_res.stdout.strip().splitlines()
        if len(lines) > 1:
            for line in lines[1:]:
                parts = line.split()
                if parts:
                    container_ids.append(parts[0])

        # 3. Query details in batch if containers exist
        inspect_output = "[]"
        if container_ids:
            try:
                inspect_res = await exec_to_use.execute("docker", ["inspect"] + container_ids)
                if inspect_res.success:
                    inspect_output = inspect_res.stdout
                else:
                    errors.append(f"docker inspect failed: {inspect_res.stderr.strip()}")
            except Exception as e:
                errors.append(f"docker inspect execution failed: {str(e)}")

        stats_output = ""
        try:
            stats_res = await exec_to_use.execute("docker", ["stats", "--no-stream", "--no-trunc"])
            if stats_res.success:
                stats_output = stats_res.stdout
            else:
                errors.append(f"docker stats failed: {stats_res.stderr.strip()}")
        except Exception as e:
            errors.append(f"docker stats execution failed: {str(e)}")

        network_output = ""
        try:
            network_res = await exec_to_use.execute("docker", ["network", "ls"])
            if network_res.success:
                network_output = network_res.stdout
            else:
                errors.append(f"docker network ls failed: {network_res.stderr.strip()}")
        except Exception as e:
            errors.append(f"docker network execution failed: {str(e)}")

        volume_output = ""
        try:
            volume_res = await exec_to_use.execute("docker", ["volume", "ls"])
            if volume_res.success:
                volume_output = volume_res.stdout
            else:
                errors.append(f"docker volume ls failed: {volume_res.stderr.strip()}")
        except Exception as e:
            errors.append(f"docker volume execution failed: {str(e)}")

        # Parse collected outputs
        try:
            metrics = DockerParser.parse(
                inspect_output=inspect_output,
                stats_output=stats_output,
                network_output=network_output,
                volume_output=volume_output,
                timestamp=timestamp,
            )
            payload = metrics.model_dump()
        except Exception as parse_err:
            status = CollectorStatus.FAILED
            errors.append(f"Parsing failed: {str(parse_err)}")

        if errors:
            status = CollectorStatus.FAILED

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

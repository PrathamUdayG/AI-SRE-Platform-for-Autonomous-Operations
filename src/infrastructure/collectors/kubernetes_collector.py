"""
-------------------------------------------------------
File:
kubernetes_collector.py

Purpose:
Infrastructure collector implementation for gathering Kubernetes runtime telemetry.

Why this file exists:
Implements the abstract Collector interface to run commands like kubectl get nodes, pods, deployments, etc.

Responsibilities:
- Implement the abstract Collector interface.
- Execute kubectl get namespaces, nodes, pods, deployments, services, events, version.
- Feed output strings into KubernetesParser.
- Handle systems without kubectl or API server unreachable scenarios gracefully.

Used By:
- Telemetry Orchestrators
- Agent Runner

Depends On:
- src.domain.collectors.collector.Collector
- src.domain.collectors.collector_result.CollectorResult
- src.domain.collectors.collector_status.CollectorStatus
- src.domain.collectors.metric_type.MetricType
- src.domain.executor.command_executor.CommandExecutor
- src.application.parsers.kubernetes_parser.KubernetesParser
-------------------------------------------------------
"""

from datetime import datetime, timezone
import time
from typing import Optional
import structlog

from src.application.parsers.kubernetes_parser import KubernetesParser
from src.domain.collectors.collector import Collector
from src.domain.collectors.collector_result import CollectorResult
from src.domain.collectors.collector_status import CollectorStatus
from src.domain.collectors.metric_type import MetricType
from src.domain.executor.command_executor import CommandExecutor

logger = structlog.get_logger(__name__)


class KubernetesCollector(Collector):
    """
    Why this class exists:
    Gathers Kubernetes telemetry metrics inside the Infrastructure layer.

    Responsibility:
    Executes kubectl CLI commands, handles unreachable API server gracefully, and returns structured CollectorResult.

    Who uses it:
    Orchestration engines and scheduling loops.
    """

    def __init__(self, executor: CommandExecutor) -> None:
        """
        Initialize KubernetesCollector with a command executor.

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
        return "KubernetesCollector"

    @property
    def metric_type(self) -> str:
        """
        Return the metric type name.

        Returns:
            str: Metric type classification.
        """
        return MetricType.KUBERNETES

    async def collect(self, executor: Optional[CommandExecutor] = None) -> CollectorResult:
        """
        Asynchronously collect Kubernetes metrics and return a standardized result.

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

        # 1. Probe connectivity using namespaces
        namespaces_json = ""
        try:
            ns_res = await exec_to_use.execute("kubectl", ["get", "namespaces", "-o", "json"])
            if not ns_res.success:
                logger.warning("Kubernetes cluster is unreachable or auth failed", stderr=ns_res.stderr)
                execution_time_ms = int((time.perf_counter() - start_time) * 1000)
                return CollectorResult(
                    timestamp=timestamp,
                    hostname=hostname,
                    collector_name=self.name,
                    metric_type=self.metric_type,
                    payload={},
                    status=CollectorStatus.FAILED,
                    errors=[f"Kubernetes cluster unreachable: {ns_res.stderr.strip()}"],
                    execution_time_ms=execution_time_ms,
                )
            namespaces_json = ns_res.stdout
        except Exception as conn_err:
            logger.warning("kubectl client not installed or file not found", error=str(conn_err))
            execution_time_ms = int((time.perf_counter() - start_time) * 1000)
            return CollectorResult(
                timestamp=timestamp,
                hostname=hostname,
                collector_name=self.name,
                metric_type=self.metric_type,
                payload={},
                status=CollectorStatus.FAILED,
                errors=[f"Kubernetes client unavailable: {str(conn_err)}"],
                execution_time_ms=execution_time_ms,
            )

        # 2. Collect other metrics
        nodes_json = ""
        try:
            nodes_res = await exec_to_use.execute("kubectl", ["get", "nodes", "-o", "json"])
            if nodes_res.success:
                nodes_json = nodes_res.stdout
            else:
                errors.append(f"kubectl get nodes failed: {nodes_res.stderr.strip()}")
        except Exception as e:
            errors.append(f"kubectl get nodes execution failed: {str(e)}")

        pods_json = ""
        try:
            pods_res = await exec_to_use.execute(
                "kubectl", ["get", "pods", "--all-namespaces", "-o", "json"]
            )
            if pods_res.success:
                pods_json = pods_res.stdout
            else:
                errors.append(f"kubectl get pods failed: {pods_res.stderr.strip()}")
        except Exception as e:
            errors.append(f"kubectl get pods execution failed: {str(e)}")

        deployments_json = ""
        try:
            depl_res = await exec_to_use.execute(
                "kubectl", ["get", "deployments", "--all-namespaces", "-o", "json"]
            )
            if depl_res.success:
                deployments_json = depl_res.stdout
            else:
                errors.append(f"kubectl get deployments failed: {depl_res.stderr.strip()}")
        except Exception as e:
            errors.append(f"kubectl get deployments execution failed: {str(e)}")

        services_json = ""
        try:
            srv_res = await exec_to_use.execute(
                "kubectl", ["get", "services", "--all-namespaces", "-o", "json"]
            )
            if srv_res.success:
                services_json = srv_res.stdout
            else:
                errors.append(f"kubectl get services failed: {srv_res.stderr.strip()}")
        except Exception as e:
            errors.append(f"kubectl get services execution failed: {str(e)}")

        # Optional metrics: version
        version_json = ""
        try:
            ver_res = await exec_to_use.execute("kubectl", ["version", "-o", "json"])
            if ver_res.success:
                version_json = ver_res.stdout
        except Exception:
            pass

        # Optional metrics: events
        events_json = ""
        try:
            evt_res = await exec_to_use.execute(
                "kubectl", ["get", "events", "--all-namespaces", "-o", "json"]
            )
            if evt_res.success:
                events_json = evt_res.stdout
        except Exception:
            pass

        # Parse outputs
        try:
            metrics = KubernetesParser.parse(
                namespaces_json=namespaces_json,
                nodes_json=nodes_json,
                pods_json=pods_json,
                deployments_json=deployments_json,
                services_json=services_json,
                events_json=events_json,
                version_json=version_json,
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

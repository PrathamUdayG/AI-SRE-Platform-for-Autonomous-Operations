"""
-------------------------------------------------------
File:
test_kubernetes_collector.py

Purpose:
Unit tests for the KubernetesCollector in the Infrastructure Layer.

Why this file exists:
Verifies that KubernetesCollector executes the correct kubectl pipelines, handles offline/unreachable cluster states gracefully, and compiles results.

Responsibilities:
- Verify properties (name, metric_type).
- Mock CommandExecutor to return success results and verify parsing integration.
- Verify fallback behavior when kubectl is not installed.
- Verify behavior when Kubernetes cluster API is unreachable.

Used By:
- pytest runner

Depends On:
- src.infrastructure.collectors.kubernetes_collector
- src.domain.executor.command_executor.CommandExecutor
-------------------------------------------------------
"""

from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock
import pytest

from src.domain.collectors.collector_status import CollectorStatus
from src.domain.collectors.metric_type import MetricType
from src.domain.executor.command_executor import CommandExecutor
from src.domain.executor.command_result import CommandResult
from src.infrastructure.collectors.kubernetes_collector import KubernetesCollector


@pytest.fixture
def mock_executor():
    return MagicMock(spec=CommandExecutor)


@pytest.fixture
def collector(mock_executor):
    return KubernetesCollector(executor=mock_executor)


@pytest.mark.asyncio
async def test_collector_properties(collector):
    """Verify KubernetesCollector properties."""
    assert collector.name == "KubernetesCollector"
    assert collector.metric_type == MetricType.KUBERNETES


@pytest.mark.asyncio
async def test_collect_cluster_unreachable(collector, mock_executor):
    """Verify collector fails gracefully if the cluster API is down."""
    now = datetime.now(timezone.utc)
    
    hostname_res = CommandResult(
        command="hostname",
        arguments=[],
        stdout="my-host",
        stderr="",
        exit_code=0,
        execution_time_ms=1,
        timed_out=False,
        success=True,
        timestamp=now
    )
    
    ns_res = CommandResult(
        command="kubectl",
        arguments=["get", "namespaces", "-o", "json"],
        stdout="",
        stderr="The connection to the server localhost:6443 was refused",
        exit_code=1,
        execution_time_ms=5,
        timed_out=False,
        success=False,
        timestamp=now
    )

    async def mock_execute(command, arguments=None):
        if command == "hostname":
            return hostname_res
        elif command == "kubectl":
            return ns_res
        raise ValueError(f"Unexpected: {command}")

    mock_executor.execute = AsyncMock(side_effect=mock_execute)
    result = await collector.collect()
    
    assert result.status == CollectorStatus.FAILED
    assert "Kubernetes cluster unreachable" in result.errors[0]
    assert result.payload == {}


@pytest.mark.asyncio
async def test_collect_kubectl_not_installed(collector, mock_executor):
    """Verify collector fails gracefully if kubectl is not installed."""
    now = datetime.now(timezone.utc)
    
    hostname_res = CommandResult(
        command="hostname",
        arguments=[],
        stdout="my-host",
        stderr="",
        exit_code=0,
        execution_time_ms=1,
        timed_out=False,
        success=True,
        timestamp=now
    )

    async def mock_execute(command, arguments=None):
        if command == "hostname":
            return hostname_res
        elif command == "kubectl":
            raise FileNotFoundError("kubectl not found")
        raise ValueError(f"Unexpected: {command}")

    mock_executor.execute = AsyncMock(side_effect=mock_execute)
    result = await collector.collect()
    
    assert result.status == CollectorStatus.FAILED
    assert "Kubernetes client unavailable" in result.errors[0]
    assert result.payload == {}


@pytest.mark.asyncio
async def test_collect_success(collector, mock_executor):
    """Verify successful collection when Kubernetes is active."""
    now = datetime.now(timezone.utc)
    
    hostname_res = CommandResult(
        command="hostname",
        arguments=[],
        stdout="my-host",
        stderr="",
        exit_code=0,
        execution_time_ms=1,
        timed_out=False,
        success=True,
        timestamp=now
    )
    
    ns_res = CommandResult(
        command="kubectl",
        arguments=["get", "namespaces", "-o", "json"],
        stdout='{"items": [{"metadata": {"name": "default"}, "status": {"phase": "Active"}}]}',
        stderr="",
        exit_code=0,
        execution_time_ms=5,
        timed_out=False,
        success=True,
        timestamp=now
    )
    
    nodes_res = CommandResult(
        command="kubectl",
        arguments=["get", "nodes", "-o", "json"],
        stdout='{"items": [{"metadata": {"name": "node1"}, "status": {"nodeInfo": {"osImage": "linux"}}}]}',
        stderr="",
        exit_code=0,
        execution_time_ms=5,
        timed_out=False,
        success=True,
        timestamp=now
    )
    
    pods_res = CommandResult(
        command="kubectl",
        arguments=["get", "pods", "--all-namespaces", "-o", "json"],
        stdout='{"items": []}',
        stderr="",
        exit_code=0,
        execution_time_ms=5,
        timed_out=False,
        success=True,
        timestamp=now
    )
    
    depl_res = CommandResult(
        command="kubectl",
        arguments=["get", "deployments", "--all-namespaces", "-o", "json"],
        stdout='{"items": []}',
        stderr="",
        exit_code=0,
        execution_time_ms=5,
        timed_out=False,
        success=True,
        timestamp=now
    )
    
    srv_res = CommandResult(
        command="kubectl",
        arguments=["get", "services", "--all-namespaces", "-o", "json"],
        stdout='{"items": []}',
        stderr="",
        exit_code=0,
        execution_time_ms=5,
        timed_out=False,
        success=True,
        timestamp=now
    )
    
    ver_res = CommandResult(
        command="kubectl",
        arguments=["version", "-o", "json"],
        stdout='{"clientVersion": {"gitVersion": "v1.28.2"}}',
        stderr="",
        exit_code=0,
        execution_time_ms=5,
        timed_out=False,
        success=True,
        timestamp=now
    )
    
    evt_res = CommandResult(
        command="kubectl",
        arguments=["get", "events", "--all-namespaces", "-o", "json"],
        stdout='{"items": []}',
        stderr="",
        exit_code=0,
        execution_time_ms=5,
        timed_out=False,
        success=True,
        timestamp=now
    )

    async def mock_execute(command, arguments=None):
        if command == "hostname":
            return hostname_res
        elif command == "kubectl":
            if arguments == ["get", "namespaces", "-o", "json"]:
                return ns_res
            elif arguments == ["get", "nodes", "-o", "json"]:
                return nodes_res
            elif arguments == ["get", "pods", "--all-namespaces", "-o", "json"]:
                return pods_res
            elif arguments == ["get", "deployments", "--all-namespaces", "-o", "json"]:
                return depl_res
            elif arguments == ["get", "services", "--all-namespaces", "-o", "json"]:
                return srv_res
            elif arguments == ["version", "-o", "json"]:
                return ver_res
            elif arguments == ["get", "events", "--all-namespaces", "-o", "json"]:
                return evt_res
        raise ValueError(f"Unexpected: {command} {arguments}")

    mock_executor.execute = AsyncMock(side_effect=mock_execute)
    result = await collector.collect()
    
    assert result.status == CollectorStatus.SUCCESS
    assert result.errors == []
    assert result.payload["cluster"]["kubernetes_version"] == "v1.28.2"
    assert len(result.payload["namespaces"]) == 1
    assert result.payload["namespaces"][0]["name"] == "default"
    assert len(result.payload["nodes"]) == 1
    assert result.payload["nodes"][0]["name"] == "node1"

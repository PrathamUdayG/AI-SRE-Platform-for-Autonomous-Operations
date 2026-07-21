"""
-------------------------------------------------------
File:
test_kubernetes_parser.py

Purpose:
Unit tests for the KubernetesParser in the Application Layer.

Why this file exists:
Verifies that various Kubernetes command outputs (JSON list results) are parsed correctly.

Responsibilities:
- Verify parsing of namespaces.
- Verify node info, including internal IP and roles extraction.
- Verify pod info with UID and restart count summation.
- Verify deployments and services.
- Verify version parsing.

Used By:
- pytest runner

Depends On:
- src.application.parsers.kubernetes_parser
-------------------------------------------------------
"""

from datetime import datetime, timezone
import pytest

from src.application.parsers.kubernetes_parser import KubernetesParser


def test_parse_namespaces():
    """Verify parsing namespaces JSON."""
    ns_json = """
    {
        "items": [
            {
                "metadata": {
                    "name": "kube-system",
                    "labels": {"control-plane": "true"}
                },
                "status": {
                    "phase": "Active"
                }
            }
        ]
    }
    """
    metrics = KubernetesParser.parse(
        namespaces_json=ns_json,
        nodes_json="{}",
        pods_json="{}",
        deployments_json="{}",
        services_json="{}",
        events_json="{}",
        version_json="{}",
        timestamp=datetime.now(timezone.utc),
    )
    
    assert len(metrics.namespaces) == 1
    ns = metrics.namespaces[0]
    assert ns.name == "kube-system"
    assert ns.status == "Active"
    assert ns.labels == {"control-plane": "true"}


def test_parse_nodes():
    """Verify parsing nodes JSON with internal IP and roles extraction."""
    nodes_json = """
    {
        "items": [
            {
                "metadata": {
                    "name": "node-1",
                    "labels": {
                        "node-role.kubernetes.io/master": "",
                        "kubernetes.io/hostname": "node-1"
                    }
                },
                "status": {
                    "addresses": [
                        {"type": "InternalIP", "address": "192.168.1.10"}
                    ],
                    "nodeInfo": {
                        "osImage": "Ubuntu 22.04 LTS",
                        "kernelVersion": "5.15.0",
                        "containerRuntimeVersion": "containerd://1.6.8",
                        "kubeletVersion": "v1.28.2"
                    },
                    "capacity": {"cpu": "4", "memory": "8Gi"},
                    "allocatable": {"cpu": "3.5", "memory": "7.5Gi"}
                }
            }
        ]
    }
    """
    metrics = KubernetesParser.parse(
        namespaces_json="{}",
        nodes_json=nodes_json,
        pods_json="{}",
        deployments_json="{}",
        services_json="{}",
        events_json="{}",
        version_json="{}",
        timestamp=datetime.now(timezone.utc),
    )
    
    assert len(metrics.nodes) == 1
    node = metrics.nodes[0]
    assert node.name == "node-1"
    assert node.roles == ["master"]
    assert node.internal_ip == "192.168.1.10"
    assert node.os_image == "Ubuntu 22.04 LTS"
    assert node.container_runtime == "containerd://1.6.8"
    assert node.capacity == {"cpu": "4", "memory": "8Gi"}


def test_parse_pods():
    """Verify parsing pods JSON."""
    pods_json = """
    {
        "items": [
            {
                "metadata": {
                    "namespace": "default",
                    "name": "my-pod",
                    "uid": "uid-123"
                },
                "spec": {
                    "nodeName": "node-1",
                    "containers": [{"image": "nginx:latest"}],
                    "initContainers": [{"image": "busybox"}]
                },
                "status": {
                    "phase": "Running",
                    "podIP": "10.244.0.5",
                    "hostIP": "192.168.1.10",
                    "startTime": "2026-07-21T14:29:48Z",
                    "containerStatuses": [{"restartCount": 2}],
                    "initContainerStatuses": [{"restartCount": 1}]
                }
            }
        ]
    }
    """
    metrics = KubernetesParser.parse(
        namespaces_json="{}",
        nodes_json="{}",
        pods_json=pods_json,
        deployments_json="{}",
        services_json="{}",
        events_json="{}",
        version_json="{}",
        timestamp=datetime.now(timezone.utc),
    )
    
    assert len(metrics.pods) == 1
    pod = metrics.pods[0]
    assert pod.pod_name == "my-pod"
    assert pod.namespace == "default"
    assert pod.uid == "uid-123"
    assert pod.phase == "Running"
    assert pod.pod_ip == "10.244.0.5"
    assert pod.restart_count == 3
    assert pod.container_images == ["nginx:latest", "busybox"]
    assert pod.start_time is not None


def test_parse_deployments_and_services():
    """Verify deployments and services parsing."""
    depl_json = """
    {
        "items": [
            {
                "metadata": {
                    "namespace": "default",
                    "name": "nginx-deployment"
                },
                "spec": {
                    "replicas": 3
                },
                "status": {
                    "availableReplicas": 2,
                    "updatedReplicas": 3
                }
            }
        ]
    }
    """
    srv_json = """
    {
        "items": [
            {
                "metadata": {
                    "namespace": "default",
                    "name": "my-service"
                },
                "spec": {
                    "type": "ClusterIP",
                    "clusterIP": "10.96.0.1",
                    "ports": [
                        {"name": "http", "port": 80, "protocol": "TCP", "targetPort": 8080}
                    ]
                },
                "status": {
                    "loadBalancer": {}
                }
            }
        ]
    }
    """
    metrics = KubernetesParser.parse(
        namespaces_json="{}",
        nodes_json="{}",
        pods_json="{}",
        deployments_json=depl_json,
        services_json=srv_json,
        events_json="{}",
        version_json="{}",
        timestamp=datetime.now(timezone.utc),
    )
    
    assert len(metrics.deployments) == 1
    assert metrics.deployments[0].deployment_name == "nginx-deployment"
    assert metrics.deployments[0].desired_replicas == 3
    assert metrics.deployments[0].available_replicas == 2
    
    assert len(metrics.services) == 1
    srv = metrics.services[0]
    assert srv.service_name == "my-service"
    assert srv.cluster_ip == "10.96.0.1"
    assert len(srv.ports) == 1
    assert srv.ports[0].port == 80
    assert srv.ports[0].target_port == "8080"

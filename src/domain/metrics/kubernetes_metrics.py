"""
-------------------------------------------------------
File:
kubernetes_metrics.py

Purpose:
Domain model representing normalized Kubernetes cluster telemetry.

Why this file exists:
Provides a strongly typed, infrastructure-agnostic representation of Kubernetes nodes, namespaces, pods, deployments, services, and events.

Responsibilities:
- Encapsulate cluster-level assets and versions in structured domain models.

Used By:
- KubernetesParser
- KubernetesCollector

Notes:
This file belongs to the Domain Layer as it defines a core telemetry data structure.
-------------------------------------------------------
"""

from datetime import datetime
from typing import Dict, List, Optional
from pydantic import BaseModel, Field


class ClusterInfo(BaseModel):
    """
    Why this class exists:
    Encapsulates Kubernetes system level and API versions.
    """

    kubernetes_version: str = Field(description="Kubernetes client/control version")
    api_server_version: Optional[str] = Field(None, description="Kubernetes API server version")


class NamespaceInfo(BaseModel):
    """
    Why this class exists:
    Encapsulates namespace names and status states.
    """

    name: str = Field(description="Namespace identifier")
    status: str = Field(description="Namespace status phase (e.g. Active)")
    labels: Dict[str, str] = Field(default_factory=dict, description="Namespace labels")


class NodeInfo(BaseModel):
    """
    Why this class exists:
    Encapsulates cluster node hardware capacity, configuration, and runtime components.
    """

    name: str = Field(description="Node hostname or node name")
    roles: List[str] = Field(default_factory=list, description="Assigned node roles")
    labels: Dict[str, str] = Field(default_factory=dict, description="Node label attributes")
    internal_ip: Optional[str] = Field(None, description="Host internal IP address")
    os_image: str = Field(description="Operating System OS image")
    kernel_version: str = Field(description="Kernel compilation string")
    container_runtime: str = Field(description="Container engine runtime version")
    kubelet_version: str = Field(description="Installed Kubelet agent version")
    capacity: Dict[str, str] = Field(default_factory=dict, description="Total node resources capacity")
    allocatable: Dict[str, str] = Field(default_factory=dict, description="Allocatable resources capacity")


class PodInfo(BaseModel):
    """
    Why this class exists:
    Encapsulates a pod running phase, node mapping, restart count, and image references.
    """

    namespace: str = Field(description="Hosting namespace")
    pod_name: str = Field(description="Pod metadata name")
    uid: str = Field(description="Unique pod resource UID")
    node_name: Optional[str] = Field(None, description="Hosting Node name")
    phase: str = Field(description="Current status phase (e.g. Running, Pending)")
    pod_ip: Optional[str] = Field(None, description="Pod IP address")
    host_ip: Optional[str] = Field(None, description="Node host IP address")
    start_time: Optional[datetime] = Field(None, description="Timestamp when pod was started")
    restart_count: int = Field(description="Sum total of all container restarts")
    container_images: List[str] = Field(default_factory=list, description="Container images references list")


class DeploymentInfo(BaseModel):
    """
    Why this class exists:
    Encapsulates deployment metadata and replica status telemetry.
    """

    namespace: str = Field(description="Hosting namespace")
    deployment_name: str = Field(description="Deployment metadata name")
    desired_replicas: int = Field(description="Number of desired replicas")
    available_replicas: int = Field(description="Number of currently available replicas")
    updated_replicas: int = Field(description="Number of updated replicas")


class ServicePort(BaseModel):
    """
    Why this class exists:
    Encapsulates a service network port mapping.
    """

    name: Optional[str] = Field(None, description="Port mapping name tag")
    port: int = Field(description="Exposed service port")
    protocol: str = Field(description="IP protocol (TCP/UDP)")
    target_port: Optional[str] = Field(None, description="Container target port mapping")


class ServiceInfo(BaseModel):
    """
    Why this class exists:
    Encapsulates service endpoints, networking types, and cluster/external IPs.
    """

    namespace: str = Field(description="Hosting namespace")
    service_name: str = Field(description="Service metadata name")
    type: str = Field(description="Service networking type (e.g. ClusterIP, LoadBalancer)")
    cluster_ip: str = Field(description="Internal cluster IP allocation")
    external_ip: List[str] = Field(default_factory=list, description="External load-balancer IPs")
    ports: List[ServicePort] = Field(default_factory=list, description="Service network ports list")


class InvolvedObject(BaseModel):
    """
    Why this class exists:
    Identifies the resource context for a cluster event.
    """

    kind: str = Field(description="Object API kind (e.g. Pod)")
    name: str = Field(description="Object name identifier")
    namespace: Optional[str] = Field(None, description="Object hosting namespace")


class EventInfo(BaseModel):
    """
    Why this class exists:
    Encapsulates a normalized cluster event log.
    """

    timestamp: datetime = Field(description="Timestamp of the event log")
    namespace: str = Field(description="Object event namespace")
    involved_object: InvolvedObject = Field(description="Reference object metadata")
    reason: str = Field(description="Short reason code (e.g. Scheduled)")
    message: str = Field(description="Detailed event log message text")
    type: str = Field(description="Event classification category (e.g. Normal, Warning)")


class KubernetesMetrics(BaseModel):
    """
    Why this class exists:
    Main container model for all collected Kubernetes metrics.
    """

    cluster: ClusterInfo = Field(description="Cluster level configuration info")
    namespaces: List[NamespaceInfo] = Field(
        default_factory=list, description="List of cluster namespaces"
    )
    nodes: List[NodeInfo] = Field(default_factory=list, description="List of cluster nodes info")
    pods: List[PodInfo] = Field(default_factory=list, description="List of cluster pods info")
    deployments: List[DeploymentInfo] = Field(
        default_factory=list, description="List of cluster deployments info"
    )
    services: List[ServiceInfo] = Field(
        default_factory=list, description="List of cluster network services"
    )
    events: List[EventInfo] = Field(
        default_factory=list, description="List of recent cluster event logs"
    )
    timestamp: datetime = Field(description="UTC timestamp of when the metrics were captured")

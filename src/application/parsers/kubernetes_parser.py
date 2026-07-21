"""
-------------------------------------------------------
File:
kubernetes_parser.py

Purpose:
Parses Kubernetes JSON command responses into normalized domain models.

Why this file exists:
Decouples raw JSON schema decoding and validation from CLI command execution, ensuring testability.

Responsibilities:
- Parse namespaces list.
- Parse nodes list with internal IP and role extraction.
- Parse pods list and compute restart sums.
- Parse deployments lists.
- Parse services lists with target port mapping.
- Parse events lists.

Used By:
- KubernetesCollector

Depends On:
- src.domain.metrics.kubernetes_metrics.KubernetesMetrics
- src.domain.exceptions.ValidationError
-------------------------------------------------------
"""

import json
from datetime import datetime, timezone
from typing import List
import structlog

from src.domain.exceptions import ValidationError
from src.domain.metrics.kubernetes_metrics import (
    ClusterInfo,
    DeploymentInfo,
    EventInfo,
    InvolvedObject,
    KubernetesMetrics,
    NamespaceInfo,
    NodeInfo,
    PodInfo,
    ServiceInfo,
    ServicePort,
)

logger = structlog.get_logger(__name__)


class KubernetesParser:
    """
    Why this class exists:
    A utility class containing static methods for parsing Kubernetes JSON elements.

    Responsibility:
    Converts Kubernetes command outputs to structured KubernetesMetrics.

    Who uses it:
    KubernetesCollector.
    """

    @classmethod
    def parse(
        cls,
        namespaces_json: str,
        nodes_json: str,
        pods_json: str,
        deployments_json: str,
        services_json: str,
        events_json: str,
        version_json: str,
        timestamp: datetime,
    ) -> KubernetesMetrics:
        """
        Parse Kubernetes command outputs into unified KubernetesMetrics.

        Raises:
            ValidationError: If all outputs are None.
        """
        if any(
            x is None
            for x in [
                namespaces_json,
                nodes_json,
                pods_json,
                deployments_json,
                services_json,
                events_json,
                version_json,
            ]
        ):
            raise ValidationError("Telemetry command outputs cannot be None.")

        # 1. Parse Cluster/Kubernetes version
        kubernetes_version = "unknown"
        api_server_version = None
        if version_json.strip():
            try:
                data = json.loads(version_json)
                if isinstance(data, dict):
                    if "serverVersion" in data and isinstance(data["serverVersion"], dict):
                        api_server_version = data["serverVersion"].get("gitVersion", "unknown")
                    if "clientVersion" in data and isinstance(data["clientVersion"], dict):
                        kubernetes_version = data["clientVersion"].get("gitVersion", "unknown")
                    if kubernetes_version == "unknown":
                        kubernetes_version = data.get("gitVersion", "unknown")
            except Exception as e:
                logger.debug("Failed parsing version JSON", error=str(e))

        cluster = ClusterInfo(
            kubernetes_version=kubernetes_version, api_server_version=api_server_version
        )

        # 2. Parse Namespaces
        namespaces: List[NamespaceInfo] = []
        if namespaces_json.strip():
            try:
                data = json.loads(namespaces_json)
                items = data.get("items", []) or []
                for item in items:
                    name = item.get("metadata", {}).get("name", "unknown")
                    status = item.get("status", {}).get("phase", "unknown")
                    labels = item.get("metadata", {}).get("labels", {}) or {}
                    namespaces.append(NamespaceInfo(name=name, status=status, labels=labels))
            except Exception as e:
                logger.debug("Failed parsing namespaces JSON", error=str(e))

        # 3. Parse Nodes
        nodes: List[NodeInfo] = []
        if nodes_json.strip():
            try:
                data = json.loads(nodes_json)
                items = data.get("items", []) or []
                for item in items:
                    metadata = item.get("metadata", {}) or {}
                    name = metadata.get("name", "unknown")
                    labels = metadata.get("labels", {}) or {}

                    roles = []
                    for k in labels.keys():
                        if k.startswith("node-role.kubernetes.io/"):
                            roles.append(k.split("/")[-1])

                    internal_ip = None
                    addresses = item.get("status", {}).get("addresses", []) or []
                    for addr in addresses:
                        if addr.get("type") == "InternalIP":
                            internal_ip = addr.get("address")
                            break

                    node_info = item.get("status", {}).get("nodeInfo", {}) or {}
                    os_image = node_info.get("osImage", "unknown")
                    kernel_version = node_info.get("kernelVersion", "unknown")
                    container_runtime = node_info.get("containerRuntimeVersion", "unknown")
                    kubelet_version = node_info.get("kubeletVersion", "unknown")

                    capacity = item.get("status", {}).get("capacity", {}) or {}
                    allocatable = item.get("status", {}).get("allocatable", {}) or {}

                    nodes.append(
                        NodeInfo(
                            name=name,
                            roles=roles,
                            labels=labels,
                            internal_ip=internal_ip,
                            os_image=os_image,
                            kernel_version=kernel_version,
                            container_runtime=container_runtime,
                            kubelet_version=kubelet_version,
                            capacity=capacity,
                            allocatable=allocatable,
                        )
                    )
            except Exception as e:
                logger.debug("Failed parsing nodes JSON", error=str(e))

        # 4. Parse Pods
        pods: List[PodInfo] = []
        if pods_json.strip():
            try:
                data = json.loads(pods_json)
                items = data.get("items", []) or []
                for item in items:
                    metadata = item.get("metadata", {}) or {}
                    namespace = metadata.get("namespace", "unknown")
                    pod_name = metadata.get("name", "unknown")
                    uid = metadata.get("uid", "unknown")
                    node_name = item.get("spec", {}).get("nodeName")

                    status = item.get("status", {}) or {}
                    phase = status.get("phase", "unknown")
                    pod_ip = status.get("podIP")
                    host_ip = status.get("hostIP")

                    start_time_str = status.get("startTime")
                    start_time = None
                    if start_time_str:
                        try:
                            clean_time = start_time_str.replace("Z", "+00:00")
                            start_time = datetime.fromisoformat(clean_time)
                        except ValueError:
                            pass

                    restart_count = 0
                    container_statuses = status.get("containerStatuses", []) or []
                    for cs in container_statuses:
                        restart_count += cs.get("restartCount", 0)

                    init_container_statuses = status.get("initContainerStatuses", []) or []
                    for ics in init_container_statuses:
                        restart_count += ics.get("restartCount", 0)

                    container_images = []
                    containers = item.get("spec", {}).get("containers", []) or []
                    for c in containers:
                        img = c.get("image")
                        if img:
                            container_images.append(img)
                    init_containers = item.get("spec", {}).get("initContainers", []) or []
                    for c in init_containers:
                        img = c.get("image")
                        if img:
                            container_images.append(img)

                    pods.append(
                        PodInfo(
                            namespace=namespace,
                            pod_name=pod_name,
                            uid=uid,
                            node_name=node_name,
                            phase=phase,
                            pod_ip=pod_ip,
                            host_ip=host_ip,
                            start_time=start_time,
                            restart_count=restart_count,
                            container_images=container_images,
                        )
                    )
            except Exception as e:
                logger.debug("Failed parsing pods JSON", error=str(e))

        # 5. Parse Deployments
        deployments: List[DeploymentInfo] = []
        if deployments_json.strip():
            try:
                data = json.loads(deployments_json)
                items = data.get("items", []) or []
                for item in items:
                    metadata = item.get("metadata", {}) or {}
                    namespace = metadata.get("namespace", "unknown")
                    name = metadata.get("name", "unknown")

                    spec = item.get("spec", {}) or {}
                    desired = spec.get("replicas", 1)

                    status = item.get("status", {}) or {}
                    available = status.get("availableReplicas", 0)
                    updated = status.get("updatedReplicas", 0)

                    deployments.append(
                        DeploymentInfo(
                            namespace=namespace,
                            deployment_name=name,
                            desired_replicas=desired,
                            available_replicas=available,
                            updated_replicas=updated,
                        )
                    )
            except Exception as e:
                logger.debug("Failed parsing deployments JSON", error=str(e))

        # 6. Parse Services
        services: List[ServiceInfo] = []
        if services_json.strip():
            try:
                data = json.loads(services_json)
                items = data.get("items", []) or []
                for item in items:
                    metadata = item.get("metadata", {}) or {}
                    namespace = metadata.get("namespace", "unknown")
                    name = metadata.get("name", "unknown")

                    spec = item.get("spec", {}) or {}
                    srv_type = spec.get("type", "ClusterIP")
                    cluster_ip = spec.get("clusterIP", "None")

                    external_ips = spec.get("externalIPs", []) or []
                    ingress = item.get("status", {}).get("loadBalancer", {}).get("ingress", []) or []
                    for ing in ingress:
                        ip = ing.get("ip") or ing.get("hostname")
                        if ip:
                            external_ips.append(ip)

                    ports = []
                    spec_ports = spec.get("ports", []) or []
                    for sp in spec_ports:
                        tp = sp.get("targetPort")
                        tp_str = str(tp) if tp is not None else None

                        ports.append(
                            ServicePort(
                                name=sp.get("name"),
                                port=sp.get("port"),
                                protocol=sp.get("protocol", "TCP"),
                                target_port=tp_str,
                            )
                        )

                    services.append(
                        ServiceInfo(
                            namespace=namespace,
                            service_name=name,
                            type=srv_type,
                            cluster_ip=cluster_ip,
                            external_ip=external_ips,
                            ports=ports,
                        )
                    )
            except Exception as e:
                logger.debug("Failed parsing services JSON", error=str(e))

        # 7. Parse Events
        events: List[EventInfo] = []
        if events_json.strip():
            try:
                data = json.loads(events_json)
                items = data.get("items", []) or []
                for item in items:
                    last_ts = (
                        item.get("lastTimestamp")
                        or item.get("eventTime")
                        or item.get("firstTimestamp")
                    )
                    if not last_ts:
                        continue
                    try:
                        clean_ts = last_ts.replace("Z", "+00:00")
                        ts = datetime.fromisoformat(clean_ts)
                    except ValueError:
                        ts = datetime.now(timezone.utc)

                    metadata = item.get("metadata", {}) or {}
                    namespace = metadata.get("namespace", "default")

                    obj = item.get("involvedObject", {}) or {}
                    inv = InvolvedObject(
                        kind=obj.get("kind", "unknown"),
                        name=obj.get("name", "unknown"),
                        namespace=obj.get("namespace"),
                    )

                    events.append(
                        EventInfo(
                            timestamp=ts,
                            namespace=namespace,
                            involved_object=inv,
                            reason=item.get("reason", "unknown"),
                            message=item.get("message", ""),
                            type=item.get("type", "Normal"),
                        )
                    )
            except Exception as e:
                logger.debug("Failed parsing events JSON", error=str(e))

        return KubernetesMetrics(
            cluster=cluster,
            namespaces=namespaces,
            nodes=nodes,
            pods=pods,
            deployments=deployments,
            services=services,
            events=events,
            timestamp=timestamp,
        )

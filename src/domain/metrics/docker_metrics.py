"""
-------------------------------------------------------
File:
docker_metrics.py

Purpose:
Domain model representing normalized Docker runtime telemetry.

Why this file exists:
Provides a strongly typed, virtualization-agnostic representation of container and volume metadata.

Responsibilities:
- Encapsulate container configurations: status, IDs, cpu/memory specs, mounts, networks, and volumes.

Used By:
- DockerParser
- DockerCollector

Notes:
This file belongs to the Domain Layer as it defines a core telemetry data structure.
-------------------------------------------------------
"""

from datetime import datetime
from typing import Dict, List, Optional
from pydantic import BaseModel, Field


class ContainerMount(BaseModel):
    """
    Why this class exists:
    Encapsulates container bind mount directories.
    """

    source: str = Field(description="Host directory source")
    destination: str = Field(description="Container mount destination")
    mode: str = Field(description="Permissions mode (e.g. rw)")
    rw: bool = Field(description="True if mount is writable")
    propagation: str = Field(description="Mount propagation settings")


class ContainerMetadata(BaseModel):
    """
    Why this class exists:
    Encapsulates static definitions and states for a container.
    """

    container_id: str = Field(description="Docker container ID hash")
    name: str = Field(description="Name of the container")
    image: str = Field(description="Docker image name tag")
    image_id: str = Field(description="Docker image digest/hash")
    created_time: datetime = Field(description="Timestamp of container creation")
    state: str = Field(description="State string (e.g. running)")
    status: str = Field(description="Status duration description")
    restart_count: int = Field(description="Number of container restarts")
    pid: Optional[int] = Field(None, description="Primary process ID")
    command: str = Field(description="Startup execution command")
    labels: Dict[str, str] = Field(default_factory=dict, description="Metadata tags/labels")
    mounts: List[ContainerMount] = Field(default_factory=list, description="Volume mounts")
    network_mode: str = Field(description="Container network configuration mode")


class ContainerStats(BaseModel):
    """
    Why this class exists:
    Encapsulates resource usages for a container.
    """

    container_id: str = Field(description="Docker container ID hash")
    name: str = Field(description="Container name")
    cpu_percentage: float = Field(description="CPU usage percentage")
    memory_usage_bytes: int = Field(description="Memory consumed in bytes")
    memory_limit_bytes: int = Field(description="Memory limit in bytes")
    memory_percentage: float = Field(description="Memory consumed percentage")
    network_rx_bytes: int = Field(description="Network bytes received")
    network_tx_bytes: int = Field(description="Network bytes sent")
    block_read_bytes: int = Field(description="Storage block bytes read")
    block_write_bytes: int = Field(description="Storage block bytes written")
    pids_count: int = Field(description="Number of processes running inside container")


class DockerNetwork(BaseModel):
    """
    Why this class exists:
    Encapsulates docker network properties.
    """

    network_id: str = Field(description="Docker network ID hash")
    name: str = Field(description="Docker network name")
    driver: str = Field(description="Network driver (e.g. bridge)")
    scope: str = Field(description="Network scope (e.g. local)")


class DockerVolume(BaseModel):
    """
    Why this class exists:
    Encapsulates docker volumes properties.
    """

    name: str = Field(description="Docker volume name")
    driver: str = Field(description="Volume driver name")
    mountpoint: Optional[str] = Field(None, description="Path where volume is mounted on host")


class DockerMetrics(BaseModel):
    """
    Why this class exists:
    Main container model for all collected Docker metrics.
    """

    containers: List[ContainerMetadata] = Field(
        default_factory=list, description="List of containers metadata"
    )
    stats: List[ContainerStats] = Field(
        default_factory=list, description="List of container resource usage statistics"
    )
    networks: List[DockerNetwork] = Field(
        default_factory=list, description="List of configured networks"
    )
    volumes: List[DockerVolume] = Field(
        default_factory=list, description="List of configured storage volumes"
    )
    timestamp: datetime = Field(description="UTC timestamp of when the metrics were captured")

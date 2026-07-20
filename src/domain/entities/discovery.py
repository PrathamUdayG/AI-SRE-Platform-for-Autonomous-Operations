# src/domain/entities/discovery.py
"""Domain entities representing discovered infrastructure snapshots."""

from datetime import datetime, timezone
from typing import List, Optional

from pydantic import BaseModel, Field


class CPUInfo(BaseModel):
    """Details about the server's CPU architecture and model."""

    model: str = Field(..., description="CPU model name")
    cores: int = Field(..., description="Number of logical CPU cores")
    sockets: int = Field(..., description="Number of physical sockets")
    threads_per_core: int = Field(..., description="Number of threads per CPU core")
    architecture: str = Field(..., description="CPU Architecture (e.g., x86_64)")


class MemoryInfo(BaseModel):
    """Details about the server's system memory (RAM)."""

    total_mb: float = Field(..., description="Total system memory in MB")
    used_mb: float = Field(..., description="Used system memory in MB")
    free_mb: float = Field(..., description="Free system memory in MB")
    shared_mb: float = Field(..., description="Shared system memory in MB")
    buff_cache_mb: float = Field(..., description="Buffer/cache memory in MB")
    available_mb: float = Field(..., description="Available system memory in MB")


class DiskInfo(BaseModel):
    """Details about a mounted filesystem storage disk."""

    device: str = Field(..., description="Filesystem device path, e.g. /dev/sda1")
    mount_point: str = Field(..., description="Directory mount point path, e.g. /")
    fstype: str = Field(..., description="Filesystem format type, e.g. ext4")
    total_gb: float = Field(..., description="Total capacity in GB")
    used_gb: float = Field(..., description="Used storage space in GB")
    free_gb: float = Field(..., description="Free/available storage space in GB")
    percentage: float = Field(..., description="Usage percentage (0 to 100)")


class NetworkInterfaceInfo(BaseModel):
    """Details about a system network interface card."""

    name: str = Field(..., description="Interface label, e.g. eth0")
    ip_addresses: List[str] = Field(
        default_factory=list, description="List of bound IP addresses"
    )
    mac_address: Optional[str] = Field(
        None, description="Hardware MAC address if available"
    )
    state: str = Field(..., description="Operational status, e.g. UP, DOWN")


class DiscoverySnapshot(BaseModel):
    """Domain model representing a single-point-in-time infrastructure discovery snapshot."""

    id: Optional[int] = Field(None, description="Unique primary key of this snapshot")
    server_id: int = Field(
        ..., description="Foreign key reference of the target server"
    )
    hostname: str = Field(..., description="Discovered system hostname")
    operating_system: str = Field(..., description="Discovered OS release string")
    kernel_version: str = Field(..., description="Discovered kernel build version")
    architecture: str = Field(..., description="Discovered CPU architecture")
    uptime: str = Field(..., description="Discovered system uptime duration")
    timezone: str = Field(..., description="Discovered timezone setting")
    cpu: CPUInfo = Field(..., description="Discovered CPU specifications")
    memory: MemoryInfo = Field(..., description="Discovered RAM allocation state")
    disks: List[DiskInfo] = Field(
        default_factory=list, description="Discovered storage partitions list"
    )
    network_interfaces: List[NetworkInterfaceInfo] = Field(
        default_factory=list,
        description="Discovered network interfaces configurations",
    )
    discovered_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        description="Timestamp when the discovery was conducted",
    )

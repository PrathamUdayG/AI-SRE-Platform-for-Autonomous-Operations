# src/presentation/api/schemas/discovery.py
"""Schemas for infrastructure discovery API requests and responses."""

from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, Field


class CPUResponse(BaseModel):
    """Schema for returning CPU configuration details."""

    model: str
    cores: int
    sockets: int
    threads_per_core: int
    architecture: str

    model_config = {"from_attributes": True}


class MemoryResponse(BaseModel):
    """Schema for returning memory usage details."""

    total_mb: float
    used_mb: float
    free_mb: float
    shared_mb: float
    buff_cache_mb: float
    available_mb: float

    model_config = {"from_attributes": True}


class DiskResponse(BaseModel):
    """Schema for returning mounted partition details."""

    device: str
    mount_point: str
    fstype: str
    total_gb: float
    used_gb: float
    free_gb: float
    percentage: float

    model_config = {"from_attributes": True}


class NetworkInterfaceResponse(BaseModel):
    """Schema for returning network interface configuration."""

    name: str
    ip_addresses: List[str]
    mac_address: Optional[str] = None
    state: str

    model_config = {"from_attributes": True}


class DiscoverySnapshotResponse(BaseModel):
    """Schema for returning a full infrastructure discovery snapshot."""

    id: int
    server_id: int
    hostname: str
    operating_system: str
    kernel_version: str
    architecture: str
    uptime: str
    timezone: str
    cpu: CPUResponse
    memory: MemoryResponse
    disks: List[DiskResponse]
    network_interfaces: List[NetworkInterfaceResponse]
    discovered_at: datetime

    model_config = {"from_attributes": True}

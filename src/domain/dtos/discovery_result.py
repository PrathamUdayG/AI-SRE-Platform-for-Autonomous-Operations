# src/domain/dtos/discovery_result.py
"""DiscoveryResult DTO to hold raw parsed system telemetry before it is mapped to entities."""

from datetime import datetime
from typing import List

from pydantic import BaseModel, Field

from src.domain.entities.discovery import (
    CPUInfo,
    DiskInfo,
    MemoryInfo,
    NetworkInterfaceInfo,
)


class DiscoveryResult(BaseModel):
    """Data Transfer Object representing a raw parsed discovery outcome."""

    server_id: int = Field(
        ..., description="Foreign key reference of the target server"
    )
    hostname: str = Field(..., description="Parsed system hostname")
    operating_system: str = Field(..., description="Parsed OS release string")
    kernel_version: str = Field(..., description="Parsed kernel version")
    architecture: str = Field(..., description="Parsed CPU architecture")
    uptime: str = Field(..., description="Parsed system uptime duration")
    timezone: str = Field(..., description="Parsed timezone setting")
    cpu: CPUInfo = Field(..., description="Parsed CPU specifications")
    memory: MemoryInfo = Field(..., description="Parsed memory details")
    disks: List[DiskInfo] = Field(
        default_factory=list, description="Parsed disks partitions list"
    )
    network_interfaces: List[NetworkInterfaceInfo] = Field(
        default_factory=list, description="Parsed network interfaces list"
    )
    discovered_at: datetime = Field(..., description="Time of discovery")

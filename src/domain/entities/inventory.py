# src/domain/entities/inventory.py
"""Inventory aggregate root entity representing a managed infrastructure asset."""

from datetime import datetime
from typing import Dict, List, Optional

from pydantic import BaseModel, Field

from src.domain.entities.discovery import (
    CPUInfo,
    DiskInfo,
    MemoryInfo,
    NetworkInterfaceInfo,
)
from src.domain.interfaces.connectors import ConnectorType


class InventoryMetadata(BaseModel):
    """Metadata tags and properties associated with the managed asset."""

    environment: Optional[str] = Field(
        default=None, description="e.g. production, staging, development"
    )
    owner: Optional[str] = Field(
        default=None,
        description="Team or individual responsible for this asset",
    )
    project: Optional[str] = Field(default=None, description="Associated project name")
    business_unit: Optional[str] = Field(
        default=None, description="Department or business unit name"
    )
    region: Optional[str] = Field(
        default=None,
        description="Physical or virtual cloud region, e.g. us-east-1",
    )
    datacenter: Optional[str] = Field(
        default=None, description="Specific hosting facility, e.g. dc-01"
    )
    role: Optional[str] = Field(
        default=None,
        description="Role within application, e.g. web-server, db-primary",
    )
    criticality: Optional[str] = Field(
        default=None,
        description="Criticality classification, e.g. high, medium, low",
    )
    connector_type: Optional[ConnectorType] = Field(
        default=None, description="The communication connector used"
    )
    tags: Dict[str, str] = Field(
        default_factory=dict, description="Extensible key-value metadata tags"
    )


class Inventory(BaseModel):
    """Inventory Aggregate Root representing a managed infrastructure asset."""

    id: Optional[int] = Field(
        default=None, description="Unique primary key of the inventory asset"
    )
    server_id: int = Field(
        ..., description="Foreign key reference of the target server"
    )
    hostname: str = Field(..., description="System hostname")
    operating_system: str = Field(..., description="System OS release string")
    kernel_version: str = Field(..., description="System kernel build version")
    architecture: str = Field(..., description="System CPU architecture")
    uptime: str = Field(..., description="System uptime duration")
    timezone: str = Field(..., description="System timezone setting")
    cpu: CPUInfo = Field(..., description="System CPU specifications")
    memory: MemoryInfo = Field(..., description="System RAM allocation state")
    disks: List[DiskInfo] = Field(
        default_factory=list, description="System storage partitions list"
    )
    network_interfaces: List[NetworkInterfaceInfo] = Field(
        default_factory=list, description="System network interfaces list"
    )
    last_discovered_at: datetime = Field(
        ..., description="Timestamp of the latest successful discovery run"
    )
    metadata: InventoryMetadata = Field(
        default_factory=lambda: InventoryMetadata(),
        description="Associated environment tag/owner metadata",
    )
    version: int = Field(
        default=1,
        description="Aggregate version counter for future history tracking",
    )

    model_config = {"from_attributes": True}

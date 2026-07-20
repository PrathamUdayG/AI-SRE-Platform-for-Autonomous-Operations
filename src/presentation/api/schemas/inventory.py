# src/presentation/api/schemas/inventory.py
"""Schemas for inventory management API requests and responses."""

from datetime import datetime
from typing import Dict, List, Optional

from pydantic import BaseModel, Field

from src.presentation.api.schemas.discovery import (
    CPUResponse,
    DiskResponse,
    MemoryResponse,
    NetworkInterfaceResponse,
)


class InventoryMetadataResponse(BaseModel):
    """Schema for returning inventory metadata tags."""

    environment: Optional[str] = None
    owner: Optional[str] = None
    project: Optional[str] = None
    business_unit: Optional[str] = None
    region: Optional[str] = None
    datacenter: Optional[str] = None
    role: Optional[str] = None
    criticality: Optional[str] = None
    connector_type: Optional[str] = None
    tags: Dict[str, str] = Field(default_factory=dict)

    model_config = {"from_attributes": True}


class InventoryResponse(BaseModel):
    """Schema for returning full inventory managed asset details."""

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
    last_discovered_at: datetime
    metadata: InventoryMetadataResponse
    version: int

    model_config = {"from_attributes": True}


class UpdateInventoryMetadataRequest(BaseModel):
    """Schema for updating metadata fields on a managed inventory asset."""

    environment: Optional[str] = Field(
        None, description="e.g. production, staging, development"
    )
    owner: Optional[str] = Field(None, description="Owner team or individual")
    project: Optional[str] = Field(None, description="Associated project")
    business_unit: Optional[str] = Field(None, description="Associated business unit")
    region: Optional[str] = Field(None, description="Region, e.g. us-east-1")
    datacenter: Optional[str] = Field(None, description="Datacenter name")
    role: Optional[str] = Field(None, description="Server role, e.g. web-server")
    criticality: Optional[str] = Field(
        None, description="Asset criticality rating, e.g. high, medium, low"
    )
    tags: Optional[Dict[str, str]] = Field(
        None, description="Dictionary of custom metadata tags to add/update"
    )

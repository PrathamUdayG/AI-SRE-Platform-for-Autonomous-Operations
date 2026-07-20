# src/domain/dtos/telemetry.py
"""DTOs for the telemetry collection framework."""

from datetime import datetime
from typing import Any, Dict

from pydantic import BaseModel, Field

from src.domain.entities.inventory import Inventory
from src.domain.entities.server import Server
from src.domain.interfaces.connectors import IConnector


class CollectionContext(BaseModel):
    """Execution context passed to telemetry collectors."""

    server: Server = Field(..., description="Target server registration")
    inventory: Inventory = Field(..., description="Authoritative inventory details")
    connector: IConnector = Field(..., description="Established connection channel")
    timestamp: datetime = Field(..., description="Timestamp of collection run")
    metadata: Dict[str, Any] = Field(
        default_factory=dict, description="Custom context metadata parameters"
    )

    model_config = {"arbitrary_types_allowed": True}


class RawMetric(BaseModel):
    """Raw metric data structure returned by collectors."""

    server_id: int = Field(..., description="Reference server ID")
    metric_type: str = Field(
        ..., description="e.g. cpu, memory, disk, network, process, service"
    )
    timestamp: datetime = Field(..., description="Time of collection")
    data: Dict[str, Any] = Field(
        default_factory=dict, description="Raw harvested telemetry key-values"
    )

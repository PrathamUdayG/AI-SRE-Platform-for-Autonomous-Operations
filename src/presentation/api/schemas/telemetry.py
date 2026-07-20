# src/presentation/api/schemas/telemetry.py
"""Schemas for telemetry collection API requests and responses."""

from datetime import datetime
from typing import Any, Dict

from pydantic import BaseModel, Field


class TelemetryResponse(BaseModel):
    """Schema for returning structured telemetry metrics details."""

    id: int = Field(..., description="Unique database record ID")
    server_id: int = Field(..., description="The registered server ID")
    metric_type: str = Field(
        ..., description="e.g. cpu, memory, disk, network, process, service"
    )
    timestamp: datetime = Field(..., description="Time of sample collection")
    data: Dict[str, Any] = Field(
        default_factory=dict,
        description="Nested key-value telemetry data payload",
    )

    model_config = {"from_attributes": True}

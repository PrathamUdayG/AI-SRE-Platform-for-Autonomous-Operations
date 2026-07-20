# src/domain/entities/telemetry.py
"""Domain entities for infrastructure telemetry."""

from datetime import datetime, timezone
from typing import Any, Dict, Optional

from pydantic import BaseModel, Field


class TelemetryMetric(BaseModel):
    """Domain entity representing a single persisted telemetry sample."""

    id: Optional[int] = Field(default=None, description="Unique primary key ID")
    server_id: int = Field(..., description="Associated server ID reference")
    metric_type: str = Field(
        ...,
        description="Type classification: cpu, memory, disk, network, process, service",
    )
    timestamp: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        description="Time the sample was collected",
    )
    data: Dict[str, Any] = Field(
        default_factory=dict,
        description="Collected metrics key-value payload measurements",
    )

    model_config = {"from_attributes": True}

# src/presentation/api/schemas/monitoring.py
"""API response schemas for health and monitoring endpoints."""

from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, Field


class FindingResponse(BaseModel):
    """Pydantic model representing a health finding result."""

    category: str = Field(..., description="E.g. CPU, Memory, Disk, Service")
    severity: str = Field(..., description="Severity state: WARNING, CRITICAL")
    metric: str = Field(..., description="The telemetry metric string name")
    threshold: float = Field(..., description="Limit threshold evaluated against")
    actual_value: float = Field(..., description="The actual telemetry reading")
    message: str = Field(..., description="Detail message describing findings")
    recommendation: str = Field(..., description="Suggested resolution guidance")

    model_config = {"from_attributes": True}


class ServerHealthResponse(BaseModel):
    """Pydantic model representing overall Server health assessment response."""

    id: Optional[int] = Field(None, description="Assessment database primary key")
    server_id: int = Field(..., description="Unique ID of evaluated host")
    overall_status: str = Field(..., description="HEALTHY, DEGRADED, UNHEALTHY")
    health_score: float = Field(..., description="Calculated aggregate health score")
    findings: List[FindingResponse] = Field(
        default_factory=list, description="List of rule violations detected"
    )
    evaluation_timestamp: datetime = Field(
        ..., description="Timestamp when evaluation was executed"
    )

    model_config = {"from_attributes": True}

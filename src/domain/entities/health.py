# src/domain/entities/health.py
"""Domain entities representing health evaluations and findings."""

from datetime import datetime, timezone
from typing import List, Optional

from pydantic import BaseModel, Field


class Finding(BaseModel):
    """Domain model representing a single rule evaluation finding."""

    id: Optional[int] = Field(
        default=None, description="Unique database ID for this finding"
    )
    category: str = Field(
        ..., description="Resource category: e.g. CPU, Memory, Disk, Service"
    )
    severity: str = Field(..., description="Finding severity: INFO, WARNING, CRITICAL")
    metric: str = Field(..., description="The metric name evaluated")
    threshold: float = Field(
        ..., description="The configured threshold evaluated against"
    )
    actual_value: float = Field(..., description="The observed value")
    message: str = Field(..., description="Descriptive summary of the finding")
    recommendation: str = Field(
        ..., description="Actionable recommendation to resolve the issue"
    )

    model_config = {"from_attributes": True}


class ServerHealth(BaseModel):
    """Aggregate root representing overall server health assessment."""

    id: Optional[int] = Field(
        default=None, description="Unique database ID for health assessment"
    )
    server_id: int = Field(..., description="Associated server ID")
    overall_status: str = Field(
        ..., description="Overall health state: HEALTHY, DEGRADED, UNHEALTHY"
    )
    health_score: float = Field(
        ..., description="Aggregated health score between 0.0 and 100.0"
    )
    findings: List[Finding] = Field(
        default_factory=list,
        description="Collection of health violations found during evaluation",
    )
    evaluation_timestamp: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        description="Evaluation timestamp",
    )

    model_config = {"from_attributes": True}

# src/presentation/api/v1/metrics.py
"""API routes for Metric resources."""

from datetime import datetime, timezone
from typing import Dict, Optional

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field

from src.application.services.metric_service import MetricService
from src.infrastructure.di import get_metric_service


# ---------- Request/Response Schemas ----------
class MetricCreate(BaseModel):
    """Schema for creating a new metric (incoming JSON)."""

    name: str = Field(..., description="Metric name, e.g. 'cpu.usage'")
    value: float = Field(..., description="Numeric value")
    service: str = Field(..., description="Service that produced the metric")
    timestamp: Optional[datetime] = Field(
        None, description="Optional timestamp (defaults to now)"
    )
    tags: Dict[str, str] = Field(default_factory=dict, description="Key-value labels")

    model_config = {
        "json_schema_extra": {
            "example": {
                "name": "cpu.usage",
                "value": 45.2,
                "service": "api-gateway",
                "tags": {"environment": "prod", "region": "us-east"},
            }
        }
    }


class MetricResponse(BaseModel):
    """Schema for returning a metric (outgoing JSON)."""

    id: int
    name: str
    value: float
    timestamp: datetime
    service: str
    tags: Dict[str, str]

    model_config = {
        "from_attributes": True
    }  # allows conversion from ORM/domain objects


# ---------- Router ----------
router = APIRouter(prefix="/metrics", tags=["metrics"])


@router.post("/", response_model=MetricResponse, status_code=status.HTTP_201_CREATED)
async def create_metric(
    metric_data: MetricCreate,
    service: MetricService = Depends(get_metric_service),
) -> MetricResponse:
    """Save a new metric to the database."""
    saved_metric = await service.create_metric(
        name=metric_data.name,
        value=metric_data.value,
        service=metric_data.service,
        timestamp=metric_data.timestamp or datetime.now(timezone.utc),
        tags=metric_data.tags,
    )
    return MetricResponse.model_validate(saved_metric)


@router.get("/{metric_id}", response_model=MetricResponse)
async def get_metric(
    metric_id: int,
    service: MetricService = Depends(get_metric_service),
) -> MetricResponse:
    """Retrieve a single metric by its ID."""
    metric = await service.get_metric_by_id(metric_id)
    if not metric:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Metric not found"
        )
    return MetricResponse.model_validate(metric)

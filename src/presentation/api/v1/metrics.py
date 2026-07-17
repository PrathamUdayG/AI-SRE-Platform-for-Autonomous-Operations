from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from datetime import datetime, timezone
from typing import Dict, Optional
from pydantic import BaseModel, Field

from src.infrastructure.database import get_db
from src.infrastructure.persistence.repositories import MetricRepository
from src.domain.entities.metric import Metric

# ---------- Request/Response Schemas ----------
class MetricCreate(BaseModel):
    """Schema for creating a new metric (incoming JSON)."""
    name: str = Field(..., description="Metric name, e.g. 'cpu.usage'")
    value: float = Field(..., description="Numeric value")
    service: str = Field(..., description="Service that produced the metric")
    timestamp: Optional[datetime] = Field(None, description="Optional timestamp (defaults to now)")
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

    model_config = {"from_attributes": True}  # allows conversion from ORM/domain objects


# ---------- Router ----------
router = APIRouter(prefix="/metrics", tags=["metrics"])


@router.post("/", response_model=MetricResponse, status_code=status.HTTP_201_CREATED)
async def create_metric(metric_data: MetricCreate, db: AsyncSession = Depends(get_db)):
    """
    Save a new metric to the database.
    """
    # 1. Convert the incoming Pydantic model to your domain entity
    metric = Metric(
        name=metric_data.name,
        value=metric_data.value,
        service=metric_data.service,
        timestamp=metric_data.timestamp or datetime.now(timezone.utc),
        tags=metric_data.tags,
    )

    # 2. Instantiate the repository with the current DB session
    repo = MetricRepository(db)

    # 3. Save – this commits to the database and returns the saved entity (with ID)
    saved_metric = await repo.save(metric)

    # 4. Convert to the response schema and return
    return MetricResponse.model_validate(saved_metric)


@router.get("/{metric_id}", response_model=MetricResponse)
async def get_metric(metric_id: int, db: AsyncSession = Depends(get_db)):
    """
    Retrieve a single metric by its ID.
    """
    repo = MetricRepository(db)
    metric = await repo.get_by_id(metric_id)

    if not metric:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Metric not found")

    return MetricResponse.model_validate(metric)
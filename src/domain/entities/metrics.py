from datetime import datetime, timezone
from typing import Optional, Dict
from pydantic import BaseModel, Field


class Metric(BaseModel):
    """Domain entity representing a single time‑series metric."""
    id: Optional[int] = None
    name: str = Field(..., description="Metric name, e.g. 'cpu.usage'")
    value: float = Field(..., description="Numeric value")
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    service: str = Field(..., description="Service that produced the metric")
    tags: Dict[str, str] = Field(default_factory=dict, description="Key‑value labels")

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
"""
What This File Does
1. Defines the Structure of a Metric
python
class Metric(BaseModel):
    id: Optional[int] = None          # Unique ID (auto-generated)
    name: str                         # What metric? e.g., "cpu.usage"
    value: float                      # The actual number
    timestamp: datetime               # When it happened
    service: str                      # Which service produced it
    tags: Dict[str, str]              # Extra labels (like "environment: prod")
2. Ensures Data Quality (Validation)
Pydantic automatically checks that:

name must be text (not a number)

value must be a number (not text)

timestamp must be a valid date/time

service must be text

tags must be key-value pairs
"""
# src/domain/dtos/monitoring.py
"""DTOs for monitoring and rule evaluations."""

from datetime import datetime
from typing import Any, Dict

from pydantic import BaseModel, Field

from src.domain.entities.inventory import Inventory
from src.domain.entities.telemetry import TelemetryMetric


class EvaluationContext(BaseModel):
    """Context passed to all health rules for evaluation."""

    inventory: Inventory = Field(
        ..., description="Inventory profile details of the target server"
    )
    latest_telemetry: Dict[str, TelemetryMetric] = Field(
        ...,
        description="Latest telemetry snapshots mapped by their metric type key",
    )
    timestamp: datetime = Field(
        ..., description="Timestamp of the current evaluation cycle run"
    )
    metadata: Dict[str, Any] = Field(
        default_factory=dict,
        description="Optional execution context parameters",
    )

# src/application/services/metric_service.py
"""Application Service representing the Metrics use cases."""

from datetime import datetime, timezone
from typing import Dict, List, Optional

import structlog

from src.domain.entities.metric import Metric
from src.domain.exceptions import ValidationError
from src.domain.repositories.metric_repository import MetricRepository

logger = structlog.get_logger(__name__)


class MetricService:
    """Application Service handling Metric operations."""

    def __init__(self, repository: MetricRepository):
        self.repository = repository

    async def create_metric(
        self,
        name: str,
        value: float,
        service: str,
        timestamp: Optional[datetime] = None,
        tags: Optional[Dict[str, str]] = None,
    ) -> Metric:
        """Validates and saves a new metric in the platform."""
        logger.info("Creating new metric", name=name, service=service)

        # Validate inputs
        if not name or len(name.strip()) == 0:
            raise ValidationError("Metric name cannot be empty.")
        if not service or len(service.strip()) == 0:
            raise ValidationError("Service name cannot be empty.")

        # Create domain entity
        metric = Metric(
            name=name,
            value=value,
            service=service,
            timestamp=timestamp or datetime.now(timezone.utc),
            tags=tags or {},
        )

        # Save using repository
        saved_metric = await self.repository.save(metric)
        logger.info("Metric saved successfully", metric_id=saved_metric.id, name=name)

        return saved_metric

    async def get_metric_by_id(self, metric_id: int) -> Optional[Metric]:
        """Retrieves a metric by its unique ID."""
        logger.info("Retrieving metric by ID", metric_id=metric_id)
        return await self.repository.get_by_id(metric_id)

    async def get_all_metrics(self, limit: int = 100, offset: int = 0) -> List[Metric]:
        """Retrieves all metrics."""
        logger.info("Retrieving all metrics", limit=limit, offset=offset)
        return await self.repository.get_all(limit=limit, offset=offset)

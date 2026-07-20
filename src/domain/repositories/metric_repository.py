# src/domain/repositories/metric_repository.py
"""Boundary interface between the application layer and the metrics persistence layer."""

from abc import abstractmethod
from typing import List, Optional

from src.domain.entities.metric import Metric
from src.domain.interfaces.repositories import IRepository


class MetricRepository(IRepository[Metric]):
    """Interface for Metric repository operations."""

    @abstractmethod
    async def save(self, entity: Metric) -> Metric:
        """Insert a new metric into the database."""
        pass

    @abstractmethod
    async def get_by_id(self, entity_id: int) -> Optional[Metric]:
        """Retrieve a metric by its primary key."""
        pass

    @abstractmethod
    async def get_all(self, limit: int = 100, offset: int = 0) -> List[Metric]:
        """Retrieve all metrics."""
        pass

    @abstractmethod
    async def delete(self, entity_id: int) -> bool:
        """Delete a metric by its ID."""
        pass

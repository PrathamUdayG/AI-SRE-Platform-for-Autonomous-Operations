# src/domain/repositories/timeline_repository.py
"""Domain interface contract for TimelineRepository operations."""

from abc import abstractmethod
from typing import List

from src.domain.entities.incident import TimelineEntry
from src.domain.interfaces.repositories import IRepository


class TimelineRepository(IRepository[TimelineEntry]):
    """Interface for TimelineEntry database storage and history lookup."""

    @abstractmethod
    async def get_by_incident_id(self, incident_id: int) -> List[TimelineEntry]:
        """Fetch chronological SRE timeline events for an incident, sorted ascending/descending."""
        pass

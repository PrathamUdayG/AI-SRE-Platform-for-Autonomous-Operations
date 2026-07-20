# src/domain/repositories/incident_repository.py
"""Domain interface contract for IncidentRepository operations."""

from abc import abstractmethod
from typing import List

from src.domain.entities.incident import Incident
from src.domain.interfaces.repositories import IRepository


class IncidentRepository(IRepository[Incident]):
    """Interface for Incident database storage and querying."""

    @abstractmethod
    async def get_by_server_id(self, server_id: int) -> List[Incident]:
        """Fetch all SRE incidents associated with a server."""
        pass

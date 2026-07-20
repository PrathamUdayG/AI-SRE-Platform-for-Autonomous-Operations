# src/domain/repositories/health_repository.py
"""Domain interface contract for HealthRepository operations."""

from abc import abstractmethod
from typing import List, Optional

from src.domain.entities.health import ServerHealth
from src.domain.interfaces.repositories import IRepository


class HealthRepository(IRepository[ServerHealth]):
    """Interface for ServerHealth database storage and querying."""

    @abstractmethod
    async def get_latest_by_server_id(self, server_id: int) -> Optional[ServerHealth]:
        """Fetch the most recent health assessment for a server."""
        pass

    @abstractmethod
    async def get_history_by_server_id(
        self, server_id: int, limit: int = 100
    ) -> List[ServerHealth]:
        """Fetch health assessment history for a server, ordered by timestamp desc."""
        pass

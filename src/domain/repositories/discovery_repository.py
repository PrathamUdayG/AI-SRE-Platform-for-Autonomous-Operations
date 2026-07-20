# src/domain/repositories/discovery_repository.py
"""Domain interface for Discovery Snapshot repository operations."""

from abc import abstractmethod
from typing import Optional

from src.domain.entities.discovery import DiscoverySnapshot
from src.domain.interfaces.repositories import IRepository


class DiscoveryRepository(IRepository[DiscoverySnapshot]):
    """Interface for Discovery Snapshot repository operations."""

    @abstractmethod
    async def get_latest_by_server_id(
        self, server_id: int
    ) -> Optional[DiscoverySnapshot]:
        """Retrieve the latest discovery snapshot for a given server."""
        pass

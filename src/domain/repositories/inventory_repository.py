# src/domain/repositories/inventory_repository.py
"""Domain interface for Inventory repository operations."""

from abc import abstractmethod
from typing import List, Optional

from src.domain.entities.inventory import Inventory
from src.domain.interfaces.repositories import IRepository


class InventoryRepository(IRepository[Inventory]):
    """Interface for Inventory repository operations."""

    @abstractmethod
    async def get_by_server_id(self, server_id: int) -> Optional[Inventory]:
        """Retrieve the inventory record for a given server."""
        pass

    @abstractmethod
    async def search(self, query_str: str) -> List[Inventory]:
        """Search inventory records by hostname, OS, metadata environment, role, etc."""
        pass

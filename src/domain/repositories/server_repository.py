# src/domain/repositories/server_repository.py
# Why: This file defines the ServerRepository interface extending IRepository.
# It acts as the boundary interface between the application layer and the
# database persistence layer, in accordance with Clean Architecture and SOLID principles.

from abc import abstractmethod
from typing import Optional

from src.domain.entities.server import Server
from src.domain.interfaces.repositories import IRepository


class ServerRepository(IRepository[Server]):
    """Interface for Server repository operations."""

    @abstractmethod
    async def get_by_hostname(self, hostname: str) -> Optional[Server]:
        """Retrieve a server by its hostname."""
        pass

    @abstractmethod
    async def get_by_ip(self, ip_address: str) -> Optional[Server]:
        """Retrieve a server by its IP address."""
        pass

    @abstractmethod
    async def exists(self, hostname: str, ip_address: str) -> bool:
        """Check if a server with the given hostname or IP already exists."""
        pass

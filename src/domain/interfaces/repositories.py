from abc import ABC, abstractmethod
from typing import Any, Optional


class IInfrastructureRepository(ABC):
    @abstractmethod
    async def get_by_id(self, resource_id: str) -> Optional[Any]:
        pass

    @abstractmethod
    async def save(self, entity: Any) -> None:
        pass


class IIncidentRepository(ABC):
    @abstractmethod
    async def get_by_id(self, incident_id: str) -> Optional[Any]:
        pass

    @abstractmethod
    async def save(self, entity: Any) -> None:
        pass

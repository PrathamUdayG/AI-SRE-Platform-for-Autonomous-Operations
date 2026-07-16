from abc import ABC, abstractmethod
from typing import Any, Dict


class IHostConnector(ABC):
    @abstractmethod
    async def execute_command(self, command: str) -> Dict[str, Any]:
        pass


class ICloudProviderConnector(ABC):
    @abstractmethod
    async def get_instance_status(self, instance_id: str) -> str:
        pass

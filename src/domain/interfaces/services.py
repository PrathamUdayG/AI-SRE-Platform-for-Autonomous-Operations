from abc import ABC, abstractmethod
from typing import Any, Dict


class IMonitoringService(ABC):
    @abstractmethod
    async def fetch_metrics(self, resource_id: str) -> Dict[str, Any]:
        pass


class IExecutionService(ABC):
    @abstractmethod
    async def execute_remediation(self, plan: Any) -> Dict[str, Any]:
        pass

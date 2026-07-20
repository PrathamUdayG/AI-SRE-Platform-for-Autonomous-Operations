# src/domain/repositories/telemetry_repository.py
"""Domain interface contract for TelemetryRepository operations."""

from abc import abstractmethod
from typing import List, Optional

from src.domain.entities.telemetry import TelemetryMetric
from src.domain.interfaces.repositories import IRepository


class TelemetryRepository(IRepository[TelemetryMetric]):
    """Interface for Telemetry database storage and querying."""

    @abstractmethod
    async def get_latest_by_server_id(
        self, server_id: int, metric_type: str
    ) -> Optional[TelemetryMetric]:
        """Fetch the most recent telemetry metric for a server and type."""
        pass

    @abstractmethod
    async def get_history_by_server_id(
        self, server_id: int, metric_type: str, limit: int = 100
    ) -> List[TelemetryMetric]:
        """Fetch telemetry history list for a server and type, ordered by timestamp desc."""
        pass

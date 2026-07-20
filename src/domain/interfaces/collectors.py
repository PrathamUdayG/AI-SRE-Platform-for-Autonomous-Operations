# src/domain/interfaces/collectors.py
"""Domain interface contracts for metric collectors."""

from abc import ABC, abstractmethod

from src.domain.dtos.telemetry import CollectionContext, RawMetric


class IMetricCollector(ABC):
    """Abstract base contract for all system telemetry collectors."""

    @abstractmethod
    async def collect(self, context: CollectionContext) -> RawMetric:
        """Harvest telemetry measurements using the provided execution context."""
        pass


class ICPUCollector(IMetricCollector, ABC):
    """Interface contract for CPU metric collection."""

    pass


class IMemoryCollector(IMetricCollector, ABC):
    """Interface contract for Memory metric collection."""

    pass


class IDiskCollector(IMetricCollector, ABC):
    """Interface contract for Filesystem and Disk usage metric collection."""

    pass


class INetworkCollector(IMetricCollector, ABC):
    """Interface contract for network traffic metric collection."""

    pass


class IProcessCollector(IMetricCollector, ABC):
    """Interface contract for process list and resource usage metric collection."""

    pass


class IServiceCollector(IMetricCollector, ABC):
    """Interface contract for active services metric collection."""

    pass

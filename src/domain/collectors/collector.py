"""
-------------------------------------------------------
File:
collector.py

Purpose:
Defines the abstract collector interface.

Why this file exists:
Every future collector implements this interface, ensuring they all follow the same execute contract.

Responsibilities:
- Define the contract for collector execution

Used By:
- CPU Collector
- Memory Collector
- Disk Collector
- Future Collectors

Notes:
This file belongs to the Domain Layer because it defines the abstraction/contract for collectors.
-------------------------------------------------------
"""

from abc import ABC, abstractmethod

from src.domain.collectors.collector_result import CollectorResult
from src.domain.interfaces.connectors import ICommandExecutor


class Collector(ABC):
    """
    Why this class exists:
    Serves as the abstract base class for all system collectors.

    Responsibility:
    Enforce a common execution interface.

    Who uses it:
    Concrete collectors and the runner/orchestrator.

    Why it belongs in this layer:
    It defines a core domain contract independent of any specific OS or tool implementation.
    """

    @property
    @abstractmethod
    def name(self) -> str:
        """
        Return the name of the collector.

        Returns:
            str: The collector name.
        """
        pass

    @property
    @abstractmethod
    def metric_type(self) -> str:
        """
        Return the type of metric this collector processes.

        Returns:
            str: The metric type name.
        """
        pass

    @abstractmethod
    async def collect(self, executor: ICommandExecutor) -> CollectorResult:
        """
        Execute the telemetry collection process using the provided executor and return a standardized result.

        Args:
            executor (ICommandExecutor): The command executor to run Linux commands.

        Returns:
            CollectorResult: The standardized telemetry result.
        """
        pass

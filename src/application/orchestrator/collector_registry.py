"""
-------------------------------------------------------
File:
collector_registry.py

Purpose:
A central registry for managing metric collectors.

Why this file exists:
Allows collectors to be dynamically plugged into or unplugged from the agent at runtime. It decouples the runner/orchestration layer from knowing about any specific collector implementations.

Responsibilities:
- Register unique collectors and reject duplicates.
- Retrieve registered collectors by name.
- Remove collectors from registry.
- Provide lists of all registered collectors.

Used By:
- CollectorOrchestrator
- Agent Bootstrap

Depends On:
- src.domain.collectors.collector.Collector
- src.domain.exceptions.ConflictError
- src.domain.exceptions.NotFoundError
-------------------------------------------------------
"""

from typing import Dict, List
import structlog

from src.domain.collectors.collector import Collector
from src.domain.exceptions import ConflictError, NotFoundError

logger = structlog.get_logger(__name__)


class CollectorRegistry:
    """
    Why this class exists:
    Maintains a runtime directory of telemetry collectors.

    Responsibility:
    Safeguards unique collector additions, lookups, and listing operations.

    Who uses it:
    Orchestrator to fetch active collectors, bootstrap to register them.
    """

    def __init__(self) -> None:
        """Initialize an empty collector registry."""
        self._collectors: Dict[str, Collector] = {}

    def register(self, collector: Collector) -> None:
        """
        Register a new collector instance.

        Args:
            collector (Collector): The collector instance to register.

        Raises:
            ConflictError: If a collector with the same name is already registered.
        """
        name = collector.name
        if name in self._collectors:
            logger.warning("Duplicate registration attempted", collector=name)
            raise ConflictError(f"Collector '{name}' is already registered.")

        self._collectors[name] = collector
        logger.info("Collector registered successfully", collector=name, metric_type=collector.metric_type)

    def unregister(self, name: str) -> None:
        """
        Remove a collector from the registry.

        Args:
            name (str): The name of the collector to remove.

        Raises:
            NotFoundError: If the collector is not currently registered.
        """
        if name not in self._collectors:
            logger.warning("Unregister attempted for missing collector", collector=name)
            raise NotFoundError(f"Collector '{name}' is not registered.")

        del self._collectors[name]
        logger.info("Collector unregistered successfully", collector=name)

    def get(self, name: str) -> Collector:
        """
        Retrieve a registered collector by its name.

        Args:
            name (str): Collector name to lookup.

        Returns:
            Collector: The registered collector instance.

        Raises:
            NotFoundError: If no collector matches the provided name.
        """
        if name not in self._collectors:
            raise NotFoundError(f"Collector '{name}' is not registered.")
        return self._collectors[name]

    def list(self) -> List[Collector]:
        """
        List all registered collectors.

        Returns:
            List[Collector]: List of collector instances.
        """
        return list(self._collectors.values())

    def exists(self, name: str) -> bool:
        """
        Check if a collector is registered.

        Args:
            name (str): Collector name.

        Returns:
            bool: True if registered, False otherwise.
        """
        return name in self._collectors

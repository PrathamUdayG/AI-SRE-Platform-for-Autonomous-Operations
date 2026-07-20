# src/infrastructure/telemetry/collector_registry.py
"""Registry to manage and look up telemetry collectors dynamically."""

from typing import Dict, List

import structlog

from src.domain.interfaces.collectors import IMetricCollector

logger = structlog.get_logger(__name__)


class CollectorRegistry:
    """Registry keeping track of IMetricCollector instances mapped by metric type."""

    _registry: Dict[str, IMetricCollector] = {}

    @classmethod
    def register(cls, metric_type: str, collector: IMetricCollector) -> None:
        """Register a new collector instance for the given metric type."""
        logger.info("Registering metric collector", type=metric_type)
        cls._registry[metric_type] = collector

    @classmethod
    def get_collector(cls, metric_type: str) -> IMetricCollector:
        """Fetch the registered collector for a given metric type."""
        if metric_type not in cls._registry:
            raise ValueError(f"No collector registered for metric type: {metric_type}")
        return cls._registry[metric_type]

    @classmethod
    def get_all_types(cls) -> List[str]:
        """Get list of all registered metric types."""
        return list(cls._registry.keys())

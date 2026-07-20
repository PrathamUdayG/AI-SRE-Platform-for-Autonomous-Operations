# src/domain/interfaces/rules.py
"""Domain interface contracts for health and monitoring rules."""

from abc import ABC, abstractmethod
from typing import Optional

from src.domain.dtos.monitoring import EvaluationContext
from src.domain.entities.health import Finding


class IMonitoringRule(ABC):
    """Abstract base contract for all health evaluation rules."""

    @property
    @abstractmethod
    def rule_id(self) -> str:
        """Unique ID identifier for the rule."""
        pass

    @abstractmethod
    def evaluate(self, context: EvaluationContext) -> Optional[Finding]:
        """Evaluate the rule against the context.

        Returns:
            Optional[Finding]: Finding object if a violation is detected, otherwise None.
        """
        pass


class ICPURule(IMonitoringRule, ABC):
    """Contract for CPU health evaluation rules."""

    pass


class IMemoryRule(IMonitoringRule, ABC):
    """Contract for Memory health evaluation rules."""

    pass


class IDiskRule(IMonitoringRule, ABC):
    """Contract for Disk and partition usage health rules."""

    pass


class INetworkRule(IMonitoringRule, ABC):
    """Contract for network throughput/state health rules."""

    pass


class IServiceRule(IMonitoringRule, ABC):
    """Contract for active service state health rules."""

    pass

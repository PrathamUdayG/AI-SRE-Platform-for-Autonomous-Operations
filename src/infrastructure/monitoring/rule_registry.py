# src/infrastructure/monitoring/rule_registry.py
"""Registry to manage and retrieve active monitoring evaluation rules."""

from typing import List

import structlog

from src.domain.interfaces.rules import IMonitoringRule

logger = structlog.get_logger(__name__)


class RuleRegistry:
    """Registry maintaining a list of active IMonitoringRule instances."""

    _rules: List[IMonitoringRule] = []

    @classmethod
    def register(cls, rule: IMonitoringRule) -> None:
        """Register a health evaluation rule."""
        logger.info("Registering health rule", rule_id=rule.rule_id)
        cls._rules.append(rule)

    @classmethod
    def get_rules(cls) -> List[IMonitoringRule]:
        """Get all registered evaluation rules."""
        return cls._rules

# src/infrastructure/monitoring/rules.py
"""Concrete implementations of health monitoring rules."""

from typing import Optional

from src.domain.dtos.monitoring import EvaluationContext
from src.domain.entities.health import Finding
from src.domain.interfaces.rules import (
    ICPURule,
    IDiskRule,
    IMemoryRule,
    INetworkRule,
    IServiceRule,
)
from src.infrastructure.config.settings import settings
from src.infrastructure.monitoring.rule_registry import RuleRegistry


class CPURule(ICPURule):
    """Rule to evaluate CPU usage against configured threshold."""

    def __init__(self, threshold: Optional[float] = None):
        self.threshold = threshold or settings.monitoring.cpu_threshold_pct

    @property
    def rule_id(self) -> str:
        return "rule.cpu.utilization"

    def evaluate(self, context: EvaluationContext) -> Optional[Finding]:
        metric = context.latest_telemetry.get("cpu")
        if not metric or "usage_percent" not in metric.data:
            return None

        val = float(metric.data["usage_percent"])
        if val > self.threshold:
            return Finding(
                category="CPU",
                severity="CRITICAL" if val > 90.0 else "WARNING",
                metric="cpu.usage_percent",
                threshold=self.threshold,
                actual_value=val,
                message=f"CPU utilization is high: {val}% (threshold: {self.threshold}%)",
                recommendation="Scale cpu resources or inspect top resource consuming processes.",
            )
        return None


class MemoryRule(IMemoryRule):
    """Rule to evaluate RAM memory usage against configured threshold."""

    def __init__(self, threshold: Optional[float] = None):
        self.threshold = threshold or settings.monitoring.memory_threshold_pct

    @property
    def rule_id(self) -> str:
        return "rule.memory.utilization"

    def evaluate(self, context: EvaluationContext) -> Optional[Finding]:
        metric = context.latest_telemetry.get("memory")
        if not metric or "usage_percent" not in metric.data:
            return None

        val = float(metric.data["usage_percent"])
        if val > self.threshold:
            return Finding(
                category="Memory",
                severity="CRITICAL" if val > 95.0 else "WARNING",
                metric="memory.usage_percent",
                threshold=self.threshold,
                actual_value=val,
                message=f"Memory utilization is high: {val}% (threshold: {self.threshold}%)",
                recommendation="Check for process memory leaks or upgrade system memory capacity.",
            )
        return None


class DiskRule(IDiskRule):
    """Rule to evaluate disk usage capacity across partitions."""

    def __init__(self, threshold: Optional[float] = None):
        self.threshold = threshold or settings.monitoring.disk_threshold_pct

    @property
    def rule_id(self) -> str:
        return "rule.disk.utilization"

    def evaluate(self, context: EvaluationContext) -> Optional[Finding]:
        metric = context.latest_telemetry.get("disk")
        if not metric or "partitions" not in metric.data:
            return None

        partitions = metric.data["partitions"]
        for part in partitions:
            val = float(part.get("usage_percent", 0.0))
            mount = part.get("mount_point", "/")
            if val > self.threshold:
                return Finding(
                    category="Disk",
                    severity="CRITICAL" if val > 95.0 else "WARNING",
                    metric=f"disk.usage_percent:{mount}",
                    threshold=self.threshold,
                    actual_value=val,
                    message=f"Disk partition '{mount}' is near capacity: {val}% (threshold: {self.threshold}%)",
                    recommendation=f"Clear space on mount point {mount} or expand block storage partition.",
                )
        return None


class NetworkRule(INetworkRule):
    """Rule to verify network interface health and activity."""

    @property
    def rule_id(self) -> str:
        return "rule.network.interfaces"

    def evaluate(self, context: EvaluationContext) -> Optional[Finding]:
        metric = context.latest_telemetry.get("network")
        if not metric or "interfaces" not in metric.data:
            return None

        interfaces = metric.data["interfaces"]
        # If no active interface is running
        if not interfaces:
            return Finding(
                category="Network",
                severity="CRITICAL",
                metric="network.active_interfaces",
                threshold=1.0,
                actual_value=0.0,
                message="No active network interfaces reported.",
                recommendation="Inspect physical network link status and network configurations.",
            )
        return None


class ServiceRule(IServiceRule):
    """Rule to verify critical service states based on server metadata role."""

    @property
    def rule_id(self) -> str:
        return "rule.services.state"

    def evaluate(self, context: EvaluationContext) -> Optional[Finding]:
        metric = context.latest_telemetry.get("service")
        if not metric or "services" not in metric.data:
            return None

        role = (
            context.inventory.metadata.role.lower()
            if context.inventory.metadata and context.inventory.metadata.role
            else ""
        )
        services = metric.data["services"]
        running_names = {s.get("name", "").lower() for s in services}

        # Check critical services based on role
        if "web" in role or "nginx" in role:
            if "nginx" not in running_names:
                return Finding(
                    category="Service",
                    severity="CRITICAL",
                    metric="service.nginx.running",
                    threshold=1.0,
                    actual_value=0.0,
                    message="Nginx web server is not running on web server asset.",
                    recommendation="Run 'systemctl start nginx' to restore web service traffic.",
                )
        elif "db" in role or "database" in role or "postgres" in role:
            if "postgresql" not in running_names:
                return Finding(
                    category="Service",
                    severity="CRITICAL",
                    metric="service.postgresql.running",
                    threshold=1.0,
                    actual_value=0.0,
                    message="PostgreSQL database service is not active on database host.",
                    recommendation="Run 'systemctl start postgresql' to restore database access.",
                )

        return None


# Register rules in registry
RuleRegistry.register(CPURule())
RuleRegistry.register(MemoryRule())
RuleRegistry.register(DiskRule())
RuleRegistry.register(NetworkRule())
RuleRegistry.register(ServiceRule())

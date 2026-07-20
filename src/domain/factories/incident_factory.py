# src/domain/factories/incident_factory.py
"""Factory for generating Operational Incidents from health assessment aggregates."""

from src.domain.entities.health import ServerHealth
from src.domain.entities.incident import Incident


class IncidentFactory:
    """Factory containing SRE business rules for incident creation."""

    @staticmethod
    def create_from_health(health: ServerHealth, server_hostname: str) -> Incident:
        """Instantiate an Incident aggregate from a ServerHealth evaluation result."""
        if health.overall_status.upper() == "HEALTHY":
            raise ValueError(
                "Cannot trigger SRE incidents from a HEALTHY server status."
            )

        # Determine severity based on overall health state and findings
        severity = "WARNING"
        if health.overall_status.upper() == "UNHEALTHY":
            severity = "CRITICAL"
        elif any(f.severity.upper() == "CRITICAL" for f in health.findings):
            severity = "CRITICAL"

        title = f"Health degradation detected on host {server_hostname}"
        description = (
            f"Server health check score dropped to {health.health_score} "
            f"with {len(health.findings)} active SRE rule violations."
        )

        return Incident(
            title=title,
            description=description,
            severity=severity,
            status="OPEN",
            source="MONITORING",
            server_id=health.server_id,
            findings=health.findings,
        )

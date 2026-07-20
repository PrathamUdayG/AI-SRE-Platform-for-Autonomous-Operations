# src/application/services/rule_engine.py
"""Service coordinating the evaluation of registered health rules."""

from datetime import datetime, timezone
from typing import List

import structlog

from src.domain.dtos.monitoring import EvaluationContext
from src.domain.entities.health import ServerHealth
from src.domain.exceptions import NotFoundError
from src.domain.repositories.health_repository import HealthRepository
from src.domain.repositories.inventory_repository import InventoryRepository
from src.domain.repositories.server_repository import ServerRepository
from src.domain.repositories.telemetry_repository import TelemetryRepository
from src.infrastructure.monitoring.rule_registry import RuleRegistry

logger = structlog.get_logger(__name__)


class RuleEngine:
    """Orchestrates health checks and rules evaluation for server assets."""

    def __init__(
        self,
        server_repository: ServerRepository,
        inventory_repository: InventoryRepository,
        telemetry_repository: TelemetryRepository,
        health_repository: HealthRepository,
    ):
        self.server_repository = server_repository
        self.inventory_repository = inventory_repository
        self.telemetry_repository = telemetry_repository
        self.health_repository = health_repository

    async def evaluate_server(self, server_id: int) -> ServerHealth:
        """Run health rules evaluation using the latest telemetry data."""
        logger.info("Initiating server health evaluation", server_id=server_id)

        # 1. Fetch server
        server = await self.server_repository.get_by_id(server_id)
        if not server:
            raise NotFoundError(f"Server with ID {server_id} not found.")

        # 2. Fetch inventory
        inventory = await self.inventory_repository.get_by_server_id(server_id)
        if not inventory:
            raise NotFoundError(
                f"Inventory record for server ID {server_id} not found."
            )

        # 3. Gather latest telemetry metrics
        latest_telemetry = {}
        metric_types = ["cpu", "memory", "disk", "network", "service"]
        for mtype in metric_types:
            metric = await self.telemetry_repository.get_latest_by_server_id(
                server_id, mtype
            )
            if metric:
                latest_telemetry[mtype] = metric

        # 4. Construct evaluation context
        context = EvaluationContext(
            inventory=inventory,
            latest_telemetry=latest_telemetry,
            timestamp=datetime.now(timezone.utc),
        )

        # 5. Run evaluations
        findings = []
        rules = RuleRegistry.get_rules()
        logger.info(
            "Evaluating rules", server_id=server_id, registered_rules=len(rules)
        )
        for rule in rules:
            try:
                finding = rule.evaluate(context)
                if finding:
                    findings.append(finding)
            except Exception as e:
                logger.error(
                    "Rule evaluation failed",
                    rule_id=rule.rule_id,
                    server_id=server_id,
                    error=str(e),
                )

        # 6. Calculate health score and state status
        # Deduction calculation: Critical = 20 pts, Warning = 10 pts, Info = 5 pts
        deductions = 0.0
        for f in findings:
            sev = f.severity.upper()
            if sev == "CRITICAL":
                deductions += 20.0
            elif sev == "WARNING":
                deductions += 10.0
            else:
                deductions += 5.0

        health_score = max(0.0, 100.0 - deductions)

        if health_score >= 90.0:
            overall_status = "HEALTHY"
        elif health_score >= 70.0:
            overall_status = "DEGRADED"
        else:
            overall_status = "UNHEALTHY"

        # 7. Persist evaluation results
        health = ServerHealth(
            server_id=server_id,
            overall_status=overall_status,
            health_score=health_score,
            findings=findings,
            evaluation_timestamp=context.timestamp,
        )

        saved_health = await self.health_repository.save(health)
        logger.info(
            "Server health evaluated successfully",
            server_id=server_id,
            score=health_score,
            status=overall_status,
            findings_count=len(findings),
        )
        return saved_health

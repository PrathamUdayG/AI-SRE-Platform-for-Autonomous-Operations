# tests/application/test_monitoring.py
"""Unit tests for the monitoring rules, registry, mappers, repository, and RuleEngine."""

from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock

import pytest

from src.application.services.rule_engine import RuleEngine
from src.domain.dtos.monitoring import EvaluationContext
from src.domain.entities.discovery import CPUInfo, MemoryInfo
from src.domain.entities.health import Finding, ServerHealth
from src.domain.entities.inventory import Inventory, InventoryMetadata
from src.domain.entities.server import Server
from src.domain.entities.telemetry import TelemetryMetric
from src.domain.exceptions import NotFoundError
from src.infrastructure.monitoring.rule_registry import RuleRegistry
from src.infrastructure.monitoring.rules import (
    CPURule,
    DiskRule,
    MemoryRule,
    NetworkRule,
    ServiceRule,
)
from src.infrastructure.persistence.mappers import HealthMapper
from src.infrastructure.persistence.models import ServerHealthModel
from src.infrastructure.repositories.postgres_health_repository import (
    PostgresHealthRepository,
)


@pytest.fixture
def sample_inventory():
    """Fixture returning a standard Inventory domain entity."""
    return Inventory(
        id=1,
        server_id=10,
        hostname="web-prod",
        operating_system="Linux",
        kernel_version="5.15",
        architecture="x86_64",
        uptime="1d",
        timezone="UTC",
        cpu=CPUInfo(
            model="Intel", cores=4, sockets=1, threads_per_core=1, architecture="x86"
        ),
        memory=MemoryInfo(
            total_mb=16000.0,
            used_mb=4000.0,
            free_mb=12000.0,
            shared_mb=0.0,
            buff_cache_mb=0.0,
            available_mb=12000.0,
        ),
        disks=[],
        network_interfaces=[],
        metadata=InventoryMetadata(environment="production", role="web"),
        last_discovered_at=datetime.now(timezone.utc),
    )


# ---------- Registry Tests ----------
def test_rule_registry():
    """Verify that RuleRegistry correctly registers and retrieves rules."""
    initial_count = len(RuleRegistry.get_rules())

    class DummyRule:
        @property
        def rule_id(self):
            return "dummy.rule"

        def evaluate(self, context):
            return None

    RuleRegistry.register(DummyRule())
    assert len(RuleRegistry.get_rules()) == initial_count + 1


# ---------- Rule Tests ----------
def test_cpu_rule(sample_inventory):
    """Verify CPURule evaluates cpu telemetry correctly."""
    rule = CPURule(threshold=80.0)

    # 1. OK case
    metric_ok = TelemetryMetric(
        id=1,
        server_id=10,
        metric_type="cpu",
        timestamp=datetime.now(timezone.utc),
        data={"usage_percent": 45.0},
    )
    context_ok = EvaluationContext(
        inventory=sample_inventory,
        latest_telemetry={"cpu": metric_ok},
        timestamp=datetime.now(timezone.utc),
    )
    assert rule.evaluate(context_ok) is None

    # 2. Violation case
    metric_bad = TelemetryMetric(
        id=2,
        server_id=10,
        metric_type="cpu",
        timestamp=datetime.now(timezone.utc),
        data={"usage_percent": 85.0},
    )
    context_bad = EvaluationContext(
        inventory=sample_inventory,
        latest_telemetry={"cpu": metric_bad},
        timestamp=datetime.now(timezone.utc),
    )
    finding = rule.evaluate(context_bad)
    assert finding is not None
    assert finding.category == "CPU"
    assert finding.severity == "WARNING"
    assert finding.actual_value == 85.0


def test_memory_rule(sample_inventory):
    """Verify MemoryRule evaluates memory usage against thresholds."""
    rule = MemoryRule(threshold=85.0)

    metric_bad = TelemetryMetric(
        id=3,
        server_id=10,
        metric_type="memory",
        timestamp=datetime.now(timezone.utc),
        data={"usage_percent": 96.0},
    )
    context = EvaluationContext(
        inventory=sample_inventory,
        latest_telemetry={"memory": metric_bad},
        timestamp=datetime.now(timezone.utc),
    )
    finding = rule.evaluate(context)
    assert finding is not None
    assert finding.category == "Memory"
    assert finding.severity == "CRITICAL"


def test_disk_rule(sample_inventory):
    """Verify DiskRule checks partition usage percent."""
    rule = DiskRule(threshold=90.0)

    metric = TelemetryMetric(
        id=4,
        server_id=10,
        metric_type="disk",
        timestamp=datetime.now(timezone.utc),
        data={
            "partitions": [
                {"mount_point": "/", "usage_percent": 40.0},
                {"mount_point": "/data", "usage_percent": 95.0},
            ]
        },
    )
    context = EvaluationContext(
        inventory=sample_inventory,
        latest_telemetry={"disk": metric},
        timestamp=datetime.now(timezone.utc),
    )
    finding = rule.evaluate(context)
    assert finding is not None
    assert finding.category == "Disk"
    assert finding.metric == "disk.usage_percent:/data"
    assert finding.severity == "WARNING"


def test_network_rule(sample_inventory):
    """Verify NetworkRule reports zero active interface warnings."""
    rule = NetworkRule()

    # Empty network interfaces list
    metric_empty = TelemetryMetric(
        id=5,
        server_id=10,
        metric_type="network",
        timestamp=datetime.now(timezone.utc),
        data={"interfaces": []},
    )
    context = EvaluationContext(
        inventory=sample_inventory,
        latest_telemetry={"network": metric_empty},
        timestamp=datetime.now(timezone.utc),
    )
    finding = rule.evaluate(context)
    assert finding is not None
    assert finding.severity == "CRITICAL"


def test_service_rule(sample_inventory):
    """Verify ServiceRule triggers warning when nginx service is down on a web server."""
    rule = ServiceRule()

    # Web server role but only postgres service running
    metric = TelemetryMetric(
        id=6,
        server_id=10,
        metric_type="service",
        timestamp=datetime.now(timezone.utc),
        data={"services": [{"name": "postgresql", "state": "running"}]},
    )
    context = EvaluationContext(
        inventory=sample_inventory,
        latest_telemetry={"service": metric},
        timestamp=datetime.now(timezone.utc),
    )
    finding = rule.evaluate(context)
    assert finding is not None
    assert finding.category == "Service"
    assert "nginx" in finding.message.lower()


# ---------- Mapper Tests ----------
def test_health_mapper():
    """Verify bidirectional mappings in HealthMapper."""
    finding = Finding(
        category="CPU",
        severity="WARNING",
        metric="cpu.usage",
        threshold=80.0,
        actual_value=82.0,
        message="high CPU usage",
        recommendation="check processes",
    )
    entity = ServerHealth(
        server_id=1,
        overall_status="DEGRADED",
        health_score=80.0,
        findings=[finding],
        evaluation_timestamp=datetime.now(timezone.utc),
    )

    model = HealthMapper.to_model(entity)
    assert isinstance(model, ServerHealthModel)
    assert model.health_score == 80.0
    assert len(model.findings) == 1
    assert model.findings[0]["metric"] == "cpu.usage"

    domain = HealthMapper.to_domain(model)
    assert domain.overall_status == "DEGRADED"
    assert len(domain.findings) == 1
    assert domain.findings[0].actual_value == 82.0


# ---------- Repository Tests ----------
@pytest.mark.asyncio
async def test_postgres_health_repository_save():
    """Verify PostgresHealthRepository save calls session add/commit/refresh."""
    mock_session = MagicMock()
    mock_session.add = MagicMock()
    mock_session.commit = AsyncMock()
    mock_session.refresh = AsyncMock()

    repo = PostgresHealthRepository(mock_session)
    entity = ServerHealth(
        server_id=3,
        overall_status="HEALTHY",
        health_score=100.0,
        findings=[],
        evaluation_timestamp=datetime.now(timezone.utc),
    )

    def mock_refresh(model):
        model.id = 88

    mock_session.refresh.side_effect = mock_refresh
    saved = await repo.save(entity)
    assert saved.id == 88
    mock_session.add.assert_called_once()
    mock_session.commit.assert_called_once()


# ---------- RuleEngine Service Tests ----------
@pytest.mark.asyncio
async def test_rule_engine_evaluate_success(sample_inventory):
    """Verify successful evaluation flow computes correct status and saves results."""
    server = Server(
        id=10,
        hostname="web-prod",
        ip_address="192.168.1.10",
        operating_system="Linux",
        cpu_cores=4,
        memory_gb=16.0,
    )

    mock_server_repo = MagicMock()
    mock_server_repo.get_by_id = AsyncMock(return_value=server)

    mock_inventory_repo = MagicMock()
    mock_inventory_repo.get_by_server_id = AsyncMock(return_value=sample_inventory)

    mock_telemetry_repo = MagicMock()
    # Mock CPU metric as 95% usage (triggering CPURule warning/critical)
    cpu_metric = TelemetryMetric(
        id=101,
        server_id=10,
        metric_type="cpu",
        timestamp=datetime.now(timezone.utc),
        data={"usage_percent": 95.0},
    )

    async def mock_get_latest(sid, mtype):
        if mtype == "cpu":
            return cpu_metric
        return None

    mock_telemetry_repo.get_latest_by_server_id = AsyncMock(side_effect=mock_get_latest)

    mock_health_repo = MagicMock()
    mock_health_repo.save = AsyncMock(side_effect=lambda h: h)

    engine = RuleEngine(
        server_repository=mock_server_repo,
        inventory_repository=mock_inventory_repo,
        telemetry_repository=mock_telemetry_repo,
        health_repository=mock_health_repo,
    )

    health = await engine.evaluate_server(10)
    assert health.server_id == 10
    assert len(health.findings) > 0
    # Should calculate a degraded/unhealthy score due to CPU usage violation
    assert health.health_score < 100.0
    assert health.overall_status != "HEALTHY"
    mock_health_repo.save.assert_called_once()


@pytest.mark.asyncio
async def test_rule_engine_server_not_found():
    """Verify NotFoundError is raised for invalid servers."""
    mock_server_repo = MagicMock()
    mock_server_repo.get_by_id = AsyncMock(return_value=None)

    engine = RuleEngine(
        server_repository=mock_server_repo,
        inventory_repository=MagicMock(),
        telemetry_repository=MagicMock(),
        health_repository=MagicMock(),
    )

    with pytest.raises(NotFoundError):
        await engine.evaluate_server(999)

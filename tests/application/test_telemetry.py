# tests/application/test_telemetry.py
"""Unit tests for the Telemetry Collectors, Parsers, Mappers, and Orchestrator."""

from datetime import datetime, timezone
from typing import Any, Optional
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.application.services.telemetry_orchestrator import TelemetryOrchestrator
from src.application.telemetry.parsers import (
    CPUTelemetryParser,
    DiskTelemetryParser,
    MemoryTelemetryParser,
    NetworkTelemetryParser,
    ProcessTelemetryParser,
    ServiceTelemetryParser,
)
from src.domain.dtos.telemetry import CollectionContext, RawMetric
from src.domain.entities.discovery import CPUInfo, MemoryInfo
from src.domain.entities.inventory import Inventory
from src.domain.entities.server import Server
from src.domain.entities.telemetry import TelemetryMetric
from src.domain.exceptions import NotFoundError
from src.domain.interfaces.connectors import ConnectorType, IConnector
from src.infrastructure.persistence.mappers import MetricMapper
from src.infrastructure.persistence.models import TelemetryMetricModel
from src.infrastructure.repositories.postgres_telemetry_repository import (
    PostgresTelemetryRepository,
)
from src.infrastructure.telemetry.collectors import (
    CPUCollector,
    DiskCollector,
    MemoryCollector,
    NetworkCollector,
    ProcessCollector,
    ServiceCollector,
)

# ---------- Mock Command Outputs ----------
TOP_CPU_MOCK = "%Cpu(s):  1.5 us,  0.5 sy,  0.0 ni, 98.0 id,  0.0 wa,  0.0 hi"
FREE_M_MOCK = """
               total        used        free      shared  buff/cache   available
Mem:           16000        4000        2000         500        10000       11500
Swap:           2048           0        2048
"""
DF_H_MOCK = """
Filesystem      Size  Used Avail Use% Mounted on
/dev/nvme0n1p1  250G  100G  150G  40% /
tmpfs           3.9G     0  3.9G   0% /dev/shm
"""
PROC_NET_DEV_MOCK = """
Inter-|   Receive                                                |  Transmit
 face |bytes    packets errs drop fifo frame compressed multicast|bytes    packets errs drop fifo colls carrier compressed
    lo:    1000      10    0    0    0     0          0         0     1000      10    0    0    0     0       0          0
  eth0: 5000000    2000    0    0    0     0          0         0  8000000    3000    0    0    0     0       0          0
"""
PS_MOCK = """
  PID  PPID %CPU %MEM CMD
 1234     1  2.5  1.2 python main.py
 5678  1234  1.0  0.8 worker.py
"""
SYSTEMCTL_MOCK = """
nginx.service                                   loaded active running Nginx Web Server
postgresql.service                              loaded active running PostgreSQL Database
"""


# ---------- Typed Mock Connector ----------
class MockConnector(IConnector):
    """Mock implementation of IConnector to pass Pydantic type checks."""

    def __init__(self, execute_side_effect=None):
        self._is_connected = False
        self._execute_side_effect = execute_side_effect

    async def connect(self) -> None:
        self._is_connected = True

    async def disconnect(self) -> None:
        self._is_connected = False

    @property
    def is_connected(self) -> bool:
        return self._is_connected

    async def execute(self, command: str, timeout: Optional[float] = None) -> str:
        if self._execute_side_effect:
            return await self._execute_side_effect(command)
        return ""

    async def upload_file(self, local_path: str, remote_path: str) -> None:
        pass

    async def download_file(self, remote_path: str, local_path: str) -> None:
        pass

    @property
    def type(self) -> ConnectorType:
        return ConnectorType.SSH


# ---------- Parser Tests ----------
def test_cpu_parser():
    """Verify CPU usage parsing."""
    res = CPUTelemetryParser.parse(TOP_CPU_MOCK)
    assert res["usage_percent"] == 2.0
    assert res["idle_percent"] == 98.0

    fallback_res = CPUTelemetryParser.parse("0.15 0.10 0.05 1/120 12345")
    assert fallback_res["load_1m"] == 0.15


def test_memory_parser():
    """Verify free memory parsing."""
    res = MemoryTelemetryParser.parse(FREE_M_MOCK)
    assert res["total_mb"] == 16000.0
    assert res["used_mb"] == 4000.0
    assert res["usage_percent"] == 25.0


def test_disk_parser():
    """Verify df -h disk partitions parsing."""
    res = DiskTelemetryParser.parse(DF_H_MOCK)
    assert len(res) == 1
    assert res[0]["device"] == "/dev/nvme0n1p1"
    assert res[0]["usage_percent"] == 40.0


def test_network_parser():
    """Verify rx/tx network bytes parsing."""
    res = NetworkTelemetryParser.parse(PROC_NET_DEV_MOCK)
    assert len(res) == 1
    assert res[0]["interface"] == "eth0"
    assert res[0]["rx_bytes"] == 5000000


def test_process_parser():
    """Verify running CPU processes parsing."""
    res = ProcessTelemetryParser.parse(PS_MOCK)
    assert len(res) == 2
    assert res[0]["pid"] == 1234
    assert res[0]["cpu_percent"] == 2.5
    assert "python main.py" in res[0]["command"]


def test_service_parser():
    """Verify active systemctl services parsing."""
    res = ServiceTelemetryParser.parse(SYSTEMCTL_MOCK)
    assert len(res) == 2
    assert res[0]["name"] == "nginx"


# ---------- Collector Tests ----------
@pytest.mark.asyncio
async def test_collectors():
    """Verify all collectors execute correct commands and invoke parsers."""
    server = Server(
        id=1,
        hostname="server-1",
        ip_address="1.2.3.4",
        operating_system="Linux",
        cpu_cores=4,
        memory_gb=16.0,
    )
    inventory = Inventory(
        id=1,
        server_id=1,
        hostname="server-1",
        operating_system="Linux",
        kernel_version="5.4",
        architecture="x86_64",
        uptime="10d",
        timezone="UTC",
        cpu=CPUInfo(
            model="Intel",
            cores=4,
            sockets=1,
            threads_per_core=1,
            architecture="x86",
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
        last_discovered_at=datetime.now(timezone.utc),
    )

    async def mock_execute(cmd):
        if "free" in cmd:
            return FREE_M_MOCK
        elif "df" in cmd:
            return DF_H_MOCK
        elif "net/dev" in cmd:
            return PROC_NET_DEV_MOCK
        elif "ps" in cmd:
            return PS_MOCK
        elif "systemctl" in cmd:
            return SYSTEMCTL_MOCK
        return TOP_CPU_MOCK

    mock_connector = MockConnector(execute_side_effect=mock_execute)

    context = CollectionContext(
        server=server,
        inventory=inventory,
        connector=mock_connector,
        timestamp=datetime.now(timezone.utc),
    )

    # Test CPU
    cpu_raw = await CPUCollector().collect(context)
    assert cpu_raw.metric_type == "cpu"
    assert cpu_raw.data["usage_percent"] == 2.0

    # Test Memory
    mem_raw = await MemoryCollector().collect(context)
    assert mem_raw.metric_type == "memory"
    assert mem_raw.data["total_mb"] == 16000.0

    # Test Disk
    disk_raw = await DiskCollector().collect(context)
    assert disk_raw.metric_type == "disk"
    assert len(disk_raw.data["partitions"]) == 1

    # Test Network
    net_raw = await NetworkCollector().collect(context)
    assert net_raw.metric_type == "network"
    assert len(net_raw.data["interfaces"]) == 1

    # Test Process
    proc_raw = await ProcessCollector().collect(context)
    assert proc_raw.metric_type == "process"
    assert len(proc_raw.data["processes"]) == 2

    # Test Service
    srv_raw = await ServiceCollector().collect(context)
    assert srv_raw.metric_type == "service"
    assert len(srv_raw.data["services"]) == 2


# ---------- Mapper Tests ----------
def test_metric_mapper():
    """Verify bidirectional mappings in MetricMapper."""
    raw = RawMetric(
        server_id=10,
        metric_type="cpu",
        timestamp=datetime.now(timezone.utc),
        data={"usage_percent": 12.5},
    )

    entity = MetricMapper.to_entity(raw)
    assert entity.id is None
    assert entity.server_id == 10
    assert entity.data == {"usage_percent": 12.5}

    entity.id = 77
    model = MetricMapper.to_model(entity)
    assert isinstance(model, TelemetryMetricModel)
    assert model.id == 77
    assert model.server_id == 10

    domain = MetricMapper.to_domain(model)
    assert domain.id == 77
    assert domain.server_id == 10
    assert domain.data == {"usage_percent": 12.5}


# ---------- TelemetryOrchestrator Tests ----------
@pytest.mark.asyncio
async def test_telemetry_orchestrator_success():
    """Verify successful orchestration collects, resolves, and saves metrics."""
    server = Server(
        id=5,
        hostname="prod-api",
        ip_address="192.168.1.5",
        operating_system="Ubuntu",
        cpu_cores=8,
        memory_gb=32.0,
    )
    inventory = Inventory(
        id=2,
        server_id=5,
        hostname="prod-api",
        operating_system="Ubuntu",
        kernel_version="5.15",
        architecture="x86_64",
        uptime="5d",
        timezone="UTC",
        cpu=CPUInfo(
            model="AMD",
            cores=8,
            sockets=1,
            threads_per_core=2,
            architecture="x86_64",
        ),
        memory=MemoryInfo(
            total_mb=32000.0,
            used_mb=8000.0,
            free_mb=24000.0,
            shared_mb=0.0,
            buff_cache_mb=0.0,
            available_mb=24000.0,
        ),
        disks=[],
        network_interfaces=[],
        last_discovered_at=datetime.now(timezone.utc),
    )

    mock_server_repo = MagicMock()
    mock_server_repo.get_by_id = AsyncMock(return_value=server)

    mock_inventory_repo = MagicMock()
    mock_inventory_repo.get_by_server_id = AsyncMock(return_value=inventory)

    async def mock_execute(cmd):
        return FREE_M_MOCK

    mock_connector = MockConnector(execute_side_effect=mock_execute)

    mock_resolver = MagicMock()
    mock_resolver.resolve = MagicMock(return_value=mock_connector)

    mock_telemetry_repo = MagicMock()
    mock_telemetry_repo.save = AsyncMock(side_effect=lambda s: s)

    orchestrator = TelemetryOrchestrator(
        server_repository=mock_server_repo,
        inventory_repository=mock_inventory_repo,
        connector_resolver=mock_resolver,
        telemetry_repository=mock_telemetry_repo,
    )

    results = await orchestrator.collect_telemetry(server_id=5)

    assert len(results) > 0
    # The CPUCollector was registered and executed
    cpu_result = next((r for r in results if r.metric_type == "cpu"), None)
    assert cpu_result is not None
    assert mock_telemetry_repo.save.call_count == len(results)


@pytest.mark.asyncio
async def test_telemetry_orchestrator_server_not_found():
    """Verify orchestrator raises NotFoundError for invalid servers."""
    mock_server_repo = MagicMock()
    mock_server_repo.get_by_id = AsyncMock(return_value=None)
    mock_inventory_repo = MagicMock()
    mock_resolver = MagicMock()
    mock_telemetry_repo = MagicMock()

    orchestrator = TelemetryOrchestrator(
        server_repository=mock_server_repo,
        inventory_repository=mock_inventory_repo,
        connector_resolver=mock_resolver,
        telemetry_repository=mock_telemetry_repo,
    )

    with pytest.raises(NotFoundError):
        await orchestrator.collect_telemetry(server_id=999)


# ---------- PostgresTelemetryRepository Tests ----------
@pytest.mark.asyncio
async def test_postgres_telemetry_repository_save():
    """Verify PostgresTelemetryRepository save and mapping flow."""
    mock_session = MagicMock()
    mock_session.add = MagicMock()
    mock_session.commit = AsyncMock()
    mock_session.refresh = AsyncMock()

    repo = PostgresTelemetryRepository(mock_session)

    entity = TelemetryMetric(
        id=None,
        server_id=12,
        metric_type="cpu",
        timestamp=datetime.now(timezone.utc),
        data={"usage_percent": 15.0},
    )

    def mock_refresh(model):
        model.id = 101

    mock_session.refresh.side_effect = mock_refresh

    saved = await repo.save(entity)
    assert saved.id == 101
    mock_session.add.assert_called_once()
    mock_session.commit.assert_called_once()

# src/infrastructure/telemetry/collectors.py
"""Concrete implementations of system telemetry collectors."""

import structlog

from src.application.telemetry.parsers import (
    CPUTelemetryParser,
    DiskTelemetryParser,
    MemoryTelemetryParser,
    NetworkTelemetryParser,
    ProcessTelemetryParser,
    ServiceTelemetryParser,
)
from src.domain.dtos.telemetry import CollectionContext, RawMetric
from src.domain.interfaces.collectors import (
    ICPUCollector,
    IDiskCollector,
    IMemoryCollector,
    INetworkCollector,
    IProcessCollector,
    IServiceCollector,
)
from src.infrastructure.telemetry.collector_registry import CollectorRegistry

logger = structlog.get_logger(__name__)


class CPUCollector(ICPUCollector):
    """Collector for CPU utilization and load statistics."""

    async def collect(self, context: CollectionContext) -> RawMetric:
        assert context.server.id is not None
        logger.info("Collecting CPU telemetry", server_id=context.server.id)
        try:
            output = await context.connector.execute(
                'top -bn1 | grep "Cpu(s)" || cat /proc/loadavg'
            )
        except Exception as e:
            logger.warning(
                "Failed to collect CPU top stats; using loadavg fallback",
                error=str(e),
            )
            output = await context.connector.execute("cat /proc/loadavg")

        parsed_data = CPUTelemetryParser.parse(output)
        return RawMetric(
            server_id=context.server.id,
            metric_type="cpu",
            timestamp=context.timestamp,
            data=parsed_data,
        )


class MemoryCollector(IMemoryCollector):
    """Collector for system memory allocation details."""

    async def collect(self, context: CollectionContext) -> RawMetric:
        assert context.server.id is not None
        logger.info("Collecting Memory telemetry", server_id=context.server.id)
        output = await context.connector.execute("free -m")
        parsed_data = MemoryTelemetryParser.parse(output)
        return RawMetric(
            server_id=context.server.id,
            metric_type="memory",
            timestamp=context.timestamp,
            data=parsed_data,
        )


class DiskCollector(IDiskCollector):
    """Collector for mounted partition disk usage capacities."""

    async def collect(self, context: CollectionContext) -> RawMetric:
        assert context.server.id is not None
        logger.info("Collecting Disk telemetry", server_id=context.server.id)
        output = await context.connector.execute("df -h")
        parsed_data = DiskTelemetryParser.parse(output)
        return RawMetric(
            server_id=context.server.id,
            metric_type="disk",
            timestamp=context.timestamp,
            data={"partitions": parsed_data},
        )


class NetworkCollector(INetworkCollector):
    """Collector for network interfaces RX/TX data rates."""

    async def collect(self, context: CollectionContext) -> RawMetric:
        assert context.server.id is not None
        logger.info("Collecting Network telemetry", server_id=context.server.id)
        output = await context.connector.execute("cat /proc/net/dev")
        parsed_data = NetworkTelemetryParser.parse(output)
        return RawMetric(
            server_id=context.server.id,
            metric_type="network",
            timestamp=context.timestamp,
            data={"interfaces": parsed_data},
        )


class ProcessCollector(IProcessCollector):
    """Collector for active process CPU/Memory consumption lists."""

    async def collect(self, context: CollectionContext) -> RawMetric:
        assert context.server.id is not None
        logger.info("Collecting Process telemetry", server_id=context.server.id)
        output = await context.connector.execute(
            "ps -eo pid,ppid,%cpu,%mem,cmd --sort=-%cpu | head -n 11"
        )
        parsed_data = ProcessTelemetryParser.parse(output)
        return RawMetric(
            server_id=context.server.id,
            metric_type="process",
            timestamp=context.timestamp,
            data={"processes": parsed_data},
        )


class ServiceCollector(IServiceCollector):
    """Collector for active systemctl running services list."""

    async def collect(self, context: CollectionContext) -> RawMetric:
        assert context.server.id is not None
        logger.info("Collecting Service telemetry", server_id=context.server.id)
        output = await context.connector.execute(
            "systemctl list-units --type=service --state=running --no-legend"
        )
        parsed_data = ServiceTelemetryParser.parse(output)
        return RawMetric(
            server_id=context.server.id,
            metric_type="service",
            timestamp=context.timestamp,
            data={"services": parsed_data},
        )


# Register all collectors inside the global registry
CollectorRegistry.register("cpu", CPUCollector())
CollectorRegistry.register("memory", MemoryCollector())
CollectorRegistry.register("disk", DiskCollector())
CollectorRegistry.register("network", NetworkCollector())
CollectorRegistry.register("process", ProcessCollector())
CollectorRegistry.register("service", ServiceCollector())

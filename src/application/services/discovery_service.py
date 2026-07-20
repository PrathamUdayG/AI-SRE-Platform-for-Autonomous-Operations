# src/application/services/discovery_service.py
"""Application service that orchestrates the infrastructure discovery pipeline."""

from datetime import datetime, timezone
from typing import Optional

import structlog

from src.application.discovery.parsers import (
    CPUParser,
    FilesystemParser,
    MemoryParser,
    NetworkParser,
    OSParser,
    TimezoneParser,
    UptimeParser,
)
from src.domain.discovery.commands import DiscoveryCommands
from src.domain.dtos.discovery_result import DiscoveryResult
from src.domain.entities.discovery import DiscoverySnapshot
from src.domain.exceptions import ConnectionFailedError, NotFoundError
from src.domain.interfaces.connector_resolver import IConnectorResolver
from src.domain.interfaces.connectors import ConnectorType
from src.domain.repositories.discovery_repository import DiscoveryRepository
from src.domain.repositories.server_repository import ServerRepository
from src.infrastructure.config.settings import settings
from src.infrastructure.persistence.mappers import DiscoveryMapper

logger = structlog.get_logger(__name__)


class DiscoveryService:
    """Orchestrates system command executions, raw output parsings, and DTO returns."""

    def __init__(
        self,
        server_repository: ServerRepository,
        discovery_repository: DiscoveryRepository,
        connector_resolver: IConnectorResolver,
    ):
        self.server_repository = server_repository
        self.discovery_repository = discovery_repository
        self.connector_resolver = connector_resolver

    async def discover_server(self, server_id: int) -> DiscoveryResult:
        """Trigger low-level target command query, assemble DiscoveryResult DTO, persist snapshot, and return."""
        logger.info("Triggering infrastructure discovery", server_id=server_id)

        # 1. Retrieve the registered server
        server = await self.server_repository.get_by_id(server_id)
        if not server:
            raise NotFoundError(f"Server with ID {server_id} not found.")

        # 2. Resolve the SSH connector using IConnectorResolver
        password_val = (
            settings.hostinger.ssh_password.get_secret_value()
            if settings.hostinger.ssh_password
            else None
        )
        connector = self.connector_resolver.resolve(
            ConnectorType.SSH,
            host=server.ip_address,
            username=settings.hostinger.ssh_username,
            password=password_val,
            key_path=settings.hostinger.ssh_key_path,
            port=settings.hostinger.ssh_port,
            timeout=settings.hostinger.ssh_timeout,
            retries=2,
            retry_delay=1.0,
        )

        # 3. Execute all target commands to harvest system telemetry
        try:
            await connector.connect()

            hostname_out = await connector.execute(DiscoveryCommands.HOSTNAME)
            os_out = await connector.execute(DiscoveryCommands.OS_INFO)
            kernel_out = await connector.execute(DiscoveryCommands.KERNEL_INFO)
            arch_out = await connector.execute(DiscoveryCommands.ARCH)
            cpu_out = await connector.execute(DiscoveryCommands.CPU_INFO)
            mem_out = await connector.execute(DiscoveryCommands.MEMORY_INFO)
            disk_out = await connector.execute(DiscoveryCommands.DISK_INFO)
            net_out = await connector.execute(DiscoveryCommands.NETWORK_INFO)
            tz_out = await connector.execute(DiscoveryCommands.TIMEZONE)
            uptime_out = await connector.execute(DiscoveryCommands.UPTIME)
        except Exception as e:
            logger.error(
                "Discovery command execution failed",
                server_id=server_id,
                error=str(e),
            )
            raise ConnectionFailedError(
                f"Discovery failed due to network communication error: {str(e)}"
            )
        finally:
            await connector.disconnect()

        # 4. Invoke the individual functional parsers
        hostname = hostname_out.strip()
        operating_system = OSParser.parse(os_out)
        kernel_version = kernel_out.strip()
        architecture = arch_out.strip()
        cpu_info = CPUParser.parse(cpu_out)
        memory_info = MemoryParser.parse(mem_out)
        disks = FilesystemParser.parse(disk_out)
        network_interfaces = NetworkParser.parse(net_out)
        timezone_val = TimezoneParser.parse(tz_out)
        uptime = UptimeParser.parse(uptime_out)

        # 5. Assemble DiscoveryResult DTO
        result = DiscoveryResult(
            server_id=server_id,
            hostname=hostname,
            operating_system=operating_system,
            kernel_version=kernel_version,
            architecture=architecture,
            uptime=uptime,
            timezone=timezone_val,
            cpu=cpu_info,
            memory=memory_info,
            disks=disks,
            network_interfaces=network_interfaces,
            discovered_at=datetime.now(timezone.utc),
        )

        # 6. Map DTO to persistable snapshot entity and save in discovery repository for history/audit
        snapshot = DiscoveryMapper.to_snapshot(result)
        await self.discovery_repository.save(snapshot)

        return result

    async def get_latest_discovery(self, server_id: int) -> Optional[DiscoverySnapshot]:
        """Fetch the most recent discovery snapshot for the specified server."""
        logger.info("Retrieving latest discovery snapshot", server_id=server_id)
        server = await self.server_repository.get_by_id(server_id)
        if not server:
            raise NotFoundError(f"Server with ID {server_id} not found.")

        return await self.discovery_repository.get_latest_by_server_id(server_id)


class_config = {"from_attributes": True}

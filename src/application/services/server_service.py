# src/application/services/server_service.py
# Why: This Application Service handles the domain use case of registering a server.
# It validates inputs (hostname, IP address) and checks for duplicates against
# the repository interface before invoking persistence, maintaining Clean Architecture.

import ipaddress
import re
import structlog
from src.domain.entities.server import Server
from src.domain.repositories.server_repository import ServerRepository
from src.domain.exceptions import ValidationError, ConflictError

logger = structlog.get_logger(__name__)

class ServerService:
    """
    Application Service representing the Server Registration use cases.
    """

    def __init__(self, repository: ServerRepository):
        self.repository = repository

    async def register_server(
        self,
        hostname: str,
        ip_address: str,
        operating_system: str,
        cpu_cores: int,
        memory_gb: float,
    ) -> Server:
        """
        Validates and registers a new server in the platform.
        """
        logger.info("Registering new server", hostname=hostname, ip_address=ip_address)

        # 1. Validate hostname
        self._validate_hostname(hostname)

        # 2. Validate IP Address
        self._validate_ip(ip_address)

        # 3. Validate resources
        if cpu_cores <= 0:
            raise ValidationError(f"CPU cores must be greater than 0. Got {cpu_cores}")
        if memory_gb <= 0:
            raise ValidationError(f"Memory GB must be greater than 0. Got {memory_gb}")

        # 4. Check if server already exists by hostname or IP address
        if await self.repository.exists(hostname, ip_address):
            logger.warning("Conflict detected during server registration", hostname=hostname, ip_address=ip_address)
            raise ConflictError(
                f"A server with hostname '{hostname}' or IP '{ip_address}' already exists."
            )

        # 5. Create domain entity
        new_server = Server.create(
            hostname=hostname,
            ip_address=ip_address,
            operating_system=operating_system,
            cpu_cores=cpu_cores,
            memory_gb=memory_gb,
        )

        # 6. Save using repository
        saved_server = await self.repository.save(new_server)
        logger.info("Server registered successfully", server_id=saved_server.id, hostname=hostname)

        return saved_server

    def _validate_hostname(self, hostname: str) -> None:
        if not hostname or len(hostname.strip()) == 0:
            raise ValidationError("Hostname cannot be empty.")
        if len(hostname) > 253:
            raise ValidationError("Hostname cannot be longer than 253 characters.")
        # Hostname regex (RFC 1123 compliant hostname label checks)
        hostname_regex = r"^(?![0-9]+$)(?!-)[a-zA-Z0-9-]{1,63}(?<!-)(\.[a-zA-Z0-9-]{1,63})*$"
        if not re.match(hostname_regex, hostname):
            raise ValidationError(f"Invalid hostname format: '{hostname}'")

    def _validate_ip(self, ip: str) -> None:
        if not ip or len(ip.strip()) == 0:
            raise ValidationError("IP address cannot be empty.")
        try:
            ipaddress.ip_address(ip)
        except ValueError:
            raise ValidationError(f"Invalid IP address format: '{ip}'")

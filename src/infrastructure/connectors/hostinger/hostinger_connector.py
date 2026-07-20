# src/infrastructure/connectors/hostinger/hostinger_connector.py
"""Hostinger specific VPS connector implementation."""

from typing import Any, Dict, Optional

import httpx
import structlog

from src.domain.exceptions import ConnectionFailedError
from src.domain.interfaces.connectors import ConnectorType, IConnector
from src.infrastructure.connectors.linux.ssh_connector import LinuxSSHConnector

logger = structlog.get_logger(__name__)


class HostingerConnector(IConnector):
    """Hostinger-specific connector.

    Delegates OS-level communication to LinuxSSHConnector, while offering
    Hostinger API capabilities for VPS management.
    """

    def __init__(
        self,
        host: str,
        username: str,
        password: Optional[str] = None,
        key_path: Optional[str] = None,
        port: int = 22,
        timeout: float = 10.0,
        api_base_url: str = "https://api.hostinger.com/v1",
        api_token: Optional[str] = None,
    ):
        self._ssh_connector = LinuxSSHConnector(
            host=host,
            username=username,
            password=password,
            key_path=key_path,
            port=port,
            timeout=timeout,
        )
        self._api_base_url = api_base_url
        self._api_token = api_token
        self._client: Optional[httpx.AsyncClient] = None

    @property
    def type(self) -> ConnectorType:
        return ConnectorType.HOSTINGER

    @property
    def is_connected(self) -> bool:
        return self._ssh_connector.is_connected

    async def connect(self) -> None:
        """Establish SSH session and prepare API client."""
        logger.info(
            "Connecting to Hostinger VPS & API",
            base_url=self._api_base_url,
            host=self._ssh_connector._host,
        )
        # Connect SSH
        await self._ssh_connector.connect()

        # Initialize HTTP client for Hostinger API
        headers = {}
        if self._api_token:
            headers["Authorization"] = f"Bearer {self._api_token}"
        self._client = httpx.AsyncClient(
            base_url=self._api_base_url,
            headers=headers,
            timeout=self._ssh_connector._timeout,
        )

    async def disconnect(self) -> None:
        """Disconnect SSH and close API client."""
        await self._ssh_connector.disconnect()
        if self._client:
            await self._client.aclose()
            self._client = None

    async def execute(self, command: str, timeout: Optional[float] = None) -> str:
        """Execute shell command on Hostinger VPS."""
        return await self._ssh_connector.execute(command, timeout)

    async def upload_file(self, local_path: str, remote_path: str) -> None:
        """Upload file to Hostinger VPS."""
        await self._ssh_connector.upload_file(local_path, remote_path)

    async def download_file(self, remote_path: str, local_path: str) -> None:
        """Download file from Hostinger VPS."""
        await self._ssh_connector.download_file(remote_path, local_path)

    # ---------- Hostinger API VPS Capabilities ----------
    async def reboot_vps(self, vps_id: str) -> None:
        """Trigger VPS reboot via Hostinger API."""
        if not self._client:
            raise ConnectionFailedError(
                "Hostinger API client is not initialized. Call connect() first."
            )
        logger.info("Requesting Hostinger VPS reboot", vps_id=vps_id)
        try:
            response = await self._client.post(f"/vps/{vps_id}/reboot")
            response.raise_for_status()
        except Exception as e:
            logger.error("Failed to reboot Hostinger VPS", vps_id=vps_id, error=str(e))
            raise ConnectionFailedError(
                f"Hostinger API VPS reboot request failed: {str(e)}"
            )

    async def get_vps_details(self, vps_id: str) -> Dict[str, Any]:
        """Fetch VPS details from Hostinger API."""
        if not self._client:
            raise ConnectionFailedError(
                "Hostinger API client is not initialized. Call connect() first."
            )
        logger.info("Fetching Hostinger VPS details", vps_id=vps_id)
        try:
            response = await self._client.get(f"/vps/{vps_id}")
            response.raise_for_status()
            return response.json()
        except Exception as e:
            logger.error(
                "Failed to fetch Hostinger VPS details",
                vps_id=vps_id,
                error=str(e),
            )
            raise ConnectionFailedError(f"Hostinger API fetch details failed: {str(e)}")

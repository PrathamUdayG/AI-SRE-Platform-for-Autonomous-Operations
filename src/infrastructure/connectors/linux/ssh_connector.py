# src/infrastructure/connectors/linux/ssh_connector.py
"""Paramiko-based SSH connector for remote Linux hosts."""

import asyncio
import os
import socket
from typing import Optional

import paramiko  # type: ignore[import-untyped]
import structlog

from src.domain.exceptions import (
    AuthenticationFailedError,
    CommandExecutionFailedError,
    ConnectionFailedError,
    ConnectorTimeoutError,
)
from src.domain.interfaces.connectors import ConnectorType, IConnector

logger = structlog.get_logger(__name__)


class LinuxSSHConnector(IConnector):
    """Paramiko-based SSH connector for remote Linux hosts.

    Executes blocking operations in separate threads to avoid blocking the
    asyncio event loop.
    """

    def __init__(
        self,
        host: str,
        username: str,
        password: Optional[str] = None,
        key_path: Optional[str] = None,
        port: int = 22,
        timeout: float = 10.0,
        retries: int = 3,
        retry_delay: float = 1.0,
    ):
        self._host = host
        self._username = username
        self._password = password
        self._key_path = key_path
        self._port = port
        self._timeout = timeout
        self._retries = retries
        self._retry_delay = retry_delay

        self._client: Optional[paramiko.SSHClient] = None
        self._connected = False

    @property
    def type(self) -> ConnectorType:
        return ConnectorType.SSH

    @property
    def is_connected(self) -> bool:
        return (
            self._connected
            and self._client is not None
            and self._client.get_transport() is not None
            and self._client.get_transport().is_active()
        )

    async def connect(self) -> None:
        """Connect to the remote host with retry logic."""
        if self.is_connected:
            return

        logger.info(
            "Connecting via SSH",
            host=self._host,
            username=self._username,
            port=self._port,
        )

        last_error: Optional[Exception] = None
        for attempt in range(1, self._retries + 1):
            try:
                await asyncio.to_thread(self._sync_connect)
                self._connected = True
                logger.info("SSH connection established successfully", host=self._host)
                return
            except (AuthenticationFailedError, ConnectorTimeoutError):
                # Don't retry on auth failures, they are permanent
                raise
            except Exception as e:
                last_error = e
                logger.warning(
                    "SSH connection attempt failed",
                    host=self._host,
                    attempt=attempt,
                    error=str(e),
                )
                if attempt < self._retries:
                    await asyncio.sleep(self._retry_delay)

        raise ConnectionFailedError(
            f"Failed to connect to {self._host}:{self._port} after"
            f" {self._retries} attempts. Last error: {str(last_error)}"
        )

    def _sync_connect(self) -> None:
        client = paramiko.SSHClient()
        client.set_missing_host_key_policy(paramiko.AutoAddPolicy())

        # Load private key if path is provided
        pkey = None
        if self._key_path:
            expanded_path = os.path.expanduser(self._key_path)
            if not os.path.exists(expanded_path):
                raise ConnectionFailedError(
                    f"SSH private key file not found: {expanded_path}"
                )
            try:
                pkey = paramiko.RSAKey.from_private_key_file(expanded_path)
            except paramiko.PasswordRequiredException:
                # If key requires password, try using the provided password
                if self._password:
                    pkey = paramiko.RSAKey.from_private_key_file(
                        expanded_path, password=self._password
                    )
                else:
                    raise AuthenticationFailedError(
                        "SSH private key requires a passphrase."
                    )
            except Exception as e:
                raise ConnectionFailedError(f"Failed to load SSH private key: {str(e)}")

        try:
            client.connect(
                hostname=self._host,
                port=self._port,
                username=self._username,
                password=self._password,
                pkey=pkey,
                timeout=self._timeout,
                banner_timeout=self._timeout,
                auth_timeout=self._timeout,
            )
            self._client = client
        except paramiko.AuthenticationException as ae:
            raise AuthenticationFailedError(f"Authentication failed: {str(ae)}")
        except (socket.timeout, TimeoutError) as te:
            raise ConnectorTimeoutError(f"Connection timeout: {str(te)}")
        except (paramiko.SSHException, socket.error) as se:
            raise ConnectionFailedError(f"SSH error occurred: {str(se)}")

    async def disconnect(self) -> None:
        """Close the SSH connection."""
        if self._client:
            logger.info("Disconnecting SSH client", host=self._host)
            try:
                await asyncio.to_thread(self._client.close)
            except Exception as e:
                logger.error("Error closing SSH connection", error=str(e))
            finally:
                self._client = None
                self._connected = False

    async def execute(self, command: str, timeout: Optional[float] = None) -> str:
        """Execute command and return raw output."""
        if not self.is_connected:
            await self.connect()

        exec_timeout = timeout or self._timeout
        logger.info(
            "Executing SSH command",
            host=self._host,
            command=command,
            timeout=exec_timeout,
        )

        try:
            return await asyncio.to_thread(self._sync_execute, command, exec_timeout)
        except (
            CommandExecutionFailedError,
            ConnectorTimeoutError,
            ConnectionFailedError,
        ):
            raise
        except Exception as e:
            logger.error("Failed to execute SSH command", error=str(e))
            raise CommandExecutionFailedError(f"Command execution failed: {str(e)}")

    def _sync_execute(self, command: str, timeout: float) -> str:
        if not self._client:
            raise ConnectionFailedError("Client is not connected.")

        transport = self._client.get_transport()
        if not transport:
            raise ConnectionFailedError("Transport is inactive.")

        try:
            chan = transport.open_session()
            chan.settimeout(timeout)
            chan.exec_command(command)

            # Read outputs
            stdout_data = []
            stderr_data = []

            # Wait for command exit status while reading
            while not chan.exit_status_ready():
                if chan.recv_ready():
                    stdout_data.append(
                        chan.recv(4096).decode("utf-8", errors="replace")
                    )
                if chan.recv_stderr_ready():
                    stderr_data.append(
                        chan.recv_stderr(4096).decode("utf-8", errors="replace")
                    )

                # Check if we should exit due to timeout/close
                if chan.closed:
                    break

            # Collect remaining data
            while chan.recv_ready():
                stdout_data.append(chan.recv(4096).decode("utf-8", errors="replace"))
            while chan.recv_stderr_ready():
                stderr_data.append(
                    chan.recv_stderr(4096).decode("utf-8", errors="replace")
                )

            exit_status = chan.get_exit_status()
            stdout_str = "".join(stdout_data)
            stderr_str = "".join(stderr_data)

            if exit_status != 0:
                raise CommandExecutionFailedError(
                    f"Command returned exit status {exit_status}. Stderr:"
                    f" {stderr_str.strip()}"
                )

            return stdout_str
        except socket.timeout:
            raise ConnectorTimeoutError(f"Command timed out after {timeout} seconds.")
        except Exception as e:
            if isinstance(e, (CommandExecutionFailedError, ConnectorTimeoutError)):
                raise
            raise ConnectionFailedError(f"Channel execution error: {str(e)}")

    async def upload_file(self, local_path: str, remote_path: str) -> None:
        """Upload a file using SFTP."""
        if not self.is_connected:
            await self.connect()

        logger.info(
            "Uploading file via SFTP",
            host=self._host,
            local=local_path,
            remote=remote_path,
        )
        try:
            await asyncio.to_thread(self._sync_upload_file, local_path, remote_path)
        except Exception as e:
            logger.error("SFTP upload failed", error=str(e))
            raise ConnectionFailedError(f"SFTP upload failed: {str(e)}")

    def _sync_upload_file(self, local_path: str, remote_path: str) -> None:
        if not self._client:
            raise ConnectionFailedError("Client is not connected.")
        sftp = self._client.open_sftp()
        try:
            sftp.put(local_path, remote_path)
        finally:
            sftp.close()

    async def download_file(self, remote_path: str, local_path: str) -> None:
        """Download a file using SFTP."""
        if not self.is_connected:
            await self.connect()

        logger.info(
            "Downloading file via SFTP",
            host=self._host,
            remote=remote_path,
            local=local_path,
        )
        try:
            await asyncio.to_thread(self._sync_download_file, remote_path, local_path)
        except Exception as e:
            logger.error("SFTP download failed", error=str(e))
            raise ConnectionFailedError(f"SFTP download failed: {str(e)}")

    def _sync_download_file(self, remote_path: str, local_path: str) -> None:
        if not self._client:
            raise ConnectionFailedError("Client is not connected.")
        sftp = self._client.open_sftp()
        try:
            sftp.get(remote_path, local_path)
        finally:
            sftp.close()

# tests/infrastructure/test_connectors.py
"""Unit tests for the Connector Framework (LinuxSSHConnector & HostingerConnector)."""

import socket
from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import paramiko  # type: ignore[import-untyped]
import pytest

from src.domain.exceptions import (
    AuthenticationFailedError,
    CommandExecutionFailedError,
    ConnectionFailedError,
    ConnectorTimeoutError,
)
from src.infrastructure.connectors.hostinger.hostinger_connector import (
    HostingerConnector,
)
from src.infrastructure.connectors.linux.ssh_connector import LinuxSSHConnector


@pytest.fixture
def mock_ssh_client():
    """Fixture to mock Paramiko SSHClient."""
    with patch("paramiko.SSHClient") as mock_class:
        mock_inst = MagicMock()
        mock_class.return_value = mock_inst

        # Mock Transport
        mock_transport = MagicMock()
        mock_inst.get_transport.return_value = mock_transport
        mock_transport.is_active.return_value = True

        # Mock Channel
        mock_channel = MagicMock()
        mock_transport.open_session.return_value = mock_channel
        mock_channel.exit_status_ready.return_value = True
        mock_channel.closed = False
        mock_channel.get_exit_status.return_value = 0
        mock_channel.recv.return_value = b"mock stdout output"
        mock_channel.recv_stderr.return_value = b""
        mock_channel.recv_ready.side_effect = [True, False]
        mock_channel.recv_stderr_ready.side_effect = [False]

        # Mock SFTP
        mock_sftp = MagicMock()
        mock_inst.open_sftp.return_value = mock_sftp

        yield mock_inst


@pytest.mark.asyncio
async def test_ssh_connector_connection_success(mock_ssh_client):
    """Verify successful SSH connection and command execution."""
    connector = LinuxSSHConnector(
        host="192.168.1.10",
        username="test-user",
        password="test-password",
        retries=1,
    )

    # Connect
    await connector.connect()
    assert connector.is_connected is True
    mock_ssh_client.connect.assert_called_once_with(
        hostname="192.168.1.10",
        port=22,
        username="test-user",
        password="test-password",
        pkey=None,
        timeout=10.0,
        banner_timeout=10.0,
        auth_timeout=10.0,
    )

    # Command Execution
    output = await connector.execute("uptime")
    assert output == "mock stdout output"

    # Disconnect
    await connector.disconnect()
    assert connector.is_connected is False
    mock_ssh_client.close.assert_called_once()


@pytest.mark.asyncio
async def test_ssh_connector_auth_failure(mock_ssh_client):
    """Verify connector raises AuthenticationFailedError on auth failure."""
    mock_ssh_client.connect.side_effect = paramiko.AuthenticationException(
        "Authentication failed."
    )

    connector = LinuxSSHConnector(
        host="192.168.1.10",
        username="test-user",
        password="wrong-password",
        retries=1,
    )

    with pytest.raises(AuthenticationFailedError) as exc:
        await connector.connect()
    assert "Authentication failed" in str(exc.value)
    assert connector.is_connected is False


@pytest.mark.asyncio
async def test_ssh_connector_timeout(mock_ssh_client):
    """Verify connector raises ConnectorTimeoutError on socket timeout."""
    mock_ssh_client.connect.side_effect = socket.timeout("Connection timed out")

    connector = LinuxSSHConnector(
        host="192.168.1.10",
        username="test-user",
        password="password",
        retries=1,
    )

    with pytest.raises(ConnectorTimeoutError) as exc:
        await connector.connect()
    assert "Connection timeout" in str(exc.value)


@pytest.mark.asyncio
async def test_ssh_connector_command_execution_failure(mock_ssh_client):
    """Verify CommandExecutionFailedError on non-zero command return code."""
    connector = LinuxSSHConnector(
        host="192.168.1.10", username="test-user", password="password", retries=1
    )

    # Mock command exit status as 1 (error) and stderr output
    mock_channel = mock_ssh_client.get_transport().open_session.return_value
    mock_channel.get_exit_status.return_value = 1
    mock_channel.recv.return_value = b""
    mock_channel.recv_stderr.return_value = b"bash: command not found"
    mock_channel.recv_stderr_ready.side_effect = [True, False]

    await connector.connect()

    with pytest.raises(CommandExecutionFailedError) as exc:
        await connector.execute("invalid_command")
    assert "Command returned exit status 1" in str(exc.value)
    assert "bash: command not found" in str(exc.value)


@pytest.mark.asyncio
async def test_ssh_connector_file_transfer(mock_ssh_client):
    """Verify SFTP file uploads and downloads."""
    connector = LinuxSSHConnector(
        host="192.168.1.10", username="test-user", password="password", retries=1
    )
    await connector.connect()

    mock_sftp = mock_ssh_client.open_sftp.return_value

    await connector.upload_file("local.txt", "remote.txt")
    mock_sftp.put.assert_called_once_with("local.txt", "remote.txt")

    await connector.download_file("remote.txt", "local.txt")
    mock_sftp.get.assert_called_once_with("remote.txt", "local.txt")


@pytest.mark.asyncio
async def test_hostinger_connector_delegation(mock_ssh_client):
    """Verify HostingerConnector delegates shell operations to its internal SSH client."""
    connector = HostingerConnector(
        host="hostinger-vps",
        username="hostinger-user",
        password="hostinger-password",
        api_base_url="https://mock-api.hostinger.com",
        api_token="mock-token",
    )

    with patch.object(
        connector._ssh_connector, "connect", new_callable=AsyncMock
    ) as mock_connect:
        await connector.connect()
        mock_connect.assert_called_once()

    with patch.object(
        connector._ssh_connector, "execute", new_callable=AsyncMock
    ) as mock_execute:
        await connector.execute("df -h")
        mock_execute.assert_called_once_with("df -h", None)

    with patch.object(
        connector._ssh_connector, "disconnect", new_callable=AsyncMock
    ) as mock_disconnect:
        await connector.disconnect()
        mock_disconnect.assert_called_once()


@pytest.mark.asyncio
async def test_hostinger_connector_api_calls():
    """Verify HostingerConnector performs correct HTTP requests to Hostinger REST APIs."""
    connector = HostingerConnector(
        host="hostinger-vps",
        username="hostinger-user",
        password="hostinger-password",
        api_base_url="https://mock-api.hostinger.com",
        api_token="mock-token",
    )

    # Initialize client manually or mock connect's SSH call
    with patch.object(connector._ssh_connector, "connect", new_callable=AsyncMock):
        await connector.connect()

    # Mock HTTP client responses
    mock_response_reboot = MagicMock()
    mock_response_reboot.status_code = 200

    mock_response_details = MagicMock()
    mock_response_details.status_code = 200
    mock_response_details.json.return_value = {"vps_id": "vps_123", "status": "running"}

    with (
        patch.object(connector._client, "post", new_callable=AsyncMock) as mock_post,
        patch.object(connector._client, "get", new_callable=AsyncMock) as mock_get,
    ):
        mock_post.return_value = mock_response_reboot
        mock_get.return_value = mock_response_details

        await connector.reboot_vps("vps_123")
        mock_post.assert_called_once_with("/vps/vps_123/reboot")

        details = await connector.get_vps_details("vps_123")
        mock_get.assert_called_once_with("/vps/vps_123")
        assert details == {"vps_id": "vps_123", "status": "running"}

    # Cleanup client
    await connector.disconnect()

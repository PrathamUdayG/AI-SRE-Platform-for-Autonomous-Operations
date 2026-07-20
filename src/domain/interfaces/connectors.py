# src/domain/interfaces/connectors.py
"""Domain interface contracts for infrastructure connectors."""

from abc import ABC, abstractmethod
from enum import Enum
from typing import Optional


class ConnectorType(str, Enum):
    """Supported connector types in the AI-SRE Platform."""

    SSH = "ssh"
    HOSTINGER = "hostinger"
    AWS = "aws"
    AZURE = "azure"
    DOCKER = "docker"
    KUBERNETES = "kubernetes"


class IConnection(ABC):
    """Contract for managing the lifecycle of an infrastructure connection."""

    @abstractmethod
    async def connect(self) -> None:
        """Establish connection to the remote resource."""
        pass

    @abstractmethod
    async def disconnect(self) -> None:
        """Close connection to the remote resource."""
        pass

    @property
    @abstractmethod
    def is_connected(self) -> bool:
        """Check if the connector is currently connected."""
        pass


class ICommandExecutor(ABC):
    """Contract for executing commands on a remote resource."""

    @abstractmethod
    async def execute(self, command: str, timeout: Optional[float] = None) -> str:
        """Execute a shell command and return the raw output as a string.

        Raises:
            CommandExecutionFailedError: If execution fails or returns non-zero.
            ConnectorTimeoutError: If execution times out.
        """
        pass


class IFileTransfer(ABC):
    """Contract for transferring files to/from a remote resource."""

    @abstractmethod
    async def upload_file(self, local_path: str, remote_path: str) -> None:
        """Upload a local file to a remote destination path."""
        pass

    @abstractmethod
    async def download_file(self, remote_path: str, local_path: str) -> None:
        """Download a remote file to a local destination path."""
        pass


class IConnector(IConnection, ICommandExecutor, IFileTransfer, ABC):
    """Combined contract for full connection, command execution, and file transfer."""

    @property
    @abstractmethod
    def type(self) -> ConnectorType:
        """Get the type of this connector."""
        pass

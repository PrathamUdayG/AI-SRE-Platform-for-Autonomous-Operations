"""
-------------------------------------------------------
File:
command_executor.py

Purpose:
Defines the abstract interface for executing system commands.

Why this file exists:
By using an abstract execution contract, collectors only depend on the interface, allowing easy mocking in unit tests and supporting future cross-platform executor integrations (Windows, cloud APIs) without modifying collector logic.

Responsibilities:
- Define the contract for executing shell/binary commands asynchronously.

Used By:
- All Metric Collectors
- LinuxCommandExecutor

Depends On:
- src.domain.executor.command_result.CommandResult
-------------------------------------------------------
"""

from abc import ABC, abstractmethod
from typing import List, Optional

from src.domain.executor.command_result import CommandResult


class CommandExecutor(ABC):
    """
    Why this class exists:
    Provides the execution interface that all collectors use to run operations.

    Responsibility:
    Define a generic, asynchronous method for running commands with timeout limits.

    Who uses it:
    Collectors to gather system telemetry.
    """

    @abstractmethod
    async def execute(
        self,
        command: str,
        arguments: Optional[List[str]] = None,
        timeout: Optional[float] = None,
    ) -> CommandResult:
        """
        Asynchronously execute a system command and return the strongly-typed CommandResult.

        Args:
            command (str): Base executable name (e.g. "df").
            arguments (Optional[List[str]]): Arguments list for execution.
            timeout (Optional[float]): Time limit in seconds before aborting the execution.

        Returns:
            CommandResult: Structured outcomes containing exit code, stdout, stderr, and timings.
        """
        pass

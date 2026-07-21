"""
-------------------------------------------------------
File:
command_validator.py

Purpose:
Validates that commands and arguments are strictly read-only and safe to execute.

Why this file exists:
The collector agent must be strictly read-only. We need a security policy layer to intercept and reject any potentially destructive operations (e.g., rm, kill, systemctl restart) before execution.

Responsibilities:
- Enforce command whitelist rules.
- Reject dangerous shell metacharacters to prevent command injection.
- Validate specific arguments for multi-purpose CLI tools (like systemctl, docker, kubectl) to block modification verbs.

Used By:
- CommandExecutor
- LinuxCommandExecutor

Depends On:
- src.domain.exceptions.PolicyViolationError
-------------------------------------------------------
"""

import re
from abc import ABC, abstractmethod
from typing import List, Set

from src.domain.exceptions import PolicyViolationError


class CommandValidator(ABC):
    """
    Why this class exists:
    Defines the contract for command safety validation.

    Responsibility:
    Provide an abstract validation interface for validating commands and arguments.

    Who uses it:
    Command executors before invoking system subprocess APIs.
    """

    @abstractmethod
    def validate(self, command: str, arguments: List[str]) -> None:
        """
        Validate command and its arguments. Raise PolicyViolationError if invalid.

        Args:
            command (str): Base executable name (e.g., "df").
            arguments (List[str]): Arguments passed to command.

        Raises:
            PolicyViolationError: If command or args fail safety verification.
        """
        pass


class ReadOnlyCommandValidator(CommandValidator):
    """
    Why this class exists:
    A concrete implementation of CommandValidator that enforces read-only access on Linux.

    Responsibility:
    Maintains a whitelist of safe base commands and filters out forbidden verbs/characters.

    Who uses it:
    Linux command execution frameworks.
    """

    # Core allowed commands
    ALLOWED_COMMANDS: Set[str] = {
        "cat",
        "df",
        "ps",
        "ss",
        "ip",
        "hostname",
        "uname",
        "journalctl",
        "docker",
        "kubectl",
        "free",
        "uptime",
        "lscpu",
        "lsblk",
        "systemctl",
        "hostnamectl",
        "tail",
    }



    # Shell redirection/execution injection characters to block
    FORBIDDEN_CHARS_PATTERN = re.compile(r"[;&|<>`\$\n\r\(\)]")

    # Verbs that modify state inside allowed CLI utilities
    FORBIDDEN_VERBS: Set[str] = {
        # General state modification
        "restart",
        "stop",
        "start",
        "enable",
        "disable",
        "mask",
        "unmask",
        "reload",
        "reset-failed",
        "kill",
        "pkill",
        "run",
        "exec",
        "rm",
        "delete",
        "apply",
        "create",
        "set",
        "patch",
        "scale",
        "autoscale",
        "expose",
        "replace",
        "update",
        "build",
        "push",
        "pull",
        "tag",
        "import",
        "load",
        "save",
        "login",
        "logout",
        "write",
    }

    def validate(self, command: str, arguments: List[str]) -> None:
        """
        Perform multi-tier validation checks on the command name and arguments list.
        """
        clean_command = command.strip().lower()

        # 1. Base command must be strictly inside the allowed whitelist
        if clean_command not in self.ALLOWED_COMMANDS:
            raise PolicyViolationError(
                f"Command '{command}' is not whitelisted for read-only execution."
            )

        # 2. Check for shell metacharacters in command or any arguments
        for arg in arguments:
            if self.FORBIDDEN_CHARS_PATTERN.search(arg):
                raise PolicyViolationError(
                    f"Shell metacharacters are forbidden in arguments: '{arg}'"
                )

        # 3. Specific validation for CLI tools that support both read and write operations
        for arg in arguments:
            # Normalize argument for comparison (e.g. strip leading dashes if checking verbs)
            clean_arg = arg.strip().lower()
            if clean_arg in self.FORBIDDEN_VERBS:
                raise PolicyViolationError(
                    f"Argument verb '{arg}' violates the read-only execution policy."
                )

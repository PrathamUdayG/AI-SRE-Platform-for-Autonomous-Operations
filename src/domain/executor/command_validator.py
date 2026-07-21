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

    # Shift from Negative Blocking to Positive Allow-listing:
    # Instead of maintaining an incomplete global FORBIDDEN_VERBS set that is prone to evasion 
    # (e.g., missing specific verbs or context), we now use a strict positive allow-list 
    # of sub-commands via ALLOWED_SUBCOMMANDS. This ensures that only explicitly permitted 
    # read-only sub-commands can be executed for multi-purpose CLI utilities.
    ALLOWED_SUBCOMMANDS = {
        "systemctl": {
            "status",
            "show",
            "list-units",
            "list-unit-files",
            "is-active",
            "is-enabled",
            "get-default",
            "cat",
            "is-failed",
            "list-dependencies",
            "list-machines",
        },
        "docker": {
            "ps",
            "images",
            "inspect",
            "logs",
            "stats",
            "top",
            "version",
            "history",
            "diff",
            "port",
            "events",
            "system df",
        },
        "kubectl": {
            "get",
            "describe",
            "logs",
            "top",
            "version",
            "explain",
            "api-resources",
            "api-versions",
            "cluster-info",
            "config view",
            "auth can-i",
        },
        "ip": {
            "addr show",
            "link show",
            "route show",
            "neigh show",
            "addr",
            "link",
            "route",
            "neigh",
        },
        "hostnamectl": {
            "status",
            None,
        },
    }

    # Shell redirection/execution injection characters to block
    FORBIDDEN_CHARS_PATTERN = re.compile(r"[;&|<>`\$\n\r\(\)]")

    # Forbidden journalctl options that mutate state or trigger system changes
    FORBIDDEN_JOURNALCTL_OPTIONS: Set[str] = {
        "--rotate",
        "--vacuum-size",
        "--vacuum-time",
        "--vacuum-files",
    }

    def _extract_subcommand(self, arguments: List[str]) -> str | None:
        """
        Extracts the primary sub-command from a list of arguments.
        
        This method skips all leading flags (arguments starting with '-' or '--')
        to find the first non-flag argument. For multi-level sub-commands, it combines
        up to three consecutive non-flag arguments into a single space-joined string.
        """
        first_non_flag_idx = -1
        for idx, arg in enumerate(arguments):
            if not arg.startswith("-"):
                first_non_flag_idx = idx
                break

        if first_non_flag_idx == -1:
            return None

        sub_parts = []
        for arg in arguments[first_non_flag_idx:]:
            if arg.startswith("-"):
                break
            sub_parts.append(arg)
            if len(sub_parts) == 3:
                break

        return " ".join(sub_parts)

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

        # 3. Specific validation for CLI tools that support both read and write operations.
        # We use a positive allow-list (ALLOWED_SUBCOMMANDS) to verify that the extracted
        # subcommand matches a permitted pattern.
        if clean_command in self.ALLOWED_SUBCOMMANDS:
            subcommand = self._extract_subcommand(arguments)
            allowed_set = self.ALLOWED_SUBCOMMANDS[clean_command]

            if subcommand is None:
                if None not in allowed_set:
                    raise PolicyViolationError(
                        f"Command '{command}' requires a sub-command."
                    )
            else:
                # Match the extracted subcommand or any of its word-joined prefixes
                words = subcommand.split()
                matched = False
                for i in range(len(words), 0, -1):
                    prefix = " ".join(words[:i])
                    if prefix in allowed_set:
                        # Extra security check for 'ip' command: block specific modifying verbs
                        # as an additional safety net against state-changing verbs
                        if clean_command == "ip":
                            for arg in arguments:
                                clean_arg = arg.strip().lower()
                                if clean_arg in {"add", "del", "set", "change", "replace", "flush"}:
                                    raise PolicyViolationError(
                                        f"Verb '{arg}' is not allowed for command 'ip'."
                                    )
                        matched = True
                        break

                if not matched:
                    raise PolicyViolationError(
                        f"Sub-command '{subcommand}' violates the read-only execution policy."
                    )

        # 4. journalctl validation
        if clean_command == "journalctl":
            for arg in arguments:
                # Perform exact prefix matching for the forbidden options.
                # Since options like --vacuum-size can be passed with an equals sign,
                # e.g., --vacuum-size=100M, we use startswith on the argument.
                for opt in self.FORBIDDEN_JOURNALCTL_OPTIONS:
                    if arg.startswith(opt):
                        raise PolicyViolationError(
                            f"Forbidden journalctl option '{arg}' is not allowed."
                        )

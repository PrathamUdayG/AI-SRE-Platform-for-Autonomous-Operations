"""
-------------------------------------------------------
File:
__init__.py

Purpose:
Package entry point for the command execution Domain Layer interfaces and models.

Why this file exists:
Exposes CommandResult, CommandExecutor, CommandValidator, and ReadOnlyCommandValidator for cleaner package-level imports.

Responsibilities:
- Re-export executor contracts and models.
-------------------------------------------------------
"""

from src.domain.executor.command_executor import CommandExecutor
from src.domain.executor.command_result import CommandResult
from src.domain.executor.command_validator import (
    CommandValidator,
    ReadOnlyCommandValidator,
)

__all__ = [
    "CommandExecutor",
    "CommandResult",
    "CommandValidator",
    "ReadOnlyCommandValidator",
]

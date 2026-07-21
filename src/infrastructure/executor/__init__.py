"""
-------------------------------------------------------
File:
__init__.py

Purpose:
Package entry point for the Infrastructure command executor.

Why this file exists:
Allows clean, consistent module imports for the Linux Command Executor implementation.

Responsibilities:
- Expose LinuxCommandExecutor.
-------------------------------------------------------
"""

from src.infrastructure.executor.linux_command_executor import LinuxCommandExecutor

__all__ = ["LinuxCommandExecutor"]

"""
-------------------------------------------------------
File:
command_result.py

Purpose:
Model representing the structured execution result of a Linux command.

Why this file exists:
Every command executed by a collector must return a strongly typed, structured object containing stdout, stderr, exit code, and metadata, rather than raw strings or tuples.

Responsibilities:
- Encapsulate exit code, stdout, stderr, execution duration, and timeouts.
- Determine execution success based on exit code and safety violations.

Used By:
- CommandExecutor
- LinuxCommandExecutor
- All Metric Collectors

Notes:
This file belongs to the Domain Layer as it specifies a core data contract for command outcomes.
-------------------------------------------------------
"""

from datetime import datetime
from typing import List
from pydantic import BaseModel, Field


class CommandResult(BaseModel):
    """
    Why this class exists:
    Holds the complete outcomes and metadata of a command execution.

    Responsibility:
    Ensure type safety and structured formatting for command output fields.

    Who uses it:
    Infrastructure executors to return results, collectors to parse outputs.
    """

    command: str = Field(description="The executable file name that was run")
    arguments: List[str] = Field(default_factory=list, description="Arguments passed to the executable")
    stdout: str = Field(description="Captured standard output stream")
    stderr: str = Field(description="Captured standard error stream")
    exit_code: int = Field(description="Process exit status code")
    execution_time_ms: int = Field(description="Time elapsed during execution in milliseconds")
    timed_out: bool = Field(description="Flag indicating if the execution exceeded limits and timed out")
    success: bool = Field(description="Flag indicating whether execution succeeded (exit code 0 and no timeout)")
    timestamp: datetime = Field(description="UTC timestamp when command execution completed")

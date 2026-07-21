"""
-------------------------------------------------------
File:
linux_command_executor.py

Purpose:
Infrastructure implementation of CommandExecutor for executing local Linux commands.

Why this file exists:
Provides the actual asynchronous execution of OS-level processes. It keeps collectors safe by validating every command prior to execution, captures output stream statistics, and manages timeouts cleanly without blocking the event loop.

Responsibilities:
- Wrap asyncio.create_subprocess_exec.
- Inject and run CommandValidator.
- Capture execution metrics (exit code, stdout, stderr, execution time).
- Handle execution errors gracefully (FileNotFoundError, PermissionError, timeouts).

Used By:
- All Metric Collectors

Depends On:
- src.domain.executor.command_executor.CommandExecutor
- src.domain.executor.command_validator.CommandValidator
- src.domain.executor.command_result.CommandResult
-------------------------------------------------------
"""

import asyncio
import time
from datetime import datetime, timezone
from typing import List, Optional
import structlog

from src.domain.exceptions import PolicyViolationError
from src.domain.executor.command_executor import CommandExecutor
from src.domain.executor.command_result import CommandResult
from src.domain.executor.command_validator import CommandValidator

logger = structlog.get_logger(__name__)


class LinuxCommandExecutor(CommandExecutor):
    """
    Why this class exists:
    Executes Linux binaries asynchronously inside the Infrastructure layer.

    Responsibility:
    Runs commands safely without using shells, measures duration, decodes outputs,
    and returns a structured CommandResult.

    Who uses it:
    Collectors and host health monitors.
    """

    def __init__(self, validator: CommandValidator) -> None:
        """
        Initialize LinuxCommandExecutor with a command validator.

        Args:
            validator (CommandValidator): Validator to check command execution safety.
        """
        self._validator = validator

    async def execute(
        self,
        command: str,
        arguments: Optional[List[str]] = None,
        timeout: Optional[float] = None,
    ) -> CommandResult:
        """
        Execute command via create_subprocess_exec after validating it.

        Args:
            command (str): Executable path or binary name.
            arguments (Optional[List[str]]): Command argument list.
            timeout (Optional[float]): Time limit in seconds.

        Returns:
            CommandResult: Structured result.
        """
        args = arguments or []
        start_time = time.perf_counter()

        # 1. Security policy validation
        try:
            self._validator.validate(command, args)
        except PolicyViolationError as e:
            logger.warning(
                "Command validation failed. Security Policy violation.",
                command=command,
                arguments=args,
                error=str(e),
            )
            execution_time_ms = int((time.perf_counter() - start_time) * 1000)
            return CommandResult(
                command=command,
                arguments=args,
                stdout="",
                stderr=f"Security Policy Violation: {str(e)}",
                exit_code=-1,
                execution_time_ms=execution_time_ms,
                timed_out=False,
                success=False,
                timestamp=datetime.now(timezone.utc),
            )

        # 2. Asynchronous process execution
        process = None
        stdout = ""
        stderr = ""
        exit_code = -1
        timed_out = False

        try:
            process = await asyncio.create_subprocess_exec(
                command,
                *args,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )

            if timeout is not None:
                stdout_bytes, stderr_bytes = await asyncio.wait_for(
                    process.communicate(), timeout=timeout
                )
            else:
                stdout_bytes, stderr_bytes = await process.communicate()

            stdout = stdout_bytes.decode("utf-8", errors="replace")
            stderr = stderr_bytes.decode("utf-8", errors="replace")
            exit_code = process.returncode if process.returncode is not None else 0

        except asyncio.TimeoutError:
            logger.error(
                "Command execution timed out",
                command=command,
                arguments=args,
                timeout=timeout,
            )
            timed_out = True
            if process:
                try:
                    process.kill()
                except OSError as os_err:
                    logger.debug("Failed to kill process after timeout", error=str(os_err))
                await process.wait()  # Clean up process resources
            stderr = f"Execution timed out after {timeout} seconds."
            exit_code = -1

        except FileNotFoundError as e:
            logger.error("Executable file not found", command=command, error=str(e))
            stderr = f"Command not found: {str(e)}"
            exit_code = 127

        except PermissionError as e:
            logger.error("Permission denied to run executable", command=command, error=str(e))
            stderr = f"Permission denied: {str(e)}"
            exit_code = 126

        except OSError as e:
            logger.error("OS level error during execution", command=command, error=str(e))
            stderr = f"OS Error: {str(e)}"
            exit_code = -1

        except Exception as e:
            logger.critical("Unexpected exception in command executor", command=command, error=str(e))
            stderr = f"Unexpected Exception: {str(e)}"
            exit_code = -1

        execution_time_ms = int((time.perf_counter() - start_time) * 1000)
        success = (exit_code == 0) and not timed_out

        logger.debug(
            "Command execution finished",
            command=command,
            exit_code=exit_code,
            execution_time_ms=execution_time_ms,
            success=success,
        )

        return CommandResult(
            command=command,
            arguments=args,
            stdout=stdout,
            stderr=stderr,
            exit_code=exit_code,
            execution_time_ms=execution_time_ms,
            timed_out=timed_out,
            success=success,
            timestamp=datetime.now(timezone.utc),
        )

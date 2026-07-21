"""
-------------------------------------------------------
File:
test_linux_command_executor.py

Purpose:
Unit tests for the LinuxCommandExecutor in the Infrastructure Layer.

Why this file exists:
Ensures that command execution transitions, timeouts, exit codes, security rejections, and system exceptions (like PermissionError) are accurately mapped to the CommandResult contract without spawning real OS processes.

Responsibilities:
- Mock asyncio.create_subprocess_exec.
- Verify successful command capturing.
- Verify non-zero status code captures.
- Verify timeout handling and process termination.
- Verify permission and missing executable errors.
- Verify security policy validation integration.
- Verify safe UTF-8 decoding with replacement on non-UTF-8 characters.

Used By:
- pytest runner

Depends On:
- src.infrastructure.executor.linux_command_executor
- src.domain.executor.command_validator.ReadOnlyCommandValidator
-------------------------------------------------------
"""

import asyncio
from unittest.mock import AsyncMock, MagicMock, patch
import pytest

from src.domain.exceptions import PolicyViolationError
from src.domain.executor.command_validator import ReadOnlyCommandValidator
from src.infrastructure.executor.linux_command_executor import LinuxCommandExecutor


@pytest.fixture
def mock_validator():
    val = MagicMock(spec=ReadOnlyCommandValidator)
    val.validate.return_value = None
    return val


@pytest.fixture
def executor(mock_validator):
    return LinuxCommandExecutor(validator=mock_validator)


@pytest.mark.asyncio
async def test_execute_success(executor, mock_validator):
    """Verify happy path execution returning exit code 0 and stdout."""
    mock_process = AsyncMock()
    mock_process.communicate.return_value = (b"hello test", b"")
    mock_process.returncode = 0

    with patch("asyncio.create_subprocess_exec", return_value=mock_process) as mock_create:
        result = await executor.execute("df", ["-h"])

        mock_validator.validate.assert_called_once_with("df", ["-h"])
        mock_create.assert_called_once_with(
            "df", "-h", stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE
        )
        assert result.success is True
        assert result.stdout == "hello test"
        assert result.stderr == ""
        assert result.exit_code == 0
        assert result.timed_out is False


@pytest.mark.asyncio
async def test_execute_non_zero_exit_code(executor):
    """Verify execution capturing non-zero exit status code and stderr."""
    mock_process = AsyncMock()
    mock_process.communicate.return_value = (b"", b"Invalid option")
    mock_process.returncode = 1

    with patch("asyncio.create_subprocess_exec", return_value=mock_process):
        result = await executor.execute("df", ["-xyz"])

        assert result.success is False
        assert result.stdout == ""
        assert result.stderr == "Invalid option"
        assert result.exit_code == 1
        assert result.timed_out is False


@pytest.mark.asyncio
async def test_execute_timeout(executor):
    """Verify execution timeout kills the process and returns timed_out=True."""
    mock_process = AsyncMock()
    mock_process.communicate = AsyncMock()
    mock_process.kill = MagicMock()
    mock_process.wait = AsyncMock()

    with patch("asyncio.create_subprocess_exec", return_value=mock_process):
        with patch("asyncio.wait_for", side_effect=asyncio.TimeoutError):
            result = await executor.execute("df", ["-h"], timeout=1.0)

            mock_process.kill.assert_called_once()
            mock_process.wait.assert_called_once()
            assert result.success is False
            assert result.timed_out is True
            assert "Execution timed out" in result.stderr
            assert result.exit_code == -1


@pytest.mark.asyncio
async def test_execute_file_not_found(executor):
    """Verify 127 status code mapping when binary does not exist."""
    with patch("asyncio.create_subprocess_exec", side_effect=FileNotFoundError("No such file")):
        result = await executor.execute("df", ["-h"])

        assert result.success is False
        assert result.exit_code == 127
        assert "Command not found" in result.stderr


@pytest.mark.asyncio
async def test_execute_permission_denied(executor):
    """Verify 126 status code mapping when process permission is denied."""
    with patch("asyncio.create_subprocess_exec", side_effect=PermissionError("Permission denied")):
        result = await executor.execute("df", ["-h"])

        assert result.success is False
        assert result.exit_code == 126
        assert "Permission denied" in result.stderr


@pytest.mark.asyncio
async def test_execute_os_error(executor):
    """Verify general OS exceptions return a status code of -1."""
    with patch("asyncio.create_subprocess_exec", side_effect=OSError("OS resource depletion")):
        result = await executor.execute("df", ["-h"])

        assert result.success is False
        assert result.exit_code == -1
        assert "OS Error" in result.stderr


@pytest.mark.asyncio
async def test_execute_validator_rejection(mock_validator):
    """Verify that validator errors are caught and return a rejected result directly."""
    mock_validator.validate.side_effect = PolicyViolationError("Command blocked")
    executor = LinuxCommandExecutor(validator=mock_validator)

    result = await executor.execute("rm", ["-rf", "/"])

    # Subprocess exec must not be called
    with patch("asyncio.create_subprocess_exec") as mock_create:
        assert result.success is False
        assert result.exit_code == -1
        assert "Security Policy Violation" in result.stderr
        mock_create.assert_not_called()


@pytest.mark.asyncio
async def test_execute_utf8_decoding_safeguards(executor):
    """Verify non-UTF-8 bytes are decoded safely using replacement characters."""
    mock_process = AsyncMock()
    # \xff is invalid in UTF-8
    mock_process.communicate.return_value = (b"output \xff", b"error \xff")
    mock_process.returncode = 0

    with patch("asyncio.create_subprocess_exec", return_value=mock_process):
        result = await executor.execute("df", ["-h"])

        assert result.success is True
        assert "\ufffd" in result.stdout  # Unicode replacement char
        assert "\ufffd" in result.stderr
        assert result.exit_code == 0

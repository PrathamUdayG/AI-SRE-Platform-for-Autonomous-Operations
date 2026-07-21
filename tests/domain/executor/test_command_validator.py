"""
-------------------------------------------------------
File:
test_command_validator.py

Purpose:
Tests for the ReadOnlyCommandValidator in the Domain Layer.

Why this file exists:
Ensures the security policy is strictly enforced. It verifies that allowed read-only commands succeed validation, while forbidden commands, metacharacters, or state-changing action verbs are blocked.

Responsibilities:
- Verify allowed commands pass validation.
- Verify non-whitelisted commands raise PolicyViolationError.
- Verify forbidden shell injection characters raise PolicyViolationError.
- Verify state-changing CLI arguments raise PolicyViolationError.

Used By:
- pytest runner

Depends On:
- src.domain.executor.command_validator
- src.domain.exceptions.PolicyViolationError
-------------------------------------------------------
"""

import pytest
from src.domain.exceptions import PolicyViolationError
from src.domain.executor.command_validator import ReadOnlyCommandValidator


@pytest.fixture
def validator():
    return ReadOnlyCommandValidator()


def test_allowed_commands(validator):
    """Verify that allowed read-only commands and safe arguments pass validation."""
    # Simple valid executions
    validator.validate("df", ["-h"])
    validator.validate("free", ["-m"])
    validator.validate("ps", ["aux"])
    validator.validate("ip", ["addr", "show"])
    validator.validate("uptime", [])


def test_disallowed_commands(validator):
    """Verify that non-whitelisted commands are strictly blocked."""
    disallowed = ["rm", "mv", "cp", "kill", "pkill", "apt", "yum", "dnf", "shutdown", "reboot"]
    for cmd in disallowed:
        with pytest.raises(PolicyViolationError) as excinfo:
            validator.validate(cmd, [])
        assert "not whitelisted" in str(excinfo.value)


def test_forbidden_shell_metacharacters(validator):
    """Verify that any argument containing shell metacharacters is rejected to prevent injection."""
    metachars = [";", "&", "|", "<", ">", "`", "$", "\n", "\r", "(", ")"]
    for char in metachars:
        with pytest.raises(PolicyViolationError) as excinfo:
            validator.validate("df", [f"-h{char}"])
        assert "Shell metacharacters are forbidden" in str(excinfo.value)


def test_forbidden_verbs(validator):
    """Verify that forbidden action verbs (like restart, stop, delete) are blocked."""
    # systemctl restart is blocked
    with pytest.raises(PolicyViolationError) as excinfo:
        validator.validate("systemctl", ["restart", "nginx"])
    assert "violates the read-only execution policy" in str(excinfo.value)

    # docker rm is blocked
    with pytest.raises(PolicyViolationError) as excinfo:
        validator.validate("docker", ["rm", "container_id"])
    assert "violates the read-only execution policy" in str(excinfo.value)

    # kubectl delete is blocked
    with pytest.raises(PolicyViolationError) as excinfo:
        validator.validate("kubectl", ["delete", "pod", "mypod"])
    assert "violates the read-only execution policy" in str(excinfo.value)

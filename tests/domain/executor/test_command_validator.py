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


def test_systemctl_validation(validator):
    """Verify positive allow-listing for systemctl."""
    # Allowed sub-commands
    validator.validate("systemctl", ["status", "nginx"])
    validator.validate("systemctl", ["list-units"])
    validator.validate("systemctl", ["cat", "nginx.service"])
    validator.validate("systemctl", ["list-dependencies"])

    # Blocked sub-commands
    for blocked_sub in ["start", "stop", "restart", "enable", "disable", "set-property", "edit", "daemon-reload"]:
        with pytest.raises(PolicyViolationError) as excinfo:
            validator.validate("systemctl", [blocked_sub, "nginx"])
        assert "violates the read-only execution policy" in str(excinfo.value)


def test_docker_validation(validator):
    """Verify positive allow-listing for docker."""
    # Allowed sub-commands
    validator.validate("docker", ["ps"])
    validator.validate("docker", ["system", "df"])
    validator.validate("docker", ["inspect", "container_id"])
    validator.validate("docker", ["logs", "container_id"])

    # Blocked sub-commands
    for blocked_sub in ["run", "exec", "rm", "rmi", "build", "push", "pull", "network", "volume"]:
        with pytest.raises(PolicyViolationError) as excinfo:
            validator.validate("docker", [blocked_sub])
        assert "violates the read-only execution policy" in str(excinfo.value)


def test_kubectl_validation(validator):
    """Verify positive allow-listing for kubectl."""
    # Allowed sub-commands
    validator.validate("kubectl", ["get", "pods"])
    validator.validate("kubectl", ["describe", "node", "my-node"])
    validator.validate("kubectl", ["config", "view"])
    validator.validate("kubectl", ["auth", "can-i", "create", "pods"])

    # Blocked sub-commands
    for blocked_sub in ["apply", "create", "delete", "edit", "patch", "replace"]:
        with pytest.raises(PolicyViolationError) as excinfo:
            validator.validate("kubectl", [blocked_sub, "deployment"])
        assert "violates the read-only execution policy" in str(excinfo.value)

    # Blocked nested config sub-command
    with pytest.raises(PolicyViolationError) as excinfo:
        validator.validate("kubectl", ["config", "set", "current-context", "my-context"])
    assert "violates the read-only execution policy" in str(excinfo.value)


def test_ip_validation(validator):
    """Verify positive allow-listing and verb blocking for ip command."""
    # Allowed sub-commands and arguments
    validator.validate("ip", ["addr"])
    validator.validate("ip", ["addr", "show"])
    validator.validate("ip", ["addr", "show", "dev", "eth0"])
    validator.validate("ip", ["link", "show"])
    validator.validate("ip", ["route", "show"])

    # Blocked modifying verbs
    for blocked_verb in ["add", "del", "set", "change", "replace", "flush"]:
        with pytest.raises(PolicyViolationError) as excinfo:
            validator.validate("ip", ["addr", blocked_verb, "192.168.1.1/24", "dev", "eth0"])
        assert "not allowed for command 'ip'" in str(excinfo.value)


def test_hostnamectl_validation(validator):
    """Verify positive allow-listing for hostnamectl."""
    # Allowed
    validator.validate("hostnamectl", [])
    validator.validate("hostnamectl", ["status"])

    # Blocked
    for blocked_sub in ["set-hostname", "set-icon-name", "set-chassis", "set-deployment", "set-location"]:
        with pytest.raises(PolicyViolationError) as excinfo:
            validator.validate("hostnamectl", [blocked_sub, "new-value"])
        assert "violates the read-only execution policy" in str(excinfo.value)


def test_journalctl_validation(validator):
    """Verify journalctl option filtering."""
    # Allowed options and flags
    validator.validate("journalctl", ["-u", "nginx"])
    validator.validate("journalctl", ["--since", "1 hour ago", "-f"])

    # Blocked options
    for blocked_opt in ["--rotate", "--vacuum-size=100M", "--vacuum-time", "--vacuum-files"]:
        with pytest.raises(PolicyViolationError) as excinfo:
            validator.validate("journalctl", [blocked_opt])
        assert "Forbidden journalctl option" in str(excinfo.value)


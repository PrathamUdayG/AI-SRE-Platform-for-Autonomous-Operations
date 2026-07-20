# tests/infrastructure/test_settings.py
"""Unit tests for Settings, DatabaseSettings, and HostingerSettings."""

import os

import pytest
from pydantic import ValidationError

from src.infrastructure.config.settings import (
    DatabaseSettings,
    HostingerSettings,
    Settings,
)


def test_settings_immutability():
    """Verify that settings and nested settings instances are frozen (immutable)."""
    settings = Settings()

    # Attempt to mutate top-level settings field
    with pytest.raises(ValidationError) as exc_info:
        settings.app_name = "New App Name"
    assert "Instance is frozen" in str(exc_info.value)

    # Attempt to mutate nested database settings field
    with pytest.raises(ValidationError) as exc_info:
        settings.database.url = "postgresql+asyncpg://other_db:5432/db"
    assert "Instance is frozen" in str(exc_info.value)

    # Attempt to mutate nested hostinger settings field
    with pytest.raises(ValidationError) as exc_info:
        settings.hostinger.ssh_host = "192.168.1.1"
    assert "Instance is frozen" in str(exc_info.value)


def test_debug_coercion():
    """Verify debug flag string coercion (on/off/true/false) to boolean."""
    # Test 'on' -> True
    settings_on = Settings(debug="on")
    assert settings_on.debug is True

    # Test 'off' -> False
    settings_off = Settings(debug="off")
    assert settings_off.debug is False

    # Test 'true' -> True
    settings_true = Settings(debug="true")
    assert settings_true.debug is True

    # Test 'false' -> False
    settings_false = Settings(debug="false")
    assert settings_false.debug is False


def test_database_settings_defaults_and_validation():
    """Verify default values and validation constraints for DatabaseSettings."""
    db_settings = DatabaseSettings(_env_file=None)
    assert db_settings.pool_size == 5
    assert db_settings.max_overflow == 10
    assert db_settings.echo is False

    # Test custom values
    custom_db = DatabaseSettings(
        url="postgresql+asyncpg://admin:password@localhost:5432/my_sre_db",
        pool_size=15,
        max_overflow=25,
        echo=True,
    )
    assert (
        str(custom_db.url)
        == "postgresql+asyncpg://admin:password@localhost:5432/my_sre_db"
    )
    assert custom_db.pool_size == 15
    assert custom_db.max_overflow == 25
    assert custom_db.echo is True

    # Test validation failure with invalid url format
    with pytest.raises(ValidationError):
        DatabaseSettings(url="invalid_url_protocol://localhost/db")


def test_hostinger_settings_defaults_and_validation():
    """Verify defaults and structure of HostingerSettings."""
    hostinger = HostingerSettings(_env_file=None)
    assert hostinger.ssh_host == "localhost"
    assert hostinger.ssh_username == "vamshi-ots"
    assert hostinger.ssh_password.get_secret_value() == "L5AslP7GcBMGfPL"

    # Test custom values
    custom_hostinger = HostingerSettings(
        ssh_host="vps.hostinger.com",
        ssh_username="admin-user",
        ssh_password="secure-password-123",
    )
    assert custom_hostinger.ssh_host == "vps.hostinger.com"
    assert custom_hostinger.ssh_username == "admin-user"
    assert custom_hostinger.ssh_password.get_secret_value() == "secure-password-123"


def test_environment_loading(monkeypatch):
    """Verify that configuration parses correct values from system environment."""
    monkeypatch.setenv("AI_SRE_APP_NAME", "Test-SRE-Engine")
    monkeypatch.setenv("AI_SRE_DEBUG", "on")
    monkeypatch.setenv(
        "DATABASE_URL", "postgresql+asyncpg://postgres:postgres@localhost:5432/testdb"
    )
    monkeypatch.setenv("AI_SRE_HOSTINGER__SSH_USERNAME", "env-ssh-user")

    # Instantiate Settings to parse monkeypatched env variables
    settings = Settings()

    assert settings.app_name == "Test-SRE-Engine"
    assert settings.debug is True
    assert (
        str(settings.database.url)
        == "postgresql+asyncpg://postgres:postgres@localhost:5432/testdb"
    )
    assert settings.hostinger.ssh_username == "env-ssh-user"

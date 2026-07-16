import pytest
from pydantic import ValidationError
from src.infrastructure.config.settings import Settings, get_settings


def test_settings_immutability():
    # Attempt to load settings with basic credentials
    settings = Settings(
        database={
            "host": "localhost",
            "username": "postgres",
            "password": "password",
            "database": "ai_sre",
        },
        redis={
            "host": "localhost",
        },
        secret_key="my_secret_key"
    )
    
    # Assert that we cannot modify fields at runtime
    with pytest.raises(ValidationError) as exc_info:
        settings.app_name = "New App Name"
    assert "Instance is frozen" in str(exc_info.value)

    with pytest.raises(ValidationError) as exc_info:
        settings.database.host = "other-host"
    assert "Instance is frozen" in str(exc_info.value)


def test_debug_coercion():
    # Test 'on' -> True
    settings_on = Settings(
        database={
            "host": "localhost",
            "username": "postgres",
            "password": "password",
            "database": "ai_sre",
        },
        redis={
            "host": "localhost",
        },
        secret_key="my_secret_key",
        debug="on"
    )
    assert settings_on.debug is True

    # Test 'off' -> False
    settings_off = Settings(
        database={
            "host": "localhost",
            "username": "postgres",
            "password": "password",
            "database": "ai_sre",
        },
        redis={
            "host": "localhost",
        },
        secret_key="my_secret_key",
        debug="off"
    )
    assert settings_off.debug is False

    # Test boolean True/False
    settings_bool = Settings(
        database={
            "host": "localhost",
            "username": "postgres",
            "password": "password",
            "database": "ai_sre",
        },
        redis={
            "host": "localhost",
        },
        secret_key="my_secret_key",
        debug=True
    )
    assert settings_bool.debug is True

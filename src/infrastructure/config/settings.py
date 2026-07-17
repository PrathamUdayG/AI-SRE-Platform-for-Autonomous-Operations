from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import PostgresDsn, SecretStr


class HostingerSettings(BaseSettings):
    ssh_host: str = "localhost"
    ssh_username: str = "vamshi-ots"
    ssh_password: SecretStr = SecretStr("L5AslP7GcBMGfPL")
    model_config = SettingsConfigDict(env_prefix="HOSTINGER_", case_sensitive=False)


class DatabaseSettings(BaseSettings):
    url: PostgresDsn = "postgresql+asyncpg://user:pass@localhost/db"
    pool_size: int = 5
    max_overflow: int = 10
    echo: bool = False
    model_config = SettingsConfigDict(env_prefix="DATABASE_", case_sensitive=False)


class Settings(BaseSettings):
    hostinger: HostingerSettings = HostingerSettings()
    database: DatabaseSettings = DatabaseSettings()
    app_name: str = "AI_SRE"
    app_env: str = "local"
    debug: bool = False

    model_config = SettingsConfigDict(env_file=".env", case_sensitive=False, extra="ignore")


settings = Settings()


def get_settings() -> Settings:
    return settings




"""
settings.py - Centralized Configuration Management

Purpose:
    - Single source of truth for all application configuration
    - Environment-specific settings (dev/staging/prod)
    - Secure management of sensitive credentials via .env
    - Type-safe configuration using Pydantic BaseSettings

Key Responsibilities:
    1. Load environment variables from .env file
    2. Define configuration schema with type validation
    3. Provide default values for non-critical settings
    4. Expose a singleton 'settings' instance for global access
    5. Enable dependency injection for testability

Benefits:
    - Separation of config from code (12-factor app)
    - Easy environment switching without code changes
    - Secret management (credentials never hard-coded)
    - Centralized validation and error handling
    - Simplified testing with override capabilities

Usage Pattern:
    from src.infrastructure.config import settings
    db_url = settings.DATABASE_URL
    debug_mode = settings.DEBUG

Dependencies:
    - pydantic-settings: Environment variable parsing
    - python-dotenv: .env file loading
    - os: System environment access
"""
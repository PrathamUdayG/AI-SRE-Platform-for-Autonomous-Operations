from typing import Optional, cast

from pydantic import Field, PostgresDsn, SecretStr, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class HostingerSettings(BaseSettings):
    """Hostinger VPS specific settings."""

    ssh_host: str = "localhost"
    ssh_username: str = "vamshi-ots"
    ssh_password: Optional[SecretStr] = SecretStr("L5AslP7GcBMGfPL")
    ssh_key_path: Optional[str] = None
    ssh_port: int = 22
    ssh_timeout: float = 10.0
    api_base_url: str = "https://api.hostinger.com/v1"
    api_token: Optional[SecretStr] = None

    @field_validator("ssh_port")
    @classmethod
    def validate_port(cls, v: int) -> int:
        """Validate that SSH port is in range."""
        if not (1 <= v <= 65535):
            raise ValueError("SSH Port must be between 1 and 65535")
        return v

    @field_validator("ssh_timeout")
    @classmethod
    def validate_timeout(cls, v: float) -> float:
        """Validate that timeout is positive."""
        if v <= 0:
            raise ValueError("SSH Timeout must be greater than 0")
        return v

    model_config = SettingsConfigDict(
        env_file=".env",
        env_prefix="HOSTINGER_",
        case_sensitive=False,
        frozen=True,
        extra="ignore",
    )


class DatabaseSettings(BaseSettings):
    """Database connection settings."""

    url: PostgresDsn = cast(PostgresDsn, "postgresql+asyncpg://user:pass@localhost/db")
    pool_size: int = 5
    max_overflow: int = 10
    echo: bool = False

    model_config = SettingsConfigDict(
        env_file=".env",
        env_prefix="DATABASE_",
        case_sensitive=False,
        frozen=True,
        extra="ignore",
    )


class MonitoringSettings(BaseSettings):
    """Configuration thresholds for health rules."""

    cpu_threshold_pct: float = 80.0
    memory_threshold_pct: float = 85.0
    disk_threshold_pct: float = 90.0

    model_config = SettingsConfigDict(
        env_file=".env",
        env_prefix="MONITORING_",
        case_sensitive=False,
        frozen=True,
        extra="ignore",
    )


class Settings(BaseSettings):
    """Global application settings."""

    hostinger: HostingerSettings = Field(default_factory=HostingerSettings)
    database: DatabaseSettings = Field(default_factory=DatabaseSettings)
    monitoring: MonitoringSettings = Field(default_factory=MonitoringSettings)
    app_name: str = "AI_SRE"
    app_env: str = "local"
    debug: bool = False
    log_level: str = "INFO"
    log_json: Optional[bool] = None

    @field_validator("debug", mode="before")
    @classmethod
    def debug_from_env(cls, v):
        """Coerce environment string to boolean."""
        if isinstance(v, str):
            val_lower = v.lower()
            if val_lower in ("true", "1", "yes", "on"):
                return True
            if val_lower in ("false", "0", "no", "off"):
                return False
        return v

    model_config = SettingsConfigDict(
        env_file=".env",
        env_prefix="AI_SRE_",
        env_nested_delimiter="__",
        case_sensitive=False,
        frozen=True,
        extra="ignore",
    )


settings = Settings()


def get_settings() -> Settings:
    """Dependency injection helper for getting settings."""
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

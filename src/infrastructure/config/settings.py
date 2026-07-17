# src/infrastructure/config/settings.py
import os
from functools import lru_cache
from pathlib import Path
from typing import Optional, Literal

from pydantic import Field, SecretStr, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class LoggingSettings(BaseSettings):
    """Configuration for structured logging."""
    level: Literal["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"] = Field(
        default="INFO", description="Global log level"
    )
    json_format: bool = Field(default=True, description="Emit logs as JSON for production")
    correlation_id_header: str = Field(
        default="X-Request-ID",
        description="HTTP header used to propagate correlation IDs"
    )


class DatabaseSettings(BaseSettings):
    """PostgreSQL (and TimescaleDB) connection settings."""
    host: str = Field(..., description="Database hostname")
    port: int = Field(5432, description="Database port")
    username: str = Field(..., description="Database user")
    password: SecretStr = Field(..., description="Database password")
    database: str = Field(..., description="Main database name")
    pool_min_size: int = Field(5, ge=1, description="Minimum connection pool size")
    pool_max_size: int = Field(20, ge=1, description="Maximum connection pool size")
    ssl_mode: Literal["disable", "require", "verify-full"] = Field(
        default="disable", description="PostgreSQL SSL mode"
    )
    timescale_enabled: bool = Field(default=True, description="Enable TimescaleDB extensions")

    @property
    def dsn(self) -> str:
        """Async PostgreSQL DSN for asyncpg / SQLAlchemy."""
        return (
            f"postgresql+asyncpg://{self.username}:{self.password.get_secret_value()}"
            f"@{self.host}:{self.port}/{self.database}"
        )

    @property
    def sync_dsn(self) -> str:
        """Sync DSN for Alembic / admin tools."""
        return (
            f"postgresql://{self.username}:{self.password.get_secret_value()}"
            f"@{self.host}:{self.port}/{self.database}"
        )


class RedisSettings(BaseSettings):
    """Redis connection settings for cache, pub/sub, and rate limiting."""
    host: str = Field(..., description="Redis host")
    port: int = Field(6379, description="Redis port")
    password: Optional[SecretStr] = Field(None, description="Redis password if required")
    db: int = Field(0, description="Redis database index")
    decode_responses: bool = Field(True, description="Auto-decode string responses")
    max_connections: int = Field(20, ge=1, description="Connection pool size")

    @property
    def url(self) -> str:
        """Redis URL for aioredis / redis-py."""
        auth = f":{self.password.get_secret_value()}@" if self.password else ""
        return f"redis://{auth}{self.host}:{self.port}/{self.db}"


class VectorDbSettings(BaseSettings):
    """Qdrant vector database configuration."""
    host: str = Field("localhost", description="Qdrant host")
    port: int = Field(6333, description="Qdrant REST API port")
    grpc_port: int = Field(6334, description="Qdrant gRPC port")
    api_key: Optional[SecretStr] = Field(None, description="Qdrant API key if using cloud")
    embedding_dimension: int = Field(1536, description="Default embedding size (e.g., text-embedding-ada-002)")
    collection_name_prefix: str = Field("ai_sre", description="Prefix for Qdrant collection names")

    @property
    def http_url(self) -> str:
        return f"http://{self.host}:{self.port}"


class LLMSettings(BaseSettings):
    """Configuration for all LLM backends we might use."""
    default_model: str = Field("gpt-4o-mini", description="Default LLM for reasoning")
    azure_endpoint: Optional[str] = Field(None, description="Azure OpenAI endpoint")
    azure_api_key: Optional[SecretStr] = Field(None, description="Azure OpenAI key")
    azure_deployment: Optional[str] = Field(None, description="Azure deployment name")
    openai_api_key: Optional[SecretStr] = Field(None, description="OpenAI API key")
    anthropic_api_key: Optional[SecretStr] = Field(None, description="Anthropic API key")
    temperature: float = Field(0.2, ge=0.0, le=1.0, description="Default temperature for generation")
    request_timeout: int = Field(60, ge=1, description="LLM request timeout in seconds")
    max_tokens: int = Field(4096, ge=1, description="Default max tokens for completion")



class HostingerSettings(BaseSettings):
    """Hostinger VPS specific connectors (will be extended later)."""
    api_base_url: Optional[str] = Field(None, description=https://api.hostinger.com/v1)
    api_token: Optional[SecretStr] = Field(None, description="Hostinger API token")
    ssh_key_path: Optional[Path] = Field(None, description="Path to private SSH key")
    ssh_username: Optional[str] = Field("root", description=vamshi-ots)


class FeatureFlags(BaseSettings):
    """Feature flags to safely roll out new capabilities."""
    enable_autonomous_execution: bool = Field(False, description="Allow AI to execute actions")
    enable_llm_rc: bool = Field(True, description="Enable LLM-based root cause analysis")
    enable_vector_knowledge: bool = Field(True, description="Enable RAG knowledge retrieval")
    enable_anomaly_detection: bool = Field(True, description="Enable statistical anomaly detection")
    enable_auto_remediation: bool = Field(False, description="Allow automated remediation workflows")


class Settings(BaseSettings):
    """
    Root settings container. All sub‑configs are nested here.
    Environment variables are prefixed with 'AI_SRE_' to avoid collisions.
    """
    model_config = SettingsConfigDict(
        env_prefix="AI_SRE_",
        env_nested_delimiter="__",
        case_sensitive=False,
        extra="forbid",
    )

    # ------------------ Nested Configs ------------------
    logging: LoggingSettings = Field(default_factory=LoggingSettings)
    database: DatabaseSettings = Field(..., description="PostgreSQL settings")
    redis: RedisSettings = Field(..., description="Redis settings")
    vector_db: VectorDbSettings = Field(default_factory=VectorDbSettings)
    llm: LLMSettings = Field(default_factory=LLMSettings)
    hostinger: HostingerSettings = Field(default_factory=HostingerSettings)
    features: FeatureFlags = Field(default_factory=FeatureFlags)

    # ------------------ Global Platform Settings ------------------
    app_name: str = Field("AI-SRE Platform", description="Application display name")
    app_env: Literal["local", "development", "staging", "production"] = Field(
        default="local", description="Current deployment environment"
    )
    debug: bool = Field(default=False, description="Enable debug mode (detailed errors, auto-reload)")
    secret_key: SecretStr = Field(..., description="Django/FastAPI secret key for sessions/crypto")
    default_timezone: str = Field("UTC", description="System timezone")

    @field_validator("debug", mode="before")
    @classmethod
    def debug_from_env(cls, v):
        """Coerce environment string 'true'/'false' to boolean."""
        if isinstance(v, str):
            return v.lower() in ("true", "1", "yes")
        return v


# ---------- Singleton accessor ----------
@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """
    Load settings from environment variables / .env file.
    Cached so it's loaded only once per process.
    """
    env_file = Path(os.getcwd()) / ".env"
    if env_file.exists():
        return Settings(_env_file=env_file)
    return Settings()


# Convenience alias for cleaner imports
settings = get_settings()



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
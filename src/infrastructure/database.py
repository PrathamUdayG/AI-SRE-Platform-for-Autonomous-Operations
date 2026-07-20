# src/infrastructure/database.py
"""Database connection and session lifecycle configuration."""

from typing import AsyncGenerator

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import declarative_base

from src.infrastructure.config.settings import settings

# Base class for all ORM models
Base = declarative_base()

# Create the async engine using the URL from settings with production-grade configurations
engine = create_async_engine(
    str(settings.database.url),
    echo=settings.database.echo,
    pool_size=settings.database.pool_size,
    max_overflow=settings.database.max_overflow,
    pool_pre_ping=True,  # Ensures connection health before reuse
    pool_recycle=1800,  # Recycle connections after 30 minutes
    pool_timeout=30.0,  # Timeout waiting for pool connection
)

# Session factory – each call creates a new session
AsyncSessionLocal = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autocommit=False,
    autoflush=False,
)


# FastAPI dependency to get a database session
async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """FastAPI dependency yielding an active database session context."""
    async with AsyncSessionLocal() as session:
        yield session

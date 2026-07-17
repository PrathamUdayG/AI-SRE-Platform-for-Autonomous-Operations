from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from sqlalchemy.orm import declarative_base
from src.infrastructure.config.settings import settings

# Base class for all ORM models
Base = declarative_base()

# Create the async engine using the URL from settings
engine = create_async_engine(
    str(settings.database.url),
    echo=settings.database.echo,
    pool_size=settings.database.pool_size,
    max_overflow=settings.database.max_overflow,
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
async def get_db() -> AsyncSession:
    async with AsyncSessionLocal() as session:
        yield session
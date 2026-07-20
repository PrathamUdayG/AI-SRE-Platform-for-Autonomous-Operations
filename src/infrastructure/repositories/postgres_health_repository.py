# src/infrastructure/repositories/postgres_health_repository.py
"""PostgreSQL database repository implementation for health monitoring assessments."""

from typing import List, Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.domain.entities.health import ServerHealth
from src.domain.repositories.health_repository import HealthRepository
from src.infrastructure.persistence.mappers import HealthMapper
from src.infrastructure.persistence.models import ServerHealthModel


class PostgresHealthRepository(HealthRepository):
    """PostgreSQL storage adapter for ServerHealth using SQLAlchemy AsyncSession."""

    def __init__(self, session: AsyncSession):
        self.session = session

    async def save(self, entity: ServerHealth) -> ServerHealth:
        """Persist or merge a ServerHealth aggregate into the database."""
        model = HealthMapper.to_model(entity)
        if model.id is not None:
            await self.session.merge(model)
        else:
            self.session.add(model)
        await self.session.commit()
        await self.session.refresh(model)
        return HealthMapper.to_domain(model)

    async def get_by_id(self, id: int) -> Optional[ServerHealth]:
        """Retrieve a specific ServerHealth record by its database ID."""
        result = await self.session.execute(
            select(ServerHealthModel).where(ServerHealthModel.id == id)
        )
        model = result.scalar_one_or_none()
        return HealthMapper.to_domain(model) if model else None

    async def get_all(self, limit: int = 100, offset: int = 0) -> List[ServerHealth]:
        """Fetch all stored server health records with pagination."""
        result = await self.session.execute(
            select(ServerHealthModel)
            .offset(offset)
            .limit(limit)
            .order_by(ServerHealthModel.evaluation_timestamp.desc())
        )
        models = result.scalars().all()
        return [HealthMapper.to_domain(m) for m in models]

    async def get_latest_by_server_id(self, server_id: int) -> Optional[ServerHealth]:
        """Retrieve the most recent health assessment matching server_id."""
        stmt = (
            select(ServerHealthModel)
            .where(ServerHealthModel.server_id == server_id)
            .order_by(ServerHealthModel.evaluation_timestamp.desc())
            .limit(1)
        )
        result = await self.session.execute(stmt)
        model = result.scalar_one_or_none()
        return HealthMapper.to_domain(model) if model else None

    async def get_history_by_server_id(
        self, server_id: int, limit: int = 100
    ) -> List[ServerHealth]:
        """Fetch chronological list of health assessments, newest first."""
        stmt = (
            select(ServerHealthModel)
            .where(ServerHealthModel.server_id == server_id)
            .order_by(ServerHealthModel.evaluation_timestamp.desc())
            .limit(limit)
        )
        result = await self.session.execute(stmt)
        models = result.scalars().all()
        return [HealthMapper.to_domain(m) for m in models]

    async def delete(self, id: int) -> bool:
        """Remove a health assessment record by ID."""
        result = await self.session.execute(
            select(ServerHealthModel).where(ServerHealthModel.id == id)
        )
        model = result.scalar_one_or_none()
        if model:
            await self.session.delete(model)
            await self.session.commit()
            return True
        return False

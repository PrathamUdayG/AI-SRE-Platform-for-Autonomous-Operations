# src/infrastructure/repositories/postgres_incident_repository.py
"""PostgreSQL database repository implementation for incidents."""

from typing import List, Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.domain.entities.incident import Incident
from src.domain.repositories.incident_repository import IncidentRepository
from src.infrastructure.persistence.mappers import IncidentMapper
from src.infrastructure.persistence.models import IncidentModel


class PostgresIncidentRepository(IncidentRepository):
    """PostgreSQL storage adapter for Incident using SQLAlchemy AsyncSession."""

    def __init__(self, session: AsyncSession):
        self.session = session

    async def save(self, entity: Incident) -> Incident:
        """Persist or merge an Incident aggregate into the database."""
        model = IncidentMapper.to_model(entity)
        if model.id is not None:
            await self.session.merge(model)
        else:
            self.session.add(model)
        await self.session.commit()
        await self.session.refresh(model)
        return IncidentMapper.to_domain(model)

    async def get_by_id(self, id: int) -> Optional[Incident]:
        """Retrieve a specific SRE incident record by its unique database ID."""
        result = await self.session.execute(
            select(IncidentModel).where(IncidentModel.id == id)
        )
        model = result.scalar_one_or_none()
        return IncidentMapper.to_domain(model) if model else None

    async def get_all(self, limit: int = 100, offset: int = 0) -> List[Incident]:
        """Fetch all operational incidents with pagination."""
        result = await self.session.execute(
            select(IncidentModel)
            .offset(offset)
            .limit(limit)
            .order_by(IncidentModel.created_at.desc())
        )
        models = result.scalars().all()
        return [IncidentMapper.to_domain(m) for m in models]

    async def get_by_server_id(self, server_id: int) -> List[Incident]:
        """Fetch all incidents associated with a server, newest first."""
        result = await self.session.execute(
            select(IncidentModel)
            .where(IncidentModel.server_id == server_id)
            .order_by(IncidentModel.created_at.desc())
        )
        models = result.scalars().all()
        return [IncidentMapper.to_domain(m) for m in models]

    async def delete(self, id: int) -> bool:
        """Remove an incident by database ID."""
        result = await self.session.execute(
            select(IncidentModel).where(IncidentModel.id == id)
        )
        model = result.scalar_one_or_none()
        if model:
            await self.session.delete(model)
            await self.session.commit()
            return True
        return False

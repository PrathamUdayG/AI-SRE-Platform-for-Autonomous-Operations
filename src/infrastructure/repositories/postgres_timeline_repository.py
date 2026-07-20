# src/infrastructure/repositories/postgres_timeline_repository.py
"""PostgreSQL database repository implementation for incident timeline events."""

from typing import List, Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.domain.entities.incident import TimelineEntry
from src.domain.repositories.timeline_repository import TimelineRepository
from src.infrastructure.persistence.mappers import TimelineMapper
from src.infrastructure.persistence.models import TimelineEntryModel


class PostgresTimelineRepository(TimelineRepository):
    """PostgreSQL storage adapter for TimelineEntry using SQLAlchemy AsyncSession."""

    def __init__(self, session: AsyncSession):
        self.session = session

    async def save(self, entity: TimelineEntry) -> TimelineEntry:
        """Persist or merge a TimelineEntry into the database."""
        model = TimelineMapper.to_model(entity)
        if model.id is not None:
            await self.session.merge(model)
        else:
            self.session.add(model)
        await self.session.commit()
        await self.session.refresh(model)
        return TimelineMapper.to_domain(model)

    async def get_by_id(self, id: int) -> Optional[TimelineEntry]:
        """Retrieve a timeline entry record by database ID."""
        result = await self.session.execute(
            select(TimelineEntryModel).where(TimelineEntryModel.id == id)
        )
        model = result.scalar_one_or_none()
        return TimelineMapper.to_domain(model) if model else None

    async def get_all(self, limit: int = 100, offset: int = 0) -> List[TimelineEntry]:
        """Fetch all timeline entries with pagination."""
        result = await self.session.execute(
            select(TimelineEntryModel)
            .offset(offset)
            .limit(limit)
            .order_by(TimelineEntryModel.timestamp.asc())
        )
        models = result.scalars().all()
        return [TimelineMapper.to_domain(m) for m in models]

    async def get_by_incident_id(self, incident_id: int) -> List[TimelineEntry]:
        """Fetch chronological timeline events for a given incident ID, oldest first."""
        result = await self.session.execute(
            select(TimelineEntryModel)
            .where(TimelineEntryModel.incident_id == incident_id)
            .order_by(TimelineEntryModel.timestamp.asc())
        )
        models = result.scalars().all()
        return [TimelineMapper.to_domain(m) for m in models]

    async def delete(self, id: int) -> bool:
        """Remove a timeline entry from database."""
        result = await self.session.execute(
            select(TimelineEntryModel).where(TimelineEntryModel.id == id)
        )
        model = result.scalar_one_or_none()
        if model:
            await self.session.delete(model)
            await self.session.commit()
            return True
        return False

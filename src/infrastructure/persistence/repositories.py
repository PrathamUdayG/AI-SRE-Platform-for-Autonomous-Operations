from typing import List, Optional
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.domain.interfaces.repositories import IRepository
from src.domain.entities.metric import Metric
from src.infrastructure.persistence.models import MetricModel


class MetricRepository(IRepository[Metric]):
    """Concrete repository for Metric entities using PostgreSQL + async SQLAlchemy."""

    def __init__(self, session: AsyncSession):
        self._session = session

    async def save(self, entity: Metric) -> Metric:
        """Insert a new metric into the database."""
        db_obj = MetricModel(
            name=entity.name,
            value=entity.value,
            timestamp=entity.timestamp,
            service=entity.service,
            tags=entity.tags,
        )
        self._session.add(db_obj)
        await self._session.commit()
        await self._session.refresh(db_obj)

        # Update the domain entity with the generated ID
        entity.id = db_obj.id
        return entity

    async def get_by_id(self, entity_id: int) -> Optional[Metric]:
        """Retrieve a metric by its primary key."""
        result = await self._session.execute(
            select(MetricModel).where(MetricModel.id == entity_id)
        )
        db_obj = result.scalar_one_or_none()
        if db_obj is None:
            return None

        return Metric(
            id=db_obj.id,
            name=db_obj.name,
            value=db_obj.value,
            timestamp=db_obj.timestamp,
            service=db_obj.service,
            tags=db_obj.tags,
        )

    async def get_all(self) -> List[Metric]:
        """Retrieve all metrics (use with care – we'll add pagination later)."""
        result = await self._session.execute(select(MetricModel))
        db_objs = result.scalars().all()

        return [
            Metric(
                id=obj.id,
                name=obj.name,
                value=obj.value,
                timestamp=obj.timestamp,
                service=obj.service,
                tags=obj.tags,
            )
            for obj in db_objs
        ]

    async def delete(self, entity_id: int) -> None:
        """Delete a metric by its ID."""
        db_obj = await self._session.get(MetricModel, entity_id)
        if db_obj:
            await self._session.delete(db_obj)
            await self._session.commit()

"""
Metric (domain entity) – a plain Python class (using Pydantic) that your application logic will use. It knows nothing about databases.

MetricModel (ORM model) – tells SQLAlchemy how to map the Metric to a database table called metrics. Each column matches a field in the entity.

MetricRepository – is a class that implements the IRepository interface you already wrote. It uses an AsyncSession (from our get_db dependency) to actually talk to the database.

save → converts your domain Metric into an ORM model, inserts it, commits, and returns the metric with the new ID.

get_by_id → queries the database, converts the result back into a domain Metric.

get_all → gets all rows (good for testing, we’ll add pagination later).

delete → removes a row by ID.
"""
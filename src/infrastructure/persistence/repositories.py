# src/infrastructure/persistence/repositories.py
"""Concrete implementation of MetricRepository using PostgreSQL and SQLAlchemy."""

from typing import List, Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.domain.entities.metric import Metric
from src.domain.repositories.metric_repository import (
    MetricRepository as IMetricRepository,
)
from src.infrastructure.persistence.models import MetricModel


class MetricRepository(IMetricRepository):
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

    async def get_all(self, limit: int = 100, offset: int = 0) -> List[Metric]:
        """Retrieve a list of metrics with pagination."""
        result = await self._session.execute(
            select(MetricModel).offset(offset).limit(limit)
        )
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

    async def delete(self, entity_id: int) -> bool:
        """Delete a metric by its ID."""
        db_obj = await self._session.get(MetricModel, entity_id)
        if db_obj:
            await self._session.delete(db_obj)
            await self._session.commit()
            return True
        return False

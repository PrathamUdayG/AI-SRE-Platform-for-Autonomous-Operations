# src/infrastructure/repositories/postgres_telemetry_repository.py
"""PostgreSQL database repository implementation for telemetry metrics."""

from typing import List, Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.domain.entities.telemetry import TelemetryMetric
from src.domain.repositories.telemetry_repository import TelemetryRepository
from src.infrastructure.persistence.mappers import MetricMapper
from src.infrastructure.persistence.models import TelemetryMetricModel


class PostgresTelemetryRepository(TelemetryRepository):
    """PostgreSQL storage adapter for telemetry using SQLAlchemy AsyncSession."""

    def __init__(self, session: AsyncSession):
        self.session = session

    async def save(self, entity: TelemetryMetric) -> TelemetryMetric:
        """Persist or merge a TelemetryMetric domain entity into the database."""
        model = MetricMapper.to_model(entity)
        if model.id is not None:
            await self.session.merge(model)
        else:
            self.session.add(model)
        await self.session.commit()
        await self.session.refresh(model)
        return MetricMapper.to_domain(model)

    async def get_by_id(self, id: int) -> Optional[TelemetryMetric]:
        """Retrieve a specific telemetry record by its unique database ID."""
        result = await self.session.execute(
            select(TelemetryMetricModel).where(TelemetryMetricModel.id == id)
        )
        model = result.scalar_one_or_none()
        return MetricMapper.to_domain(model) if model else None

    async def get_all(self, limit: int = 100, offset: int = 0) -> List[TelemetryMetric]:
        """Fetch all stored telemetry records with pagination."""
        result = await self.session.execute(
            select(TelemetryMetricModel)
            .offset(offset)
            .limit(limit)
            .order_by(TelemetryMetricModel.timestamp.desc())
        )
        models = result.scalars().all()
        return [MetricMapper.to_domain(m) for m in models]

    async def get_latest_by_server_id(
        self, server_id: int, metric_type: str
    ) -> Optional[TelemetryMetric]:
        """Retrieve the most recent telemetry sample matching server_id and type."""
        stmt = (
            select(TelemetryMetricModel)
            .where(
                TelemetryMetricModel.server_id == server_id,
                TelemetryMetricModel.metric_type == metric_type,
            )
            .order_by(TelemetryMetricModel.timestamp.desc())
            .limit(1)
        )
        result = await self.session.execute(stmt)
        model = result.scalar_one_or_none()
        return MetricMapper.to_domain(model) if model else None

    async def get_history_by_server_id(
        self, server_id: int, metric_type: str, limit: int = 100
    ) -> List[TelemetryMetric]:
        """Fetch a chronological list of metric samples for the target server, newest first."""
        stmt = (
            select(TelemetryMetricModel)
            .where(
                TelemetryMetricModel.server_id == server_id,
                TelemetryMetricModel.metric_type == metric_type,
            )
            .order_by(TelemetryMetricModel.timestamp.desc())
            .limit(limit)
        )
        result = await self.session.execute(stmt)
        models = result.scalars().all()
        return [MetricMapper.to_domain(m) for m in models]

    async def delete(self, id: int) -> bool:
        """Remove a telemetry sample by ID from database."""
        result = await self.session.execute(
            select(TelemetryMetricModel).where(TelemetryMetricModel.id == id)
        )
        model = result.scalar_one_or_none()
        if model:
            await self.session.delete(model)
            await self.session.commit()
            return True
        return False

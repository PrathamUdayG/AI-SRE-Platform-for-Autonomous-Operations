# src/infrastructure/repositories/postgres_inventory_repository.py
"""PostgreSQL-backed implementation of the InventoryRepository interface."""

from typing import List, Optional

import structlog
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.domain.entities.inventory import Inventory
from src.domain.repositories.inventory_repository import InventoryRepository
from src.infrastructure.persistence.mappers import InventoryMapper
from src.infrastructure.persistence.models import InventoryModel

logger = structlog.get_logger(__name__)


class PostgresInventoryRepository(InventoryRepository):
    """PostgreSQL-backed implementation of the InventoryRepository interface."""

    def __init__(self, session: AsyncSession):
        self.session = session

    async def save(self, entity: Inventory) -> Inventory:
        """Insert or update an inventory record."""
        logger.info(
            "Saving inventory record",
            server_id=entity.server_id,
            entity_id=entity.id,
        )

        db_model = InventoryMapper.to_model(entity)

        if entity.id is not None:
            # Update existing record
            merged = await self.session.merge(db_model)
            await self.session.commit()
            return InventoryMapper.to_domain(merged)
        else:
            # Insert new record
            self.session.add(db_model)
            await self.session.commit()
            await self.session.refresh(db_model)
            entity.id = db_model.id
            return InventoryMapper.to_domain(db_model)

    async def get_by_id(self, entity_id: int) -> Optional[Inventory]:
        """Retrieve an inventory record by its ID."""
        query = select(InventoryModel).where(InventoryModel.id == entity_id)
        result = await self.session.execute(query)
        db_obj = result.scalar_one_or_none()
        if not db_obj:
            return None
        return InventoryMapper.to_domain(db_obj)

    async def get_by_server_id(self, server_id: int) -> Optional[Inventory]:
        """Retrieve an inventory record by its server ID."""
        query = select(InventoryModel).where(InventoryModel.server_id == server_id)
        result = await self.session.execute(query)
        db_obj = result.scalar_one_or_none()
        if not db_obj:
            return None
        return InventoryMapper.to_domain(db_obj)

    async def get_all(self, limit: int = 100, offset: int = 0) -> List[Inventory]:
        """Retrieve a paginated list of all inventory records."""
        query = select(InventoryModel).offset(offset).limit(limit)
        result = await self.session.execute(query)
        db_objs = result.scalars().all()
        return [InventoryMapper.to_domain(obj) for obj in db_objs]

    async def delete(self, entity_id: int) -> bool:
        """Delete an inventory record by its ID."""
        db_obj = await self.session.get(InventoryModel, entity_id)
        if db_obj:
            await self.session.delete(db_obj)
            await self.session.commit()
            return True
        return False

    async def search(self, query_str: str) -> List[Inventory]:
        """Search inventory by hostname, OS, environment, project, region, or role."""
        pattern = f"%{query_str}%"
        query = select(InventoryModel).where(
            (InventoryModel.hostname.ilike(pattern))
            | (InventoryModel.operating_system.ilike(pattern))
            | (InventoryModel.environment.ilike(pattern))
            | (InventoryModel.project.ilike(pattern))
            | (InventoryModel.region.ilike(pattern))
            | (InventoryModel.role.ilike(pattern))
        )
        result = await self.session.execute(query)
        db_objs = result.scalars().all()
        return [InventoryMapper.to_domain(obj) for obj in db_objs]

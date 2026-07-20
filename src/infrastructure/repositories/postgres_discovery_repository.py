# src/infrastructure/repositories/postgres_discovery_repository.py
"""PostgreSQL-backed implementation of the DiscoveryRepository interface."""

from typing import List, Optional

import structlog
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.domain.entities.discovery import (
    CPUInfo,
    DiscoverySnapshot,
    DiskInfo,
    MemoryInfo,
    NetworkInterfaceInfo,
)
from src.domain.repositories.discovery_repository import DiscoveryRepository
from src.infrastructure.persistence.models import DiscoverySnapshotModel

logger = structlog.get_logger(__name__)


class PostgresDiscoveryRepository(DiscoveryRepository):
    """PostgreSQL-backed implementation of the DiscoveryRepository interface."""

    def __init__(self, session: AsyncSession):
        self.session = session

    async def save(self, snapshot: DiscoverySnapshot) -> DiscoverySnapshot:
        """Insert a new discovery snapshot into the database."""
        logger.info("Saving discovery snapshot", server_id=snapshot.server_id)
        db_snapshot = DiscoverySnapshotModel(
            server_id=snapshot.server_id,
            hostname=snapshot.hostname,
            operating_system=snapshot.operating_system,
            kernel_version=snapshot.kernel_version,
            architecture=snapshot.architecture,
            uptime=snapshot.uptime,
            timezone=snapshot.timezone,
            cpu=snapshot.cpu.model_dump(),
            memory=snapshot.memory.model_dump(),
            disks=[d.model_dump() for d in snapshot.disks],
            network_interfaces=[n.model_dump() for n in snapshot.network_interfaces],
            discovered_at=snapshot.discovered_at,
        )
        self.session.add(db_snapshot)
        await self.session.commit()
        await self.session.refresh(db_snapshot)
        snapshot.id = db_snapshot.id
        return snapshot

    async def get_by_id(self, entity_id: int) -> Optional[DiscoverySnapshot]:
        """Retrieve a specific discovery snapshot by its ID."""
        query = select(DiscoverySnapshotModel).where(
            DiscoverySnapshotModel.id == entity_id
        )
        result = await self.session.execute(query)
        db_obj = result.scalar_one_or_none()
        if not db_obj:
            return None
        return self._to_domain(db_obj)

    async def get_latest_by_server_id(
        self, server_id: int
    ) -> Optional[DiscoverySnapshot]:
        """Retrieve the latest discovery snapshot for the specified server."""
        query = (
            select(DiscoverySnapshotModel)
            .where(DiscoverySnapshotModel.server_id == server_id)
            .order_by(DiscoverySnapshotModel.discovered_at.desc())
            .limit(1)
        )
        result = await self.session.execute(query)
        db_obj = result.scalar_one_or_none()
        if not db_obj:
            return None
        return self._to_domain(db_obj)

    async def get_all(
        self, limit: int = 100, offset: int = 0
    ) -> List[DiscoverySnapshot]:
        """Retrieve a paginated list of all discovery snapshots."""
        query = select(DiscoverySnapshotModel).offset(offset).limit(limit)
        result = await self.session.execute(query)
        db_objs = result.scalars().all()
        return [self._to_domain(obj) for obj in db_objs]

    async def delete(self, entity_id: int) -> bool:
        """Delete a discovery snapshot by its ID."""
        db_obj = await self.session.get(DiscoverySnapshotModel, entity_id)
        if db_obj:
            await self.session.delete(db_obj)
            await self.session.commit()
            return True
        return False

    def _to_domain(self, db_obj: DiscoverySnapshotModel) -> DiscoverySnapshot:
        """Convert a database ORM model instance into a Domain Snapshot entity."""
        return DiscoverySnapshot(
            id=db_obj.id,
            server_id=db_obj.server_id,
            hostname=db_obj.hostname,
            operating_system=db_obj.operating_system,
            kernel_version=db_obj.kernel_version,
            architecture=db_obj.architecture,
            uptime=db_obj.uptime,
            timezone=db_obj.timezone,
            cpu=CPUInfo(**db_obj.cpu),
            memory=MemoryInfo(**db_obj.memory),
            disks=[DiskInfo(**d) for d in db_obj.disks],
            network_interfaces=[
                NetworkInterfaceInfo(**n) for n in db_obj.network_interfaces
            ],
            discovered_at=db_obj.discovered_at,
        )

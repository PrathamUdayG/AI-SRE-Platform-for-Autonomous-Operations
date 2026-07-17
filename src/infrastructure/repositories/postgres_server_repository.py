# src/infrastructure/repositories/postgres_server_repository.py
# Why: Concrete implementation of ServerRepository using PostgreSQL and SQLAlchemy.
# Implements the standard persistence operations using async SQLAlchemy sessions.

import structlog
from typing import Optional, List
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, or_
from src.domain.entities.server import Server
from src.domain.repositories.server_repository import ServerRepository
from src.infrastructure.persistence.models import ServerModel
from src.domain.exceptions import ConflictError

logger = structlog.get_logger(__name__)

class PostgresServerRepository(ServerRepository):
    """
    Concrete implementation of ServerRepository using PostgreSQL and SQLAlchemy.
    """

    def __init__(self, session: AsyncSession):
        self.session = session

    async def save(self, server: Server) -> Server:
        """Save a new server or update an existing one."""
        logger.info("Saving server to database", hostname=server.hostname, ip_address=server.ip_address)
        try:
            # Check for existing hostname or IP duplicate to raise Domain exception
            # if saving a new record (id is None)
            if server.id is None:
                existing = await self.exists(server.hostname, server.ip_address)
                if existing:
                    logger.warning("Duplicate server detected during save", hostname=server.hostname, ip_address=server.ip_address)
                    raise ConflictError(f"Server with hostname '{server.hostname}' or IP '{server.ip_address}' already exists.")

            # Convert Domain Entity -> Database Model
            db_server = ServerModel(
                id=server.id,
                hostname=server.hostname,
                ip_address=server.ip_address,
                operating_system=server.operating_system,
                cpu_cores=server.cpu_cores,
                memory_gb=server.memory_gb,
            )
            # Add to the database session
            self.session.add(db_server)
            await self.session.commit()
            await self.session.refresh(db_server)
            
            # Map back to domain entity
            server.id = db_server.id
            server.created_at = db_server.created_at
            server.updated_at = db_server.updated_at
            return server
        except ConflictError:
            raise
        except Exception as e:
            logger.error("Failed to save server to database", error=str(e), hostname=server.hostname)
            await self.session.rollback()
            raise

    async def get_by_id(self, entity_id: int) -> Optional[Server]:
        """Retrieve a server by its unique ID."""
        logger.info("Fetching server by ID", server_id=entity_id)
        query = select(ServerModel).where(ServerModel.id == entity_id)
        result = await self.session.execute(query)
        db_server = result.scalar_one_or_none()

        if db_server is None:
            return None

        return Server(
            id=db_server.id,
            hostname=db_server.hostname,
            ip_address=db_server.ip_address,
            operating_system=db_server.operating_system,
            cpu_cores=db_server.cpu_cores,
            memory_gb=db_server.memory_gb,
            created_at=db_server.created_at,
            updated_at=db_server.updated_at,
        )

    async def get_by_hostname(self, hostname: str) -> Optional[Server]:
        """Retrieve a server by its hostname."""
        logger.info("Fetching server by hostname", hostname=hostname)
        query = select(ServerModel).where(ServerModel.hostname == hostname)
        result = await self.session.execute(query)
        db_server = result.scalar_one_or_none()

        if db_server is None:
            return None

        return Server(
            id=db_server.id,
            hostname=db_server.hostname,
            ip_address=db_server.ip_address,
            operating_system=db_server.operating_system,
            cpu_cores=db_server.cpu_cores,
            memory_gb=db_server.memory_gb,
            created_at=db_server.created_at,
            updated_at=db_server.updated_at,
        )

    async def get_by_ip(self, ip_address: str) -> Optional[Server]:
        """Retrieve a server by its IP address."""
        logger.info("Fetching server by IP address", ip_address=ip_address)
        query = select(ServerModel).where(ServerModel.ip_address == ip_address)
        result = await self.session.execute(query)
        db_server = result.scalar_one_or_none()

        if db_server is None:
            return None

        return Server(
            id=db_server.id,
            hostname=db_server.hostname,
            ip_address=db_server.ip_address,
            operating_system=db_server.operating_system,
            cpu_cores=db_server.cpu_cores,
            memory_gb=db_server.memory_gb,
            created_at=db_server.created_at,
            updated_at=db_server.updated_at,
        )

    async def exists(self, hostname: str, ip_address: str) -> bool:
        """Check if a server with the given hostname or IP already exists."""
        logger.info("Checking if server exists", hostname=hostname, ip_address=ip_address)
        query = select(ServerModel).where(
            or_(ServerModel.hostname == hostname, ServerModel.ip_address == ip_address)
        )
        result = await self.session.execute(query)
        return result.first() is not None

    async def get_all(self, limit: int = 100, offset: int = 0) -> List[Server]:
        """Retrieve a list of servers with pagination."""
        logger.info("Fetching all servers", limit=limit, offset=offset)
        query = select(ServerModel).offset(offset).limit(limit)
        result = await self.session.execute(query)
        db_servers = result.scalars().all()

        return [
            Server(
                id=db_server.id,
                hostname=db_server.hostname,
                ip_address=db_server.ip_address,
                operating_system=db_server.operating_system,
                cpu_cores=db_server.cpu_cores,
                memory_gb=db_server.memory_gb,
                created_at=db_server.created_at,
                updated_at=db_server.updated_at,
            )
            for db_server in db_servers
        ]

    async def delete(self, entity_id: int) -> bool:
        """Delete a server by ID."""
        logger.info("Deleting server by ID", server_id=entity_id)
        query = select(ServerModel).where(ServerModel.id == entity_id)
        result = await self.session.execute(query)
        db_server = result.scalar_one_or_none()

        if db_server is None:
            return False

        await self.session.delete(db_server)
        await self.session.commit()
        return True

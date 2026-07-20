# src/application/services/inventory_service.py
"""Application service that manages the lifecycle of inventory assets."""

from typing import Dict, List, Optional

import structlog

from src.application.services.discovery_service import DiscoveryService
from src.domain.entities.inventory import Inventory
from src.domain.exceptions import NotFoundError
from src.domain.repositories.inventory_repository import InventoryRepository
from src.infrastructure.persistence.mappers import DiscoveryMapper

logger = structlog.get_logger(__name__)


class InventoryService:
    """Orchestrates creation from discovery, retrieval, search, updates, and deletion."""

    def __init__(
        self,
        inventory_repository: InventoryRepository,
        discovery_service: DiscoveryService,
    ):
        self.inventory_repository = inventory_repository
        self.discovery_service = discovery_service

    async def create_from_discovery(self, server_id: int) -> Inventory:
        """Perform discovery on server and upsert the result into the inventory system."""
        logger.info("Promoting discovery to inventory", server_id=server_id)

        # 1. Trigger or fetch the latest discovery result
        discovery_result = await self.discovery_service.discover_server(server_id)

        # Check if an inventory record already exists for this server
        existing = await self.inventory_repository.get_by_server_id(server_id)
        if existing:
            # Update existing inventory asset with fresh discovery info
            updated_inventory = DiscoveryMapper.to_inventory(discovery_result)
            updated_inventory.id = existing.id
            updated_inventory.metadata = existing.metadata
            updated_inventory.version = existing.version + 1
            return await self.inventory_repository.save(updated_inventory)

        # 2. Map DiscoveryResult to Inventory Domain Aggregate using DiscoveryMapper
        inventory_asset = DiscoveryMapper.to_inventory(discovery_result)

        # 3. Persist the Inventory Aggregate
        return await self.inventory_repository.save(inventory_asset)

    async def get_inventory_by_id(self, inventory_id: int) -> Inventory:
        """Fetch inventory asset record by its primary key ID."""
        asset = await self.inventory_repository.get_by_id(inventory_id)
        if not asset:
            raise NotFoundError(f"Inventory asset with ID {inventory_id} not found.")
        return asset

    async def get_all_inventory(
        self, limit: int = 100, offset: int = 0
    ) -> List[Inventory]:
        """Fetch paginated inventory assets."""
        return await self.inventory_repository.get_all(limit=limit, offset=offset)

    async def search_inventory(self, query_str: str) -> List[Inventory]:
        """Search inventory assets matching the filter text."""
        return await self.inventory_repository.search(query_str)

    async def update_metadata(
        self,
        inventory_id: int,
        environment: Optional[str] = None,
        owner: Optional[str] = None,
        project: Optional[str] = None,
        business_unit: Optional[str] = None,
        region: Optional[str] = None,
        datacenter: Optional[str] = None,
        role: Optional[str] = None,
        criticality: Optional[str] = None,
        tags: Optional[Dict[str, str]] = None,
    ) -> Inventory:
        """Update tags or metadata properties on an inventory record."""
        logger.info("Updating inventory metadata", inventory_id=inventory_id)
        asset = await self.inventory_repository.get_by_id(inventory_id)
        if not asset:
            raise NotFoundError(f"Inventory asset with ID {inventory_id} not found.")

        # Update metadata properties if provided
        if environment is not None:
            asset.metadata.environment = environment
        if owner is not None:
            asset.metadata.owner = owner
        if project is not None:
            asset.metadata.project = project
        if business_unit is not None:
            asset.metadata.business_unit = business_unit
        if region is not None:
            asset.metadata.region = region
        if datacenter is not None:
            asset.metadata.datacenter = datacenter
        if role is not None:
            asset.metadata.role = role
        if criticality is not None:
            asset.metadata.criticality = criticality
        if tags is not None:
            asset.metadata.tags.update(tags)

        asset.version += 1
        return await self.inventory_repository.save(asset)

    async def delete_inventory(self, inventory_id: int) -> bool:
        """Delete an inventory asset from the authoritative records."""
        logger.info("Deleting inventory record", inventory_id=inventory_id)
        asset = await self.inventory_repository.get_by_id(inventory_id)
        if not asset:
            raise NotFoundError(f"Inventory asset with ID {inventory_id} not found.")
        return await self.inventory_repository.delete(inventory_id)

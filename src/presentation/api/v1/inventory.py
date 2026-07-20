# src/presentation/api/v1/inventory.py
"""API routes for inventory management."""

from typing import List

import structlog
from fastapi import APIRouter, Depends, HTTPException, Query, status

from src.application.services.inventory_service import InventoryService
from src.infrastructure.di import get_inventory_service
from src.presentation.api.schemas.inventory import (
    InventoryResponse,
    UpdateInventoryMetadataRequest,
)

logger = structlog.get_logger(__name__)
router = APIRouter(prefix="/inventory", tags=["Inventory"])


@router.post(
    "/from-discovery/{server_id}",
    response_model=InventoryResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_from_discovery(
    server_id: int,
    service: InventoryService = Depends(get_inventory_service),
) -> InventoryResponse:
    """Run discovery and register/update the target server in the inventory system."""
    logger.info("API trigger: promote discovery to inventory", server_id=server_id)
    inventory = await service.create_from_discovery(server_id)
    return InventoryResponse.model_validate(inventory)


@router.get(
    "/search",
    response_model=List[InventoryResponse],
)
async def search_inventory(
    q: str = Query(..., description="Query string to search across attributes"),
    service: InventoryService = Depends(get_inventory_service),
) -> List[InventoryResponse]:
    """Search inventory assets by hostname, OS, environment, project, region, or role."""
    logger.info("API trigger: search inventory", query_str=q)
    results = await service.search_inventory(q)
    return [InventoryResponse.model_validate(i) for i in results]


@router.get(
    "",
    response_model=List[InventoryResponse],
)
async def get_all_inventory(
    limit: int = Query(100, ge=1, le=1000),
    offset: int = Query(0, ge=0),
    service: InventoryService = Depends(get_inventory_service),
) -> List[InventoryResponse]:
    """Retrieve a paginated list of all managed inventory assets."""
    logger.info("API trigger: get all inventory", limit=limit, offset=offset)
    results = await service.get_all_inventory(limit=limit, offset=offset)
    return [InventoryResponse.model_validate(i) for i in results]


@router.get(
    "/{inventory_id}",
    response_model=InventoryResponse,
)
async def get_inventory_by_id(
    inventory_id: int,
    service: InventoryService = Depends(get_inventory_service),
) -> InventoryResponse:
    """Retrieve full details of a specific inventory asset by its ID."""
    logger.info("API trigger: get inventory by id", inventory_id=inventory_id)
    inventory = await service.get_inventory_by_id(inventory_id)
    return InventoryResponse.model_validate(inventory)


@router.put(
    "/{inventory_id}",
    response_model=InventoryResponse,
)
async def update_inventory_metadata_put(
    inventory_id: int,
    request: UpdateInventoryMetadataRequest,
    service: InventoryService = Depends(get_inventory_service),
) -> InventoryResponse:
    """Update metadata properties and custom tags on an inventory asset (PUT)."""
    logger.info(
        "API trigger: update inventory metadata (PUT)", inventory_id=inventory_id
    )
    inventory = await service.update_metadata(
        inventory_id=inventory_id,
        environment=request.environment,
        owner=request.owner,
        project=request.project,
        business_unit=request.business_unit,
        region=request.region,
        datacenter=request.datacenter,
        role=request.role,
        criticality=request.criticality,
        tags=request.tags,
    )
    return InventoryResponse.model_validate(inventory)


@router.patch(
    "/{inventory_id}",
    response_model=InventoryResponse,
)
async def update_inventory_metadata_patch(
    inventory_id: int,
    request: UpdateInventoryMetadataRequest,
    service: InventoryService = Depends(get_inventory_service),
) -> InventoryResponse:
    """Update metadata properties and custom tags on an inventory asset (PATCH)."""
    logger.info(
        "API trigger: update inventory metadata (PATCH)", inventory_id=inventory_id
    )
    inventory = await service.update_metadata(
        inventory_id=inventory_id,
        environment=request.environment,
        owner=request.owner,
        project=request.project,
        business_unit=request.business_unit,
        region=request.region,
        datacenter=request.datacenter,
        role=request.role,
        criticality=request.criticality,
        tags=request.tags,
    )
    return InventoryResponse.model_validate(inventory)


@router.delete(
    "/{inventory_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
async def delete_inventory(
    inventory_id: int,
    service: InventoryService = Depends(get_inventory_service),
) -> None:
    """Delete a managed server's asset record from the inventory system."""
    logger.info("API trigger: delete inventory", inventory_id=inventory_id)
    await service.delete_inventory(inventory_id)

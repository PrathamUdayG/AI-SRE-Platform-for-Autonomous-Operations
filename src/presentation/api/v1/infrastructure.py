# src/presentation/api/v1/infrastructure.py
"""API routes for infrastructure discovery."""

import structlog
from fastapi import APIRouter, Depends, HTTPException, status

from src.application.services.discovery_service import DiscoveryService
from src.infrastructure.di import get_discovery_service
from src.presentation.api.schemas.discovery import DiscoverySnapshotResponse

logger = structlog.get_logger(__name__)
router = APIRouter(prefix="/infrastructure", tags=["Infrastructure"])


@router.post(
    "/discover/{server_id}",
    response_model=DiscoverySnapshotResponse,
    status_code=status.HTTP_201_CREATED,
)
async def discover_server(
    server_id: int,
    service: DiscoveryService = Depends(get_discovery_service),
) -> DiscoverySnapshotResponse:
    """Trigger a discovery run on the remote server and return the persisted snapshot."""
    logger.info("API trigger: discover server", server_id=server_id)
    snapshot = await service.discover_server(server_id)
    return DiscoverySnapshotResponse.model_validate(snapshot)


@router.get(
    "/discovery/{server_id}",
    response_model=DiscoverySnapshotResponse,
)
async def get_latest_discovery(
    server_id: int,
    service: DiscoveryService = Depends(get_discovery_service),
) -> DiscoverySnapshotResponse:
    """Retrieve the latest infrastructure discovery snapshot for the specified server."""
    logger.info("API trigger: get latest discovery snapshot", server_id=server_id)
    snapshot = await service.get_latest_discovery(server_id)
    if not snapshot:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No discovery snapshot found for server ID {server_id}.",
        )
    return DiscoverySnapshotResponse.model_validate(snapshot)

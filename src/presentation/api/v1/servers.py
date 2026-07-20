# src/presentation/api/v1/servers.py
"""API routes for Server resources."""

import structlog
from fastapi import APIRouter, Depends, status

from src.application.services.server_service import ServerService
from src.infrastructure.di import get_server_service
from src.presentation.api.schemas.server import RegisterServerRequest, ServerResponse

logger = structlog.get_logger(__name__)
router = APIRouter(prefix="/servers", tags=["Servers"])


@router.post(
    "/register",
    response_model=ServerResponse,
    status_code=status.HTTP_201_CREATED,
)
async def register_server(
    payload: RegisterServerRequest,
    service: ServerService = Depends(get_server_service),
) -> ServerResponse:
    """Register a new server instance to the AI SRE Platform."""
    logger.info(
        "Received request to register server",
        hostname=payload.hostname,
        ip_address=payload.ip_address,
    )

    # Invoke application service use case
    saved_server = await service.register_server(
        hostname=payload.hostname,
        ip_address=payload.ip_address,
        operating_system=payload.operating_system,
        cpu_cores=payload.cpu_cores,
        memory_gb=payload.memory_gb,
    )

    # Return response model
    return ServerResponse.model_validate(saved_server)

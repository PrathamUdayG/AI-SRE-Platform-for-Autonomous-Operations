# src/presentation/api/v1/servers.py
# Why: Defines the API routes for Server resources.
# Receives client requests, performs DI to construct service and repository,
# and calls the application layer, separating presentation from logic.

import structlog
from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession
from src.infrastructure.database import get_db
from src.presentation.api.schemas.server import RegisterServerRequest, ServerResponse
from src.infrastructure.repositories.postgres_server_repository import PostgresServerRepository
from src.application.services.server_service import ServerService

logger = structlog.get_logger(__name__)
router = APIRouter(prefix="/servers", tags=["Servers"])

@router.post("/register", response_model=ServerResponse, status_code=status.HTTP_201_CREATED)
async def register_server(
    payload: RegisterServerRequest,
    db: AsyncSession = Depends(get_db),
) -> ServerResponse:
    """
    Register a new server instance to the AI SRE Platform.
    """
    logger.info("Received request to register server", hostname=payload.hostname, ip_address=payload.ip_address)
    
    # Construction of repository and service using current db session (DI)
    repository = PostgresServerRepository(db)
    service = ServerService(repository)

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

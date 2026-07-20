# src/presentation/api/v1/monitoring.py
"""API endpoints for health checks, rule evaluations, and monitoring history."""

from typing import List

from fastapi import APIRouter, Depends, HTTPException, status

from src.application.services.rule_engine import RuleEngine
from src.domain.exceptions import NotFoundError
from src.domain.repositories.health_repository import HealthRepository
from src.infrastructure.di import get_health_repository, get_rule_engine
from src.presentation.api.schemas.monitoring import ServerHealthResponse

router = APIRouter(prefix="/monitoring", tags=["monitoring"])


@router.post(
    "/evaluate/{server_id}",
    response_model=ServerHealthResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Evaluate server health",
    description="Run health rules evaluation on the latest telemetry metrics of a server.",
)
async def evaluate_server(
    server_id: int,
    engine: RuleEngine = Depends(get_rule_engine),
):
    """Trigger a health check evaluation on a server asset."""
    try:
        health = await engine.evaluate_server(server_id)
        return health
    except NotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Evaluation failed: {str(e)}",
        )


@router.get(
    "/health/{server_id}",
    response_model=ServerHealthResponse,
    summary="Get latest health status",
    description="Retrieve the latest calculated health evaluation report for a server.",
)
async def get_latest_health(
    server_id: int,
    repository: HealthRepository = Depends(get_health_repository),
):
    """Retrieve the latest health check report."""
    health = await repository.get_latest_by_server_id(server_id)
    if not health:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No health evaluations found for server ID {server_id}.",
        )
    return health


@router.get(
    "/history/{server_id}",
    response_model=List[ServerHealthResponse],
    summary="Get health history",
    description="Fetch a chronological list of historical health evaluation results for a server.",
)
async def get_health_history(
    server_id: int,
    limit: int = 50,
    repository: HealthRepository = Depends(get_health_repository),
):
    """Fetch health check evaluation logs history."""
    history = await repository.get_history_by_server_id(server_id, limit=limit)
    return history

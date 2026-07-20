# src/presentation/api/v1/telemetry.py
"""API routes for telemetry and metrics collection."""

from typing import List

import structlog
from fastapi import APIRouter, Depends, HTTPException, Query, status

from src.application.services.telemetry_orchestrator import TelemetryOrchestrator
from src.domain.exceptions import NotFoundError
from src.domain.repositories.telemetry_repository import TelemetryRepository
from src.infrastructure.di import get_telemetry_orchestrator, get_telemetry_repository
from src.presentation.api.schemas.telemetry import TelemetryResponse

logger = structlog.get_logger(__name__)
router = APIRouter(prefix="/telemetry", tags=["Telemetry"])


@router.post(
    "/collect/{server_id}",
    response_model=List[TelemetryResponse],
    status_code=status.HTTP_201_CREATED,
)
async def collect_telemetry(
    server_id: int,
    orchestrator: TelemetryOrchestrator = Depends(get_telemetry_orchestrator),
) -> List[TelemetryResponse]:
    """Execute a one-off telemetry collection run and persist the metrics."""
    logger.info("API trigger: collect telemetry", server_id=server_id)
    try:
        metrics = await orchestrator.collect_telemetry(server_id)
        return [TelemetryResponse.model_validate(m) for m in metrics]
    except NotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except Exception as e:
        logger.error(
            "Telemetry collection endpoint failed",
            server_id=server_id,
            error=str(e),
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e)
        )


@router.get(
    "/{server_id}",
    response_model=List[TelemetryResponse],
)
async def get_telemetry_history(
    server_id: int,
    metric_type: str = Query(
        ...,
        description="Metric type: cpu, memory, disk, network, process, service",
    ),
    limit: int = Query(100, ge=1, le=1000),
    repo: TelemetryRepository = Depends(get_telemetry_repository),
) -> List[TelemetryResponse]:
    """Retrieve telemetry collection history for a specific server and metric type."""
    logger.info(
        "API trigger: get telemetry history",
        server_id=server_id,
        metric_type=metric_type,
    )
    metrics = await repo.get_history_by_server_id(server_id, metric_type, limit=limit)
    return [TelemetryResponse.model_validate(m) for m in metrics]


@router.get(
    "/latest/{server_id}",
    response_model=TelemetryResponse,
)
async def get_latest_telemetry(
    server_id: int,
    metric_type: str = Query(
        ...,
        description="Metric type: cpu, memory, disk, network, process, service",
    ),
    repo: TelemetryRepository = Depends(get_telemetry_repository),
) -> TelemetryResponse:
    """Retrieve the latest telemetry collection sample for a specific server and metric type."""
    logger.info(
        "API trigger: get latest telemetry",
        server_id=server_id,
        metric_type=metric_type,
    )
    metric = await repo.get_latest_by_server_id(server_id, metric_type)
    if not metric:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No telemetry found for server ID {server_id} and metric type '{metric_type}'",
        )
    return TelemetryResponse.model_validate(metric)

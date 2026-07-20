# src/presentation/api/v1/incidents.py
"""API endpoints for operations incident lifecycle management."""

from typing import List

from fastapi import APIRouter, Depends, HTTPException, status

from src.application.services.incident_service import IncidentService
from src.domain.exceptions import NotFoundError
from src.infrastructure.di import get_incident_service
from src.presentation.api.schemas.incident import (
    AssignRequest,
    IncidentCreateRequest,
    IncidentHealthCreateRequest,
    IncidentResponse,
    ResolveRequest,
    StatusUpdateRequest,
    TimelineEntryResponse,
)

router = APIRouter(prefix="/incidents", tags=["incidents"])


@router.post(
    "",
    response_model=IncidentResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create manual incident",
    description="Manually raise an operational incident for a target server.",
)
async def create_incident(
    payload: IncidentCreateRequest,
    service: IncidentService = Depends(get_incident_service),
):
    """Trigger manual creation of an SRE incident."""
    try:
        incident = await service.create_incident(
            title=payload.title,
            description=payload.description,
            severity=payload.severity,
            server_id=payload.server_id,
            source=payload.source or "MANUAL",
        )
        return incident
    except NotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e)
        )


@router.post(
    "/from-health",
    response_model=IncidentResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create incident from health check",
    description="Automatically spawn an incident from a failed ServerHealth assessment ID.",
)
async def create_incident_from_health(
    payload: IncidentHealthCreateRequest,
    service: IncidentService = Depends(get_incident_service),
):
    """Trigger incident creation from ServerHealth."""
    try:
        incident = await service.create_incident_from_health(payload.health_id)
        return incident
    except NotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e)
        )


@router.get(
    "",
    response_model=List[IncidentResponse],
    summary="List all incidents",
    description="Retrieve all operational incidents chronologically.",
)
async def list_incidents(
    limit: int = 50,
    offset: int = 0,
    service: IncidentService = Depends(get_incident_service),
):
    """Get all incident records."""
    return await service.list_incidents(limit=limit, offset=offset)


@router.get(
    "/{id}",
    response_model=IncidentResponse,
    summary="Get incident details",
    description="Retrieve full details for a specific incident by ID.",
)
async def get_incident(
    id: int,
    service: IncidentService = Depends(get_incident_service),
):
    """Get a single incident record."""
    try:
        return await service.get_incident(id)
    except NotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))


@router.patch(
    "/{id}/status",
    response_model=IncidentResponse,
    summary="Update incident status",
    description="Transition incident state (e.g. to ACKNOWLEDGED, IN_PROGRESS).",
)
async def update_status(
    id: int,
    payload: StatusUpdateRequest,
    service: IncidentService = Depends(get_incident_service),
):
    """Run status transitions checks and update."""
    try:
        return await service.update_status(
            incident_id=id, new_status=payload.status, actor="operator"
        )
    except NotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.patch(
    "/{id}/assign",
    response_model=IncidentResponse,
    summary="Assign incident ownership",
    description="Assign incident ownership to a specific SRE operator.",
)
async def assign_incident(
    id: int,
    payload: AssignRequest,
    service: IncidentService = Depends(get_incident_service),
):
    """Update assigned operator details."""
    try:
        return await service.assign_incident(
            incident_id=id, assignee=payload.assignee, actor="operator"
        )
    except NotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))


@router.patch(
    "/{id}/resolve",
    response_model=IncidentResponse,
    summary="Resolve incident",
    description="Close incident out with resolution logs.",
)
async def resolve_incident(
    id: int,
    payload: ResolveRequest,
    service: IncidentService = Depends(get_incident_service),
):
    """Resolve an incident."""
    try:
        return await service.resolve_incident(
            incident_id=id,
            notes=payload.notes,
            resolved_by=payload.resolved_by,
            actor="operator",
        )
    except NotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.patch(
    "/{id}/close",
    response_model=IncidentResponse,
    summary="Close incident",
    description="Mark a resolved incident as CLOSED.",
)
async def close_incident(
    id: int,
    service: IncidentService = Depends(get_incident_service),
):
    """Archive and close out a resolved incident."""
    try:
        return await service.close_incident(incident_id=id, actor="operator")
    except NotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.get(
    "/{id}/timeline",
    response_model=List[TimelineEntryResponse],
    summary="Get incident timeline",
    description="Fetch chronological timeline actions log for a specific incident.",
)
async def get_incident_timeline(
    id: int,
    service: IncidentService = Depends(get_incident_service),
):
    """Retrieve history timeline logs list."""
    try:
        return await service.get_timeline(id)
    except NotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))

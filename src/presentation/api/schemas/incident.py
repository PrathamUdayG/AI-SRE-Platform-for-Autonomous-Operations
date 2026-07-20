# src/presentation/api/schemas/incident.py
"""API request/response schemas for operations incidents and timeline routes."""

from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, Field

from src.presentation.api.schemas.monitoring import FindingResponse


class IncidentCreateRequest(BaseModel):
    """Pydantic model representing manual incident creation payload."""

    title: str = Field(..., description="Short descriptive title of the incident")
    description: str = Field(..., description="Detailed description of the issue")
    severity: str = Field(..., description="Severity level: WARNING, CRITICAL")
    server_id: int = Field(..., description="Unique database ID of the affected server")
    source: Optional[str] = Field(
        "MANUAL", description="Origin source of incident creation"
    )


class IncidentHealthCreateRequest(BaseModel):
    """Pydantic model representing incident creation from a health evaluation."""

    health_id: int = Field(
        ..., description="Unique database ID of the health evaluation"
    )


class AssignRequest(BaseModel):
    """Pydantic payload to assign an incident to an operator."""

    assignee: str = Field(..., description="Operator username or system identifier")


class ResolveRequest(BaseModel):
    """Pydantic payload to resolve an incident with context details."""

    notes: str = Field(..., description="Details and notes on how it was resolved")
    resolved_by: str = Field(
        ..., description="Operator username who resolved this incident"
    )


class StatusUpdateRequest(BaseModel):
    """Pydantic payload to trigger status state changes."""

    status: str = Field(..., description="Target status: ACKNOWLEDGED, IN_PROGRESS")


class TimelineEntryResponse(BaseModel):
    """Pydantic model representing an incident timeline record response."""

    id: Optional[int] = Field(None, description="Event database primary key ID")
    incident_id: int = Field(..., description="Reference incident ID")
    event_type: str = Field(..., description="Event action category")
    message: str = Field(..., description="Detail message describing action")
    timestamp: datetime = Field(..., description="Timestamp of recorded action")
    actor: Optional[str] = Field(
        "system", description="User or automated component who executed action"
    )

    model_config = {"from_attributes": True}


class IncidentResponse(BaseModel):
    """Pydantic model representing an operational Incident response."""

    id: Optional[int] = Field(None, description="Incident database primary key ID")
    title: str = Field(..., description="Short title describing issue")
    description: str = Field(..., description="Full context description of issue")
    severity: str = Field(..., description="WARNING, CRITICAL")
    status: str = Field(
        ..., description="OPEN, ACKNOWLEDGED, IN_PROGRESS, RESOLVED, CLOSED"
    )
    source: str = Field(..., description="Origin source of incident")
    server_id: int = Field(..., description="Reference affected server ID")
    findings: List[FindingResponse] = Field(
        default_factory=list, description="List of related SRE rule violations"
    )
    created_at: datetime = Field(..., description="Creation timestamp")
    acknowledged_at: Optional[datetime] = Field(None, description="Ack timestamp")
    resolved_at: Optional[datetime] = Field(None, description="Resolved timestamp")
    closed_at: Optional[datetime] = Field(None, description="Closed timestamp")
    assigned_to: Optional[str] = Field(None, description="Assigned operator/agent")
    resolution_notes: Optional[str] = Field(None, description="Resolution notes")

    model_config = {"from_attributes": True}

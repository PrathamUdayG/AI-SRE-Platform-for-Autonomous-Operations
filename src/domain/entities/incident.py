# src/domain/entities/incident.py
"""Domain entities and aggregate roots for operations incidents."""

from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field

from src.domain.entities.health import Finding


class Assignment(BaseModel):
    """Value object representing an incident assignment event."""

    assignee: str = Field(..., description="Username or system component assigned")
    assigned_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        description="Timestamp of assignment",
    )


class Resolution(BaseModel):
    """Value object representing an incident resolution summary."""

    resolved_by: str = Field(..., description="Actor resolving the incident")
    resolution_notes: str = Field(..., description="Resolution details and steps taken")
    resolved_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        description="Timestamp of resolution",
    )


class TimelineEntry(BaseModel):
    """Entity representing a historical event on the incident timeline."""

    id: Optional[int] = Field(
        default=None, description="Timeline entry database key ID"
    )
    incident_id: int = Field(..., description="Reference incident ID")
    event_type: str = Field(
        ...,
        description="Type of timeline event: CREATED, ACKNOWLEDGED, ASSIGNED, STATUS_CHANGED, RESOLVED, CLOSED",
    )
    message: str = Field(..., description="Human-readable event summary")
    timestamp: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        description="Timestamp when event occurred",
    )
    actor: Optional[str] = Field(
        default="system", description="Actor who initiated this event"
    )

    model_config = {"from_attributes": True}


class Incident(BaseModel):
    """Aggregate root representing an operational SRE incident."""

    id: Optional[int] = Field(default=None, description="Incident database key ID")
    title: str = Field(..., description="Short descriptive title")
    description: str = Field(..., description="Detailed explanation of incident")
    severity: str = Field(..., description="Incident severity level: WARNING, CRITICAL")
    status: str = Field(
        default="OPEN",
        description="Incident state: OPEN, ACKNOWLEDGED, IN_PROGRESS, RESOLVED, CLOSED",
    )
    source: str = Field(
        default="MONITORING", description="Origin source: e.g. MONITORING, MANUAL"
    )
    server_id: int = Field(..., description="Affected server reference ID")
    findings: List[Finding] = Field(
        default_factory=list,
        description="List of related health findings and violations",
    )
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        description="Incident creation timestamp",
    )
    acknowledged_at: Optional[datetime] = Field(
        default=None, description="Incident acknowledgement timestamp"
    )
    resolved_at: Optional[datetime] = Field(
        default=None, description="Incident resolution timestamp"
    )
    closed_at: Optional[datetime] = Field(
        default=None, description="Incident closure timestamp"
    )
    assigned_to: Optional[str] = Field(
        default=None, description="Actor currently assigned to this incident"
    )
    resolution_notes: Optional[str] = Field(
        default=None,
        description="Resolution notes provided during resolution step",
    )

    model_config = {"from_attributes": True}

    def transition_to(self, new_status: str) -> None:
        """Execute state machine transitions and record appropriate timestamps."""
        allowed = {
            "OPEN": ["ACKNOWLEDGED"],
            "ACKNOWLEDGED": ["IN_PROGRESS"],
            "IN_PROGRESS": ["RESOLVED"],
            "RESOLVED": ["CLOSED"],
            "CLOSED": [],
        }
        current = self.status.upper()
        target = new_status.upper()

        if target not in allowed.get(current, []):
            raise ValueError(f"Invalid state transition from {current} to {target}")

        self.status = target
        now = datetime.now(timezone.utc)
        if target == "ACKNOWLEDGED":
            self.acknowledged_at = now
        elif target == "RESOLVED":
            self.resolved_at = now
        elif target == "CLOSED":
            self.closed_at = now

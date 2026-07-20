# src/infrastructure/persistence/models.py
"""SQLAlchemy ORM database models."""

from datetime import datetime
from typing import Any, Dict, List, Optional

from sqlalchemy import JSON, DateTime, Float, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.sql import func

from src.infrastructure.database import Base


class MetricModel(Base):
    """SQLAlchemy ORM model for the 'metrics' table."""

    __tablename__ = "metrics"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    name: Mapped[str] = mapped_column(String, nullable=False)
    value: Mapped[float] = mapped_column(Float, nullable=False)
    timestamp: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    service: Mapped[str] = mapped_column(String, nullable=False)
    tags: Mapped[Dict[str, str]] = mapped_column(JSON, nullable=False, default=dict)


class ServerModel(Base):
    """SQLAlchemy ORM model for the 'servers' table."""

    __tablename__ = "servers"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    hostname: Mapped[str] = mapped_column(
        String, unique=True, index=True, nullable=False
    )
    ip_address: Mapped[str] = mapped_column(
        String, unique=True, index=True, nullable=False
    )
    operating_system: Mapped[str] = mapped_column(String, nullable=False)
    cpu_cores: Mapped[int] = mapped_column(Integer, nullable=False)
    memory_gb: Mapped[float] = mapped_column(Float, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )


class DiscoverySnapshotModel(Base):
    """SQLAlchemy ORM model for the 'discovery_snapshots' table."""

    __tablename__ = "discovery_snapshots"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    server_id: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    hostname: Mapped[str] = mapped_column(String, nullable=False)
    operating_system: Mapped[str] = mapped_column(String, nullable=False)
    kernel_version: Mapped[str] = mapped_column(String, nullable=False)
    architecture: Mapped[str] = mapped_column(String, nullable=False)
    uptime: Mapped[str] = mapped_column(String, nullable=False)
    timezone: Mapped[str] = mapped_column(String, nullable=False)

    # Save nested JSON payloads
    cpu: Mapped[Dict[str, Any]] = mapped_column(JSON, nullable=False)
    memory: Mapped[Dict[str, Any]] = mapped_column(JSON, nullable=False)
    disks: Mapped[list[Dict[str, Any]]] = mapped_column(JSON, nullable=False)
    network_interfaces: Mapped[list[Dict[str, Any]]] = mapped_column(
        JSON, nullable=False
    )

    discovered_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )


class InventoryModel(Base):
    """SQLAlchemy ORM model for the 'inventory' table."""

    __tablename__ = "inventory"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    server_id: Mapped[int] = mapped_column(
        Integer, nullable=False, unique=True, index=True
    )
    hostname: Mapped[str] = mapped_column(String, nullable=False)
    operating_system: Mapped[str] = mapped_column(String, nullable=False)
    kernel_version: Mapped[str] = mapped_column(String, nullable=False)
    architecture: Mapped[str] = mapped_column(String, nullable=False)
    uptime: Mapped[str] = mapped_column(String, nullable=False)
    timezone: Mapped[str] = mapped_column(String, nullable=False)

    # Save nested JSON payloads
    cpu: Mapped[Dict[str, Any]] = mapped_column(JSON, nullable=False)
    memory: Mapped[Dict[str, Any]] = mapped_column(JSON, nullable=False)
    disks: Mapped[list[Dict[str, Any]]] = mapped_column(JSON, nullable=False)
    network_interfaces: Mapped[list[Dict[str, Any]]] = mapped_column(
        JSON, nullable=False
    )
    last_discovered_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )

    # Metadata & Tags
    environment: Mapped[Optional[str]] = mapped_column(
        String, nullable=True, index=True
    )
    owner: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    project: Mapped[Optional[str]] = mapped_column(String, nullable=True, index=True)
    business_unit: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    region: Mapped[Optional[str]] = mapped_column(String, nullable=True, index=True)
    datacenter: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    role: Mapped[Optional[str]] = mapped_column(String, nullable=True, index=True)
    criticality: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    connector_type: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    tags: Mapped[Dict[str, str]] = mapped_column(JSON, nullable=False, default=dict)

    version: Mapped[int] = mapped_column(Integer, nullable=False, default=1)


class TelemetryMetricModel(Base):
    """SQLAlchemy ORM model for the 'telemetry_metrics' table."""

    __tablename__ = "telemetry_metrics"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    server_id: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    metric_type: Mapped[str] = mapped_column(String, nullable=False, index=True)
    timestamp: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, index=True
    )
    data: Mapped[Dict[str, Any]] = mapped_column(JSON, nullable=False)


class ServerHealthModel(Base):
    """SQLAlchemy ORM model for the 'server_health' table."""

    __tablename__ = "server_health"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    server_id: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    overall_status: Mapped[str] = mapped_column(String, nullable=False)
    health_score: Mapped[float] = mapped_column(Float, nullable=False)
    findings: Mapped[List[Dict[str, Any]]] = mapped_column(
        JSON, nullable=False, default=list
    )
    evaluation_timestamp: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, index=True
    )


class IncidentModel(Base):
    """SQLAlchemy ORM model for the 'incidents' table."""

    __tablename__ = "incidents"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    title: Mapped[str] = mapped_column(String, nullable=False)
    description: Mapped[str] = mapped_column(String, nullable=False)
    severity: Mapped[str] = mapped_column(String, nullable=False)
    status: Mapped[str] = mapped_column(String, nullable=False, default="OPEN")
    source: Mapped[str] = mapped_column(String, nullable=False, default="MONITORING")
    server_id: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    findings: Mapped[List[Dict[str, Any]]] = mapped_column(
        JSON, nullable=False, default=list
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, index=True
    )
    acknowledged_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    resolved_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    closed_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    assigned_to: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    resolution_notes: Mapped[Optional[str]] = mapped_column(String, nullable=True)


class TimelineEntryModel(Base):
    """SQLAlchemy ORM model for the 'incident_timeline' table."""

    __tablename__ = "incident_timeline"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    incident_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("incidents.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    event_type: Mapped[str] = mapped_column(String, nullable=False)
    message: Mapped[str] = mapped_column(String, nullable=False)
    timestamp: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, index=True
    )
    actor: Mapped[Optional[str]] = mapped_column(
        String, nullable=True, default="system"
    )

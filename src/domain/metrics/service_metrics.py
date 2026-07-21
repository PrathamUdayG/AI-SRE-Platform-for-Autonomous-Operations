"""
-------------------------------------------------------
File:
service_metrics.py

Purpose:
Domain model representing active and inactive systemd service statuses.

Why this file exists:
Provides a strongly typed, OS-agnostic representation of system service configurations, startup states, and process ownership.

Responsibilities:
- Encapsulate systemd service attributes like LoadState, ActiveState, MainPID, and enabled status.

Used By:
- ServiceParser
- ServiceCollector

Notes:
This file belongs to the Domain Layer as it defines a core telemetry data structure.
-------------------------------------------------------
"""

from datetime import datetime
from typing import List, Optional
from pydantic import BaseModel, Field


class ServiceUnit(BaseModel):
    """
    Why this class exists:
    Encapsulates specific properties of a single systemd service.
    """

    name: str = Field(description="Name of the service (e.g. ssh.service)")
    description: str = Field(default="", description="Service description")
    load_state: str = Field(description="Load state of unit file (e.g. loaded)")
    active_state: str = Field(description="Active state (e.g. active, inactive)")
    sub_state: str = Field(description="Sub execution state (e.g. running, dead)")
    unit_file_state: Optional[str] = Field(None, description="Unit file state (e.g. enabled, disabled)")
    main_pid: Optional[int] = Field(None, description="Main process identifier")
    service_type: Optional[str] = Field(None, description="Service startup type (e.g. simple, notify)")
    restart_policy: Optional[str] = Field(None, description="Service restart policy")
    fragment_path: Optional[str] = Field(None, description="Systemd fragment definition file path")
    is_enabled: bool = Field(description="Whether the service is enabled to start on boot")


class ServiceMetrics(BaseModel):
    """
    Why this class exists:
    Main container model for all systemd services telemetry.
    """

    services: List[ServiceUnit] = Field(
        default_factory=list, description="List of systemd services"
    )
    timestamp: datetime = Field(description="UTC timestamp of when the metrics were captured")

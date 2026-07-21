"""
-------------------------------------------------------
File:
collector_result.py

Purpose:
Represents the common output format returned by every collector.

Why this file exists:
Every collector (CPU, Memory, Disk, Network, etc.) should return a consistent structure so the rest of the platform never depends on Linux-specific implementations.

Responsibilities:
- Store execution metadata (timestamp, hostname, execution time)
- Store collected payload (structured JSON dict)
- Store execution status (CollectorStatus)
- Store collector name
- Store execution errors (list of strings)

Used By:
- Collector Runner
- CPU Collector
- Memory Collector
- Disk Collector
- Future RCA Engine

Notes:
This file belongs to the Domain Layer because it represents a business object and does not depend on Linux commands.
-------------------------------------------------------
"""

from datetime import datetime
from typing import Any, Dict, List
from pydantic import BaseModel, Field

from src.domain.collectors.collector_status import CollectorStatus
from src.domain.collectors.metric_type import MetricType


class CollectorResult(BaseModel):
    """
    Why this class exists:
    Encapsulates the standard schema returned by every collector execution.

    Responsibility:
    Hold telemetry data, execution time, errors, and metadata in a structured format.

    Who uses it:
    Collectors, runners, and storage/RCA layers.

    Why it belongs in this layer:
    It acts as the core data contract between the collection subsystem and outer layers.
    """

    timestamp: datetime = Field(description="UTC timestamp of the collection run")
    hostname: str = Field(description="Hostname of the target server")
    collector_name: str = Field(description="Name of the collector that executed")
    metric_type: MetricType = Field(description="The category of telemetry collected")
    payload: Dict[str, Any] = Field(default_factory=dict, description="Structured telemetry data")
    status: CollectorStatus = Field(description="Outcome status of the execution")
    errors: List[str] = Field(default_factory=list, description="Errors encountered during execution")
    execution_time_ms: int = Field(description="Time taken to execute in milliseconds")

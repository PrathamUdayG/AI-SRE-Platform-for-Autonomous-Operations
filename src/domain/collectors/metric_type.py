"""
-------------------------------------------------------
File:
metric_type.py

Purpose:
Defines the Enum representing the types of metrics/telemetry collected.

Why this file exists:
By using a centralized Enum, we prevent hardcoded strings and ensure consistency across all collectors and database models.

Responsibilities:
- Define valid telemetry types (CPU, MEMORY, DISK, etc.)

Used By:
- CollectorResult
- All Collector implementations
- Repository Layer

Notes:
This file belongs to the Domain Layer because it represents a core domain concept (telemetry categories).
-------------------------------------------------------
"""

from enum import Enum


class MetricType(str, Enum):
    """
    Why this class exists:
    Categorizes the type of metrics collected by any Collector.

    Responsibility:
    Provide type-safe metric categorization.

    Who uses it:
    CollectorResult, Collectors, and the application orchestrator.

    Why it belongs in this layer:
    It defines a core domain concept independent of external infrastructure.
    """

    CPU = "CPU"
    MEMORY = "MEMORY"
    DISK = "DISK"
    NETWORK = "NETWORK"
    PROCESS = "PROCESS"
    SERVICE = "SERVICE"
    LOG = "LOG"
    DOCKER = "DOCKER"
    KUBERNETES = "KUBERNETES"
    SYSTEM = "SYSTEM"


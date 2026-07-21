"""
-------------------------------------------------------
File:
__init__.py

Purpose:
Package entry point for telemetry orchestrators.

Why this file exists:
Provides clean package-level imports for the CollectorRegistry and CollectorOrchestrator.
-------------------------------------------------------
"""

from src.application.orchestrator.collector_orchestrator import (
    CollectorOrchestrator,
)
from src.application.orchestrator.collector_registry import CollectorRegistry

__all__ = [
    "CollectorOrchestrator",
    "CollectorRegistry",
]

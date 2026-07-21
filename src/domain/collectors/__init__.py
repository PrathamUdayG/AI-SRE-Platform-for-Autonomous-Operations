"""
-------------------------------------------------------
File:
__init__.py

Purpose:
Package entry point for domain-level collector contracts and models.

Why this file exists:
Provides clean package-level imports for other components of the platform.

Responsibilities:
- Expose MetricType, CollectorStatus, CollectorResult, and Collector interface

Used By:
- Application Layer Orchestrators
- Infrastructure Collectors
-------------------------------------------------------
"""

from src.domain.collectors.collector import Collector
from src.domain.collectors.collector_result import CollectorResult
from src.domain.collectors.collector_status import CollectorStatus
from src.domain.collectors.metric_type import MetricType

__all__ = [
    "Collector",
    "CollectorResult",
    "CollectorStatus",
    "MetricType",
]

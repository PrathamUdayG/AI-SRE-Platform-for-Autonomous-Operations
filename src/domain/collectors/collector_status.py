"""
-------------------------------------------------------
File:
collector_status.py

Purpose:
Defines the Enum representing the execution status of a collector run.

Why this file exists:
Every collector execution might succeed, fail, or be partially successful. We need a standard status representation.

Responsibilities:
- Define valid execution status values (SUCCESS, FAILED, UNAVAILABLE, PARTIAL)

Used By:
- CollectorResult
- Collector Runner
- Repository Layer

Notes:
This file belongs to the Domain Layer as it specifies a core business status concept.
-------------------------------------------------------
"""

from enum import Enum


class CollectorStatus(str, Enum):
    """
    Why this class exists:
    Represents the health and outcome of an individual collector's execution.

    Responsibility:
    Provide standardized execution status flags.

    Who uses it:
    CollectorResult, Collectors, and the monitoring orchestrator.

    Why it belongs in this layer:
    It is a domain-level abstraction of execution results, separate from implementation.
    """

    SUCCESS = "SUCCESS"
    FAILED = "FAILED"
    UNAVAILABLE = "UNAVAILABLE"
    PARTIAL = "PARTIAL"

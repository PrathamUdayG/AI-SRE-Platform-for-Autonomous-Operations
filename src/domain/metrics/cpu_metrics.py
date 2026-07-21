"""
-------------------------------------------------------
File:
cpu_metrics.py

Purpose:
Domain model representing physical and virtual CPU statistics.

Why this file exists:
Provides a strongly typed, OS-agnostic representation of system processor metrics, load averages, and core counts.

Responsibilities:
- Encapsulate CPU metric fields parsed from Linux /proc/stat and /proc/loadavg.

Used By:
- CPUParser
- CPUCollector

Notes:
This file belongs to the Domain Layer as it defines a core telemetry data structure.
-------------------------------------------------------
"""

from datetime import datetime
from pydantic import BaseModel, Field


class CPUMetrics(BaseModel):
    """
    Why this class exists:
    Encapsulates system CPU metric properties in a validated Pydantic model.

    Responsibility:
    Hold CPU time ticks, load averages, core count, and collection timestamp.

    Who uses it:
    Parsers, Collectors, and application layer orchestrators.
    """

    user_ticks: int = Field(description="Ticks spent in user mode")
    system_ticks: int = Field(description="Ticks spent in system mode")
    idle_ticks: int = Field(description="Ticks spent in idle tasks")
    iowait_ticks: int = Field(description="Ticks spent waiting for I/O to complete")
    irq_ticks: int = Field(description="Ticks servicing hardware interrupts")
    softirq_ticks: int = Field(description="Ticks servicing soft interrupts")
    steal_ticks: int = Field(description="Ticks spent in virtualized operating systems")
    guest_ticks: int = Field(description="Ticks spent running a virtual CPU for guest OS")
    load_average_1m: float = Field(description="1 minute load average")
    load_average_5m: float = Field(description="5 minute load average")
    load_average_15m: float = Field(description="15 minute load average")
    logical_cpu_count: int = Field(description="Number of logical CPUs available")
    timestamp: datetime = Field(description="UTC timestamp of when the metrics were captured")

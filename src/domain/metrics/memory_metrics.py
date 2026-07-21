"""
-------------------------------------------------------
File:
memory_metrics.py

Purpose:
Domain model representing physical and swap memory statistics.

Why this file exists:
Provides a strongly typed, OS-agnostic business representation of memory usage. It ensures other services consume normalized python metrics instead of raw kernel text.

Responsibilities:
- Encapsulate memory fields parsed from Linux /proc/meminfo.

Used By:
- MemoryParser
- MemoryCollector

Notes:
This file belongs to the Domain Layer as it defines the core data structure for system memory.
-------------------------------------------------------
"""

from datetime import datetime
from pydantic import BaseModel, Field


class MemoryMetrics(BaseModel):
    """
    Why this class exists:
    Encapsulates system memory metric properties in a validated model.

    Responsibility:
    Hold memory fields (total, free, swap, buffers, etc.) and timestamp.

    Who uses it:
    Parses, Collectors, and application layer consumers.
    """

    total_memory_kb: int = Field(description="Total usable RAM in kilobytes")
    free_memory_kb: int = Field(description="Unused physical memory in kilobytes")
    available_memory_kb: int = Field(
        description="Estimate of how much memory is available for starting new applications without swapping in kilobytes"
    )
    buffers_kb: int = Field(description="Temporary storage for raw disk blocks in kilobytes")
    cached_kb: int = Field(description="In-memory cache for files read from disk in kilobytes")
    swap_total_kb: int = Field(description="Total amount of swap space available in kilobytes")
    swap_free_kb: int = Field(description="Amount of swap space currently unused in kilobytes")
    dirty_kb: int = Field(
        description="Memory waiting to be written back to disk in kilobytes"
    )
    timestamp: datetime = Field(description="UTC timestamp of when the metrics were captured")

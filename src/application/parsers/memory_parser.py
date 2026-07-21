"""
-------------------------------------------------------
File:
memory_parser.py

Purpose:
Parses raw /proc/meminfo text into structured MemoryMetrics objects.

Why this file exists:
Isolates the string parsing logic from the collector. This ensures that the parsing engine can be tested independently of system commands and command execution failures.

Responsibilities:
- Parse key-value lines from /proc/meminfo output.
- Validate values and map them to MemoryMetrics.
- Handle missing fields gracefully by defaulting to 0 or raising validation errors.

Used By:
- MemoryCollector

Depends On:
- src.domain.metrics.memory_metrics.MemoryMetrics
- src.domain.exceptions.ValidationError
-------------------------------------------------------
"""

from datetime import datetime
import structlog

from src.domain.exceptions import ValidationError
from src.domain.metrics.memory_metrics import MemoryMetrics

logger = structlog.get_logger(__name__)


class MemoryParser:
    """
    Why this class exists:
    A utility class containing static methods for parsing memory logs.

    Responsibility:
    Convert raw /proc/meminfo text lines into strongly-typed MemoryMetrics.

    Who uses it:
    MemoryCollector and diagnostic script parsers.
    """

    @staticmethod
    def parse(raw_output: str, timestamp: datetime) -> MemoryMetrics:
        """
        Parse raw stdout from 'cat /proc/meminfo' and return a MemoryMetrics instance.

        Args:
            raw_output (str): Raw string output of the proc file.
            timestamp (datetime): UTC timestamp of collection.

        Returns:
            MemoryMetrics: Structured, type-validated memory metrics.

        Raises:
            ValidationError: If the raw output is empty, completely malformed,
                             or missing core fields.
        """
        if not raw_output or not raw_output.strip():
            raise ValidationError("Raw /proc/meminfo output is empty or whitespace.")

        metrics_dict = {}
        for line in raw_output.splitlines():
            line = line.strip()
            if not line:
                continue

            parts = line.split(":", 1)
            if len(parts) != 2:
                continue

            key = parts[0].strip()
            val_part = parts[1].strip()

            # Split value from potential units (e.g. "16388432 kB" -> "16388432")
            val_tokens = val_part.split()
            if not val_tokens:
                continue

            try:
                # Convert first token to integer
                metrics_dict[key] = int(val_tokens[0])
            except ValueError:
                logger.debug("Failed to parse integer from field", key=key, value=val_tokens[0])
                continue

        # Check that we parsed at least some fields to ensure it is not completely malformed
        if not metrics_dict:
            raise ValidationError("Could not parse any valid key-value pairs from /proc/meminfo.")

        # Map proc keys to model attributes, defaulting missing ones to 0
        try:
            return MemoryMetrics(
                total_memory_kb=metrics_dict.get("MemTotal", 0),
                free_memory_kb=metrics_dict.get("MemFree", 0),
                available_memory_kb=metrics_dict.get("MemAvailable", 0),
                buffers_kb=metrics_dict.get("Buffers", 0),
                cached_kb=metrics_dict.get("Cached", 0),
                swap_total_kb=metrics_dict.get("SwapTotal", 0),
                swap_free_kb=metrics_dict.get("SwapFree", 0),
                dirty_kb=metrics_dict.get("Dirty", 0),
                timestamp=timestamp,
            )
        except Exception as e:
            raise ValidationError(f"Failed to instantiate MemoryMetrics model: {str(e)}")

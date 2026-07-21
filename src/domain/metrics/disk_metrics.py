"""
-------------------------------------------------------
File:
disk_metrics.py

Purpose:
Domain model representing filesystem utilization and disk device I/O statistics.

Why this file exists:
Provides a strongly typed, OS-agnostic representation of system disk partition usages and low-level device controller metrics.

Responsibilities:
- Encapsulate disk metrics fields parsed from df output and /proc/diskstats.

Used By:
- DiskParser
- DiskCollector

Notes:
This file belongs to the Domain Layer as it defines a core telemetry data structure.
-------------------------------------------------------
"""

from datetime import datetime
from typing import List
from pydantic import BaseModel, Field


class FilesystemMetrics(BaseModel):
    """
    Why this class exists:
    Encapsulates specific partition usage statistics.
    """

    filesystem: str = Field(description="Name/source of the filesystem (e.g. /dev/sda1)")
    fstype: str = Field(description="Type of the filesystem (e.g. ext4)")
    total_bytes: int = Field(description="Total space capacity in bytes")
    used_bytes: int = Field(description="Used space in bytes")
    available_bytes: int = Field(description="Available space in bytes")
    use_percent: int = Field(description="Usage percentage as an integer (e.g. 45)")
    mount_point: str = Field(description="Mount point target (e.g. /)")


class DiskIOMetrics(BaseModel):
    """
    Why this class exists:
    Encapsulates low-level disk controller I/O counters.
    """

    major_number: int = Field(description="Major device number")
    minor_number: int = Field(description="Minor device number")
    device_name: str = Field(description="Name of the storage device (e.g. sda)")
    reads_completed: int = Field(description="Reads completed successfully")
    reads_merged: int = Field(description="Reads merged adjacent to other reads")
    sectors_read: int = Field(description="Total sectors read")
    read_time_ms: int = Field(description="Time spent reading in milliseconds")
    writes_completed: int = Field(description="Writes completed successfully")
    writes_merged: int = Field(description="Writes merged adjacent to other writes")
    sectors_written: int = Field(description="Total sectors written")
    write_time_ms: int = Field(description="Time spent writing in milliseconds")
    io_in_progress: int = Field(description="I/Os currently in progress")
    io_time_ms: int = Field(description="Time spent doing I/Os in milliseconds")
    weighted_io_time_ms: int = Field(description="Weighted time spent doing I/Os in milliseconds")


class DiskMetrics(BaseModel):
    """
    Why this class exists:
    Encapsulates all disk system statistics in a single model.
    """

    filesystems: List[FilesystemMetrics] = Field(
        default_factory=list, description="List of filesystem partition metrics"
    )
    disk_io: List[DiskIOMetrics] = Field(
        default_factory=list, description="List of low-level device I/O statistics"
    )
    timestamp: datetime = Field(description="UTC timestamp of when the metrics were captured")

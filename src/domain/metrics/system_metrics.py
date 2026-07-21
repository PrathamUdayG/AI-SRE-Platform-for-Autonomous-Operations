"""
-------------------------------------------------------
File:
system_metrics.py

Purpose:
Domain model representing static host metadata, hardware attributes, and OS details.

Why this file exists:
Provides a strongly typed, OS-agnostic representation of system specifications and configuration.

Responsibilities:
- Encapsulate host identity, OS properties, CPU hardware specs, virtualization parameters, and timezones.

Used By:
- SystemParser
- SystemCollector

Notes:
This file belongs to the Domain Layer as it defines a core telemetry data structure.
-------------------------------------------------------
"""

from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field


class HostIdentity(BaseModel):
    """
    Why this class exists:
    Encapsulates identity metadata for the host machine.
    """

    hostname: str = Field(description="Hostname of the machine")
    machine_id: Optional[str] = Field(None, description="Unique machine ID from /etc/machine-id")
    boot_id: Optional[str] = Field(None, description="Unique boot ID")


class OperatingSystemInfo(BaseModel):
    """
    Why this class exists:
    Encapsulates operating system distribution and kernel release statistics.
    """

    distribution_name: str = Field(description="Linux distribution name (e.g. Ubuntu)")
    distribution_version: str = Field(description="Distribution version string (e.g. 22.04)")
    pretty_name: str = Field(description="Pretty formatted OS string")
    kernel_version: str = Field(description="Detailed kernel compile/version text")
    kernel_release: str = Field(description="Kernel release string (e.g. 5.15.0-generic)")
    architecture: str = Field(description="Processor architecture (e.g. x86_64)")


class CPUInfo(BaseModel):
    """
    Why this class exists:
    Encapsulates static CPU model and topology layout attributes.
    """

    cpu_model: str = Field(description="Full name of CPU model")
    vendor: str = Field(description="CPU vendor identifier")
    logical_cpu_count: int = Field(description="Total online logical CPUs count")
    physical_cpu_count: Optional[int] = Field(None, description="Physical CPU socket count")
    threads_per_core: int = Field(description="Number of threads per CPU core")
    cores_per_socket: int = Field(description="Number of cores per physical socket")
    cpu_mhz: Optional[float] = Field(None, description="Current CPU frequency in MHz")


class HardwareInfo(BaseModel):
    """
    Why this class exists:
    Encapsulates hypervisor and virtualization attributes.
    """

    virtualization_type: str = Field(description="Type of virtualization (e.g. kvm, microsoft, none)")
    hypervisor_vendor: Optional[str] = Field(None, description="Hypervisor provider vendor name")


class SystemState(BaseModel):
    """
    Why this class exists:
    Encapsulates boot/runtime states of the host.
    """

    system_uptime: float = Field(description="Host uptime duration in seconds")
    boot_time: Optional[datetime] = Field(None, description="Calculated UTC date/time of system boot")


class SystemMetrics(BaseModel):
    """
    Why this class exists:
    Container model grouping all static host metadata parameters together.
    """

    host_identity: HostIdentity = Field(description="Identity attributes of the host")
    os_info: OperatingSystemInfo = Field(description="Operating system release parameters")
    cpu_info: CPUInfo = Field(description="Static CPU topology metadata")
    hardware: HardwareInfo = Field(description="Virtualization and hypervisor details")
    system_state: SystemState = Field(description="Host runtime/uptime details")
    timezone: str = Field(description="System timezone name (e.g. UTC)")
    operating_mode: str = Field(description="Operating mode / hostname status (e.g. static, transient)")
    timestamp: datetime = Field(description="UTC timestamp of when the metrics were captured")

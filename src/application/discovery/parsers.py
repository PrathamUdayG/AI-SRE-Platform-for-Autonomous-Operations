# src/application/discovery/parsers.py
"""Parsers for converting raw CLI command outputs into strongly-typed domain models."""

import re
from typing import Dict, List

from src.domain.entities.discovery import (
    CPUInfo,
    DiskInfo,
    MemoryInfo,
    NetworkInterfaceInfo,
)


class OSParser:
    """Parses /etc/os-release CLI output."""

    @staticmethod
    def parse(output: str) -> str:
        """Parse PRETTY_NAME or NAME from os-release output."""
        match = re.search(r'PRETTY_NAME="([^"]+)"', output)
        if match:
            return match.group(1)
        match = re.search(r'NAME="([^"]+)"', output)
        if match:
            return match.group(1)
        return "Unknown Linux"


class CPUParser:
    """Parses lscpu CLI output."""

    @staticmethod
    def parse(output: str) -> CPUInfo:
        """Parse core attributes from lscpu."""
        model = "Unknown CPU"
        cores = 1
        sockets = 1
        threads = 1
        arch = "Unknown"

        for line in output.splitlines():
            if "Model name:" in line:
                model = line.split(":", 1)[1].strip()
            elif "CPU(s):" in line and "NUMA" not in line:
                try:
                    cores = int(line.split(":", 1)[1].strip())
                except ValueError:
                    pass
            elif "Socket(s):" in line:
                try:
                    sockets = int(line.split(":", 1)[1].strip())
                except ValueError:
                    pass
            elif "Thread(s) per core:" in line:
                try:
                    threads = int(line.split(":", 1)[1].strip())
                except ValueError:
                    pass
            elif "Architecture:" in line:
                arch = line.split(":", 1)[1].strip()

        return CPUInfo(
            model=model,
            cores=cores,
            sockets=sockets,
            threads_per_core=threads,
            architecture=arch,
        )


class MemoryParser:
    """Parses free -m CLI output."""

    @staticmethod
    def parse(output: str) -> MemoryInfo:
        """Parse free fields from system RAM readout."""
        lines = output.splitlines()
        for line in lines:
            if line.startswith("Mem:"):
                parts = line.split()
                if len(parts) >= 7:
                    return MemoryInfo(
                        total_mb=float(parts[1]),
                        used_mb=float(parts[2]),
                        free_mb=float(parts[3]),
                        shared_mb=float(parts[4]),
                        buff_cache_mb=float(parts[5]),
                        available_mb=float(parts[6]),
                    )
        return MemoryInfo(
            total_mb=0.0,
            used_mb=0.0,
            free_mb=0.0,
            shared_mb=0.0,
            buff_cache_mb=0.0,
            available_mb=0.0,
        )


class FilesystemParser:
    """Parses df -hT CLI output."""

    @staticmethod
    def parse(output: str) -> List[DiskInfo]:
        """Parse mounted devices and capacities in GB."""
        disks: List[DiskInfo] = []
        lines = output.splitlines()
        if not lines:
            return disks

        for line in lines[1:]:  # Skip header
            parts = line.split()
            if len(parts) >= 7:
                device = parts[0]
                fstype = parts[1]
                size_str = parts[2]
                used_str = parts[3]
                avail_str = parts[4]
                pct_str = parts[5].replace("%", "")
                mount_point = parts[6]

                # Filter out system loop devices or pseudo partitions
                if (
                    device in ("udev", "tmpfs", "devtmpfs")
                    or mount_point.startswith("/boot/efi")
                    or mount_point.startswith("/snap")
                ):
                    continue

                def to_gb(s: str) -> float:
                    s = s.upper()
                    # extract float/int parts
                    digits = re.findall(r"[\d\.]+", s)
                    if not digits:
                        return 0.0
                    val = float(digits[0])
                    if "M" in s:
                        return val / 1024.0
                    elif "T" in s:
                        return val * 1024.0
                    return val

                try:
                    disks.append(
                        DiskInfo(
                            device=device,
                            mount_point=mount_point,
                            fstype=fstype,
                            total_gb=to_gb(size_str),
                            used_gb=to_gb(used_str),
                            free_gb=to_gb(avail_str),
                            percentage=float(pct_str),
                        )
                    )
                except Exception:
                    pass
        return disks


class NetworkParser:
    """Parses ip -o addr show CLI output."""

    @staticmethod
    def parse(output: str) -> List[NetworkInterfaceInfo]:
        """Parse interface list, states, and bound IPs."""
        interfaces: Dict[str, List[str]] = {}
        for line in output.splitlines():
            parts = line.split()
            if len(parts) >= 4:
                ifparts = parts[1]
                ifname = ifparts.rstrip(":")

                # Ignore loopback interface if necessary or keep it
                if "inet" in parts:
                    idx = parts.index("inet")
                    ip = parts[idx + 1].split("/")[0]
                    if ifname not in interfaces:
                        interfaces[ifname] = []
                    interfaces[ifname].append(ip)
                elif "inet6" in parts:
                    idx = parts.index("inet6")
                    ip = parts[idx + 1].split("/")[0]
                    if ifname not in interfaces:
                        interfaces[ifname] = []
                    interfaces[ifname].append(ip)

        results = []
        for name, ips in interfaces.items():
            results.append(
                NetworkInterfaceInfo(
                    name=name, ip_addresses=ips, state="UP", mac_address=None
                )
            )
        return results


class TimezoneParser:
    """Parses timedatectl CLI output."""

    @staticmethod
    def parse(output: str) -> str:
        """Parse timezone name from timedatectl."""
        for line in output.splitlines():
            if "Time zone:" in line or "Timezone:" in line:
                return line.split(":", 1)[1].strip()
        return "UTC"


class UptimeParser:
    """Parses uptime CLI output."""

    @staticmethod
    def parse(output: str) -> str:
        """Parse uptime duration segment."""
        match = re.search(r"up\s+(.*?),\s+\d+\s+user", output)
        if match:
            return match.group(1)
        match = re.search(r"up\s+(.*?),\s+load", output)
        if match:
            return match.group(1)
        return output.strip()

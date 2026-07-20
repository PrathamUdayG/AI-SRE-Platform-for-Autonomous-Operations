# src/application/telemetry/parsers.py
"""Parsers to translate raw command outputs into structured dictionary formats."""

import re
from typing import Any, Dict, List


class CPUTelemetryParser:
    """Parses top/loadavg commands to evaluate CPU utilization."""

    @staticmethod
    def parse(output: str) -> Dict[str, Any]:
        """Parse CPU idle percentage from top output and determine total usage."""
        # Top output line: "%Cpu(s):  5.0 us,  2.0 sy,  0.0 ni, 93.0 id ..."
        match = re.search(r"(\d+\.\d+)\s+id", output)
        if match:
            idle = float(match.group(1))
            usage = round(100.0 - idle, 2)
            return {"usage_percent": usage, "idle_percent": idle}

        # Fallback to loadavg if top command output is different
        # "0.00 0.01 0.05 1/152 12345"
        parts = output.split()
        if len(parts) >= 3:
            try:
                return {
                    "load_1m": float(parts[0]),
                    "load_5m": float(parts[1]),
                    "load_15m": float(parts[2]),
                }
            except ValueError:
                pass

        return {"usage_percent": 0.0, "idle_percent": 100.0}


class MemoryTelemetryParser:
    """Parses free -m output."""

    @staticmethod
    def parse(output: str) -> Dict[str, Any]:
        """Parse memory values in MB."""
        for line in output.splitlines():
            if line.startswith("Mem:"):
                parts = line.split()
                if len(parts) >= 7:
                    total = float(parts[1])
                    used = float(parts[2])
                    free = float(parts[3])
                    available = float(parts[6])
                    pct = round((used / total) * 100.0, 2) if total > 0 else 0.0
                    return {
                        "total_mb": total,
                        "used_mb": used,
                        "free_mb": free,
                        "available_mb": available,
                        "usage_percent": pct,
                    }
        return {"usage_percent": 0.0}


class DiskTelemetryParser:
    """Parses df -h output."""

    @staticmethod
    def parse(output: str) -> List[Dict[str, Any]]:
        """Parse disk partitions and capacities."""
        disks: List[Dict[str, Any]] = []
        lines = output.splitlines()
        if not lines:
            return disks

        for line in lines[1:]:  # Skip header
            parts = line.split()
            if len(parts) >= 6:
                device = parts[0]
                size = parts[1]
                used = parts[2]
                avail = parts[3]
                pct_str = parts[4].replace("%", "")
                mount = parts[5]

                # Exclude system loops
                if device in ("udev", "tmpfs") or mount.startswith("/snap"):
                    continue

                try:
                    disks.append(
                        {
                            "device": device,
                            "size": size,
                            "used": used,
                            "available": avail,
                            "usage_percent": float(pct_str),
                            "mount_point": mount,
                        }
                    )
                except ValueError:
                    pass
        return disks


class NetworkTelemetryParser:
    """Parses /proc/net/dev output."""

    @staticmethod
    def parse(output: str) -> List[Dict[str, Any]]:
        """Parse RX and TX bytes for interfaces."""
        interfaces: List[Dict[str, Any]] = []
        for line in output.splitlines():
            if ":" in line:
                parts = line.split(":")
                name = parts[0].strip()
                stats = parts[1].split()
                if len(stats) >= 9 and name != "lo":
                    try:
                        interfaces.append(
                            {
                                "interface": name,
                                "rx_bytes": int(stats[0]),
                                "tx_bytes": int(stats[8]),
                            }
                        )
                    except ValueError:
                        pass
        return interfaces


class ProcessTelemetryParser:
    """Parses ps command output."""

    @staticmethod
    def parse(output: str) -> List[Dict[str, Any]]:
        """Parse top CPU-consuming process snapshots."""
        processes: List[Dict[str, Any]] = []
        lines = output.splitlines()
        if len(lines) <= 1:
            return processes

        # ps -eo pid,ppid,cmd,%cpu,%mem
        for line in lines[1:]:
            parts = line.split(maxsplit=4)
            if len(parts) >= 5:
                try:
                    processes.append(
                        {
                            "pid": int(parts[0]),
                            "ppid": int(parts[1]),
                            "cpu_percent": float(parts[2]),
                            "mem_percent": float(parts[3]),
                            "command": parts[4].strip(),
                        }
                    )
                except ValueError:
                    pass
        return processes


class ServiceTelemetryParser:
    """Parses active services output."""

    @staticmethod
    def parse(output: str) -> List[Dict[str, Any]]:
        """Parse running system services lists."""
        services: List[Dict[str, Any]] = []
        for line in output.splitlines():
            parts = line.split()
            if len(parts) >= 1:
                name = parts[0].replace(".service", "")
                services.append({"name": name, "state": "running"})
        return services

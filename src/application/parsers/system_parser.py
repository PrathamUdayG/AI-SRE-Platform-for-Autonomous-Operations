"""
-------------------------------------------------------
File:
system_parser.py

Purpose:
Parses Linux host metadata, CPU layout, OS release, and uptime output.

Why this file exists:
Separates string processing and systemd-specific key-value lookup functions from command execution, ensuring static metadata collection is testable.

Responsibilities:
- Parse hostnamectl details.
- Parse uname -a parameters.
- Parse /etc/os-release key-value settings.
- Parse lscpu CPU topology.
- Parse uptime output to uptime seconds.
- Enforce fallback values.

Used By:
- SystemCollector

Depends On:
- src.domain.metrics.system_metrics.SystemMetrics
- src.domain.exceptions.ValidationError
-------------------------------------------------------
"""

from datetime import datetime, timedelta, timezone
from typing import Optional
import structlog

from src.domain.exceptions import ValidationError
from src.domain.metrics.system_metrics import (
    CPUInfo,
    HardwareInfo,
    HostIdentity,
    OperatingSystemInfo,
    SystemMetrics,
    SystemState,
)

logger = structlog.get_logger(__name__)


class SystemParser:
    """
    Why this class exists:
    A utility class containing static methods for parsing host specifications.

    Responsibility:
    Converts hostnamectl, uname, os-release, lscpu, uptime to SystemMetrics.

    Who uses it:
    SystemCollector.
    """

    @staticmethod
    def parse_uptime_to_seconds(uptime_str: str) -> float:
        """
        Parse standard Linux uptime command output to seconds.

        Args:
            uptime_str (str): CLI stdout of uptime.

        Returns:
            float: Number of uptime seconds.
        """
        uptime_str = uptime_str.strip()
        if not uptime_str or "up" not in uptime_str:
            return 0.0

        # Split by comma and truncate at segment containing user/load
        segments = uptime_str.split(",")
        valid_segments = []
        for s in segments:
            s_lower = s.lower()
            if "user" in s_lower or "load" in s_lower:
                break
            valid_segments.append(s)

        reconstructed = ",".join(valid_segments)
        if "up" not in reconstructed:
            return 0.0

        time_part = reconstructed.split("up", 1)[1].strip()

        days = 0
        hours = 0
        minutes = 0

        # 1. Parse days
        if "day" in time_part:
            try:
                day_section, rest = time_part.split("day", 1)
                days = int(day_section.split()[-1])
                time_part = rest.strip().lstrip("s").lstrip(",").strip()
            except Exception:
                pass

        # 2. Parse minutes (e.g. "50 min" or "2 mins")
        if "min" in time_part:
            try:
                min_section = time_part.split("min")[0]
                minutes = int(min_section.split()[-1])
            except Exception:
                pass
        # 3. Parse HH:MM (e.g. "3:15" or "03:15")
        if ":" in time_part:
            try:
                colon_section = time_part.split()[-1]
                if ":" in colon_section:
                    h_str, m_str = colon_section.split(":", 1)
                    hours = int(h_str)
                    minutes = int(m_str)
            except Exception:
                pass
        elif time_part:
            # Fallback check if it's just raw number of minutes or hours
            try:
                minutes = int(time_part.split()[-1])
            except Exception:
                pass

        return float((days * 86400) + (hours * 3600) + (minutes * 60))


    @classmethod
    def parse(
        cls,
        hostnamectl_output: str,
        uname_output: str,
        os_release_output: str,
        lscpu_output: str,
        uptime_output: str,
        timezone_output: str,
        timestamp: datetime,
    ) -> SystemMetrics:
        """
        Parse outputs from static configuration tools to construct SystemMetrics.

        Raises:
            ValidationError: If all outputs are empty/None or fail parsing completely.
        """
        if any(
            x is None
            for x in [
                hostnamectl_output,
                uname_output,
                os_release_output,
                lscpu_output,
                uptime_output,
                timezone_output,
            ]
        ):
            raise ValidationError("Telemetry command outputs cannot be None.")

        # 1. Parse /etc/os-release properties
        os_props = {}
        for line in os_release_output.splitlines():
            line = line.strip()
            if not line or "=" not in line:
                continue
            key, val = line.split("=", 1)
            os_props[key.strip()] = val.strip().strip('"').strip("'")

        # 2. Parse hostnamectl key-values
        h_props = {}
        for line in hostnamectl_output.splitlines():
            line = line.strip()
            if not line or ":" not in line:
                continue
            key, val = line.split(":", 1)
            h_props[key.strip().lower()] = val.strip()

        # 3. Parse lscpu key-values
        cpu_props = {}
        for line in lscpu_output.splitlines():
            line = line.strip()
            if not line or ":" not in line:
                continue
            key, val = line.split(":", 1)
            cpu_props[key.strip().lower()] = val.strip()

        # 4. Extract Host Identity
        hostname = (
            h_props.get("static hostname")
            or h_props.get("transient hostname")
            or "unknown"
        )
        # If hostname is still unknown, attempt fallback to hostnamectl or uname
        if hostname == "unknown" and uname_output:
            uname_parts = uname_output.split()
            if len(uname_parts) > 1:
                hostname = uname_parts[1]

        machine_id = h_props.get("machine id")
        boot_id = h_props.get("boot id")

        # 5. Extract Operating System Info
        dist_name = os_props.get("NAME") or os_props.get("ID") or "Linux"
        dist_version = os_props.get("VERSION_ID") or os_props.get("VERSION") or "unknown"
        pretty_name = os_props.get("PRETTY_NAME") or dist_name

        kernel_release = "unknown"
        kernel_version = "unknown"
        architecture = h_props.get("architecture") or "unknown"

        if uname_output:
            uname_parts = uname_output.split()
            if len(uname_parts) >= 3:
                kernel_release = uname_parts[2]
            if len(uname_parts) >= 4:
                kernel_version = " ".join(uname_parts[3:])
            if architecture == "unknown" and len(uname_parts) >= 12:
                # Fallback to standard uname architecture pos
                architecture = uname_parts[-2]

        if kernel_version == "unknown":
            kernel_version = h_props.get("kernel") or "unknown"

        # 6. Extract CPU Info
        cpu_model = cpu_props.get("model name") or "unknown"
        vendor = cpu_props.get("vendor id") or "unknown"
        
        logical_cpu_count = 0
        try:
            logical_cpu_count = int(cpu_props.get("cpu(s)", "0"))
        except ValueError:
            pass

        physical_cpu_count = None
        if "socket(s)" in cpu_props:
            try:
                physical_cpu_count = int(cpu_props.get("socket(s)", "0"))
            except ValueError:
                pass

        threads_per_core = 1
        if "thread(s) per core" in cpu_props:
            try:
                threads_per_core = int(cpu_props.get("thread(s) per core", "1"))
            except ValueError:
                pass

        cores_per_socket = logical_cpu_count
        if "core(s) per socket" in cpu_props:
            try:
                cores_per_socket = int(cpu_props.get("core(s) per socket", "1"))
            except ValueError:
                pass

        cpu_mhz = None
        if "cpu mhz" in cpu_props:
            try:
                cpu_mhz = float(cpu_props.get("cpu mhz", "0"))
            except ValueError:
                pass

        # 7. Extract Hardware / Virtualization
        virt_type = h_props.get("virtualization") or cpu_props.get("virtualization", "none")
        hypervisor_vendor = cpu_props.get("hypervisor vendor")

        # 8. System State / Uptime
        uptime_seconds = cls.parse_uptime_to_seconds(uptime_output)
        boot_time = None
        if uptime_seconds > 0:
            boot_time = timestamp - timedelta(seconds=uptime_seconds)

        # 9. Timezone & Hostname mode
        tz_name = timezone_output.strip() or "UTC"
        
        # Check transient hostname diffs to resolve operating mode
        static_hn = h_props.get("static hostname")
        transient_hn = h_props.get("transient hostname")
        if transient_hn and static_hn and transient_hn != static_hn:
            operating_mode = "transient"
        else:
            operating_mode = "static"

        # Safe parsing validator: raise error if everything failed to initialize
        if (
            hostname == "unknown"
            and dist_name == "Linux"
            and logical_cpu_count == 0
            and uptime_seconds == 0.0
        ):
            raise ValidationError("Could not parse any valid host system information.")

        return SystemMetrics(
            host_identity=HostIdentity(
                hostname=hostname,
                machine_id=machine_id,
                boot_id=boot_id,
            ),
            os_info=OperatingSystemInfo(
                distribution_name=dist_name,
                distribution_version=dist_version,
                pretty_name=pretty_name,
                kernel_version=kernel_version,
                kernel_release=kernel_release,
                architecture=architecture,
            ),
            cpu_info=CPUInfo(
                cpu_model=cpu_model,
                vendor=vendor,
                logical_cpu_count=logical_cpu_count,
                physical_cpu_count=physical_cpu_count,
                threads_per_core=threads_per_core,
                cores_per_socket=cores_per_socket,
                cpu_mhz=cpu_mhz,
            ),
            hardware=HardwareInfo(
                virtualization_type=virt_type,
                hypervisor_vendor=hypervisor_vendor,
            ),
            system_state=SystemState(
                system_uptime=uptime_seconds,
                boot_time=boot_time,
            ),
            timezone=tz_name,
            operating_mode=operating_mode,
            timestamp=timestamp,
        )

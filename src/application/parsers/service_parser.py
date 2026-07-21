"""
-------------------------------------------------------
File:
service_parser.py

Purpose:
Parses Linux systemctl list-units output and show properties blocks.

Why this file exists:
Isolates string manipulations and systemctl property tokenization away from OS execution context, keeping parser logic clean and fully testable.

Responsibilities:
- Parse systemctl list-units services table layout.
- Parse key=value properties printed by systemctl show.
- Enforce default values for missing details.
- Validate results and return ServiceMetrics.

Used By:
- ServiceCollector

Depends On:
- src.domain.metrics.service_metrics.ServiceMetrics
- src.domain.exceptions.ValidationError
-------------------------------------------------------
"""

from datetime import datetime
from typing import Optional
import structlog

from src.domain.exceptions import ValidationError
from src.domain.metrics.service_metrics import ServiceMetrics, ServiceUnit

logger = structlog.get_logger(__name__)


class ServiceParser:
    """
    Why this class exists:
    A utility class containing static methods for parsing systemd service status.

    Responsibility:
    Translates list-units stdout and show details into ServiceMetrics.

    Who uses it:
    ServiceCollector.
    """

    @staticmethod
    def parse(
        list_units_output: str,
        show_output: Optional[str],
        timestamp: datetime,
    ) -> ServiceMetrics:
        """
        Parse outputs from systemctl commands to return a ServiceMetrics model.

        Args:
            list_units_output (str): Stdout string of systemctl list-units.
            show_output (Optional[str]): Optional stdout string of systemctl show.
            timestamp (datetime): UTC collection timestamp.

        Returns:
            ServiceMetrics: Structured, type-validated service metrics.

        Raises:
            ValidationError: If list_units_output is None or yields zero services.
        """
        if list_units_output is None:
            raise ValidationError("list_units_output cannot be None.")

        # 1. Parse systemctl list-units
        services_map = {}
        for line in list_units_output.splitlines():
            line = line.strip()
            if not line:
                continue
            parts = line.split()
            if len(parts) < 4:
                continue

            # parts[0]: unit name (e.g. cron.service)
            # parts[1]: load state (e.g. loaded)
            # parts[2]: active state (e.g. active)
            # parts[3]: sub state (e.g. running)
            # parts[4:]: description (e.g. Regular background program...)
            name = parts[0]
            if not name.endswith(".service"):
                continue

            load_state = parts[1]
            active_state = parts[2]
            sub_state = parts[3]
            description = " ".join(parts[4:])

            services_map[name] = {
                "name": name,
                "description": description,
                "load_state": load_state,
                "active_state": active_state,
                "sub_state": sub_state,
                "unit_file_state": None,
                "main_pid": None,
                "service_type": None,
                "restart_policy": None,
                "fragment_path": None,
                "is_enabled": False,
            }

        # 2. Parse systemctl show
        if show_output:
            show_data = {}
            current_unit = None
            current_props = {}

            for line in show_output.splitlines():
                line = line.strip()
                if not line or "=" not in line:
                    continue
                key, value = line.split("=", 1)
                if key == "Id":
                    if current_unit:
                        show_data[current_unit] = current_props
                    current_unit = value
                    current_props = {}
                elif current_unit:
                    current_props[key] = value

            if current_unit:
                show_data[current_unit] = current_props

            # Enrich from show details
            for name, service in services_map.items():
                props = show_data.get(name, {})
                if props:
                    ufs = props.get("UnitFileState")
                    if ufs:
                        service["unit_file_state"] = ufs
                        service["is_enabled"] = (ufs == "enabled")

                    mpid = props.get("MainPID")
                    if mpid:
                        try:
                            pid_val = int(mpid)
                            service["main_pid"] = pid_val if pid_val > 0 else None
                        except ValueError:
                            pass

                    stype = props.get("Type")
                    if stype:
                        service["service_type"] = stype

                    restart = props.get("Restart")
                    if restart:
                        service["restart_policy"] = restart

                    frag = props.get("FragmentPath")
                    if frag:
                        service["fragment_path"] = frag

        # Convert map to ServiceUnit models
        units = []
        for s in services_map.values():
            units.append(ServiceUnit(**s))

        # Check if list is empty
        if not units:
            raise ValidationError("No systemd services parsed from list-units output.")

        return ServiceMetrics(
            services=units,
            timestamp=timestamp,
        )

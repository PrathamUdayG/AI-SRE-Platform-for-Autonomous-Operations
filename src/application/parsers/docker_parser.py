"""
-------------------------------------------------------
File:
docker_parser.py

Purpose:
Parses Docker commands output (ps, inspect, stats, network, volume) into normalized domain models.

Why this file exists:
Decouples raw Docker text/json parsing from command execution, ensuring testability.

Responsibilities:
- Parse docker ps --no-trunc output to extract running IDs.
- Deserialize docker inspect JSON output for containers configuration.
- Parse docker stats --no-stream --no-trunc resources columns.
- Parse docker network ls topology.
- Parse docker volume ls storage definitions.
- Convert memory/network values with various suffix units to raw integer bytes.

Used By:
- DockerCollector

Depends On:
- src.domain.metrics.docker_metrics.DockerMetrics
- src.domain.exceptions.ValidationError
-------------------------------------------------------
"""

import json
import re
from datetime import datetime, timezone
from typing import Dict, List, Optional
import structlog

from src.domain.exceptions import ValidationError
from src.domain.metrics.docker_metrics import (
    ContainerMetadata,
    ContainerMount,
    ContainerStats,
    DockerMetrics,
    DockerNetwork,
    DockerVolume,
)

logger = structlog.get_logger(__name__)


class DockerParser:
    """
    Why this class exists:
    A utility class containing static methods for parsing Docker telemetries.

    Responsibility:
    Converts docker commands output to structured DockerMetrics.

    Who uses it:
    DockerCollector.
    """

    @staticmethod
    def parse_size_in_bytes(size_str: str) -> int:
        """
        Parse size representations (e.g. 15.42MiB, 1.2GB, 0B) into raw integer bytes.

        Args:
            size_str (str): Suffix size string.

        Returns:
            int: Size converted to bytes.
        """
        size_str = size_str.strip().upper()
        if not size_str or size_str == "0B" or size_str == "0":
            return 0

        # Remove trailing slash or other characters that could be left from spacing
        size_str = size_str.split("/")[0].strip()

        match = re.match(r"^([0-9.]+)\s*([A-Z]*)$", size_str)
        if not match:
            return 0

        try:
            val = float(match.group(1))
        except ValueError:
            return 0

        unit = match.group(2)

        multipliers = {
            "": 1,
            "B": 1,
            "KB": 1000,
            "MB": 1000**2,
            "GB": 1000**3,
            "TB": 1000**4,
            "KIB": 1024,
            "MIB": 1024**2,
            "GIB": 1024**3,
            "TIB": 1024**4,
            "K": 1024,
            "M": 1024**2,
            "G": 1024**3,
        }
        mult = multipliers.get(unit, 1)
        return int(val * mult)

    @classmethod
    def parse_container_stats(cls, stats_output: str) -> List[ContainerStats]:
        """
        Parse raw output of docker stats --no-stream --no-trunc.

        Args:
            stats_output (str): Stdout of stats command.

        Returns:
            List[ContainerStats]: List of resource consumption stats.
        """
        stats_list: List[ContainerStats] = []
        lines = stats_output.strip().splitlines()
        if len(lines) <= 1:
            return stats_list

        for line in lines[1:]:  # skip header
            parts = line.split()
            if len(parts) < 14:
                # Malformed or different format line, skip defensively
                continue

            try:
                cid = parts[0]
                name = parts[1]
                cpu_pct = float(parts[2].rstrip("%"))
                mem_usage = cls.parse_size_in_bytes(parts[3])
                # parts[4] is "/"
                mem_limit = cls.parse_size_in_bytes(parts[5])
                mem_pct = float(parts[6].rstrip("%"))
                net_rx = cls.parse_size_in_bytes(parts[7])
                # parts[8] is "/"
                net_tx = cls.parse_size_in_bytes(parts[9])
                blk_read = cls.parse_size_in_bytes(parts[10])
                # parts[11] is "/"
                blk_write = cls.parse_size_in_bytes(parts[12])
                pids = int(parts[13])

                stats_list.append(
                    ContainerStats(
                        container_id=cid,
                        name=name,
                        cpu_percentage=cpu_pct,
                        memory_usage_bytes=mem_usage,
                        memory_limit_bytes=mem_limit,
                        memory_percentage=mem_pct,
                        network_rx_bytes=net_rx,
                        network_tx_bytes=net_tx,
                        block_read_bytes=blk_read,
                        block_write_bytes=blk_write,
                        pids_count=pids,
                    )
                )
            except Exception as e:
                logger.debug("Failed parsing stats line", error=str(e), line=line)
                continue

        return stats_list

    @classmethod
    def parse_container_metadata(cls, inspect_output: str) -> List[ContainerMetadata]:
        """
        Parse docker inspect JSON list of containers.

        Args:
            inspect_output (str): JSON list string from inspect.

        Returns:
            List[ContainerMetadata]: Container configuration models.
        """
        metadata_list: List[ContainerMetadata] = []
        if not inspect_output.strip():
            return metadata_list

        try:
            inspect_data = json.loads(inspect_output)
            if not isinstance(inspect_data, list):
                return metadata_list
        except Exception as e:
            logger.debug("Failed deserializing inspect output", error=str(e))
            return metadata_list

        for c in inspect_data:
            try:
                cid = c.get("Id", "")
                name = c.get("Name", "").lstrip("/")
                
                # Image attributes
                image = c.get("Config", {}).get("Image", "")
                image_id = c.get("Image", "")

                # Creation time parsing
                created_str = c.get("Created", "")
                created_time = None
                if created_str:
                    try:
                        # Standard docker created timestamp: 2026-07-21T14:29:48.123456789Z
                        # Python's fromisoformat requires slicing decimal fractional seconds
                        clean_created = created_str.replace("Z", "+00:00")
                        if "." in clean_created:
                            left, right = clean_created.split(".", 1)
                            # Keep at most 6 digits for microseconds + tz offset
                            tz_offset = ""
                            if "+" in right:
                                right, tz_offset = right.split("+", 1)
                                tz_offset = "+" + tz_offset
                            elif "-" in right:
                                right, tz_offset = right.split("-", 1)
                                tz_offset = "-" + tz_offset
                            right = right[:6]
                            clean_created = f"{left}.{right}{tz_offset}"
                        created_time = datetime.fromisoformat(clean_created)
                    except ValueError:
                        pass
                if not created_time:
                    created_time = datetime.now(timezone.utc)

                # State and status
                state = c.get("State", {}).get("Status", "unknown")
                status = c.get("State", {}).get("FinishedAt", "")
                # Fallback to status description if available
                # Wait, status description is not standard in inspect, so let's default to State.Status
                status_desc = f"status: {state}"

                restart_count = c.get("State", {}).get("RestartCount", 0)
                pid = c.get("State", {}).get("Pid", None)

                # Commands
                cmd_parts = c.get("Config", {}).get("Cmd", [])
                command = " ".join(cmd_parts) if isinstance(cmd_parts, list) else str(cmd_parts)

                # Labels
                labels = c.get("Config", {}).get("Labels", {}) or {}

                # Network details
                network_mode = c.get("HostConfig", {}).get("NetworkMode", "default")

                # Mounts
                mounts_data = c.get("Mounts", []) or []
                mounts = []
                for m in mounts_data:
                    mounts.append(
                        ContainerMount(
                            source=m.get("Source", ""),
                            destination=m.get("Destination", ""),
                            mode=m.get("Mode", ""),
                            rw=m.get("RW", True),
                            propagation=m.get("Propagation", ""),
                        )
                    )

                metadata_list.append(
                    ContainerMetadata(
                        container_id=cid,
                        name=name,
                        image=image,
                        image_id=image_id,
                        created_time=created_time,
                        state=state,
                        status=status_desc,
                        restart_count=restart_count,
                        pid=pid,
                        command=command,
                        labels=labels,
                        mounts=mounts,
                        network_mode=network_mode,
                    )
                )
            except Exception as e:
                logger.debug("Failed parsing inspect container entry", error=str(e))
                continue

        return metadata_list

    @classmethod
    def parse_networks(cls, network_output: str) -> List[DockerNetwork]:
        """
        Parse raw output of docker network ls.
        """
        networks = []
        lines = network_output.strip().splitlines()
        if len(lines) <= 1:
            return networks

        for line in lines[1:]:
            parts = line.split()
            if len(parts) >= 4:
                networks.append(
                    DockerNetwork(
                        network_id=parts[0],
                        name=parts[1],
                        driver=parts[2],
                        scope=parts[3],
                    )
                )
        return networks

    @classmethod
    def parse_volumes(cls, volume_output: str) -> List[DockerVolume]:
        """
        Parse raw output of docker volume ls.
        """
        volumes = []
        lines = volume_output.strip().splitlines()
        if len(lines) <= 1:
            return volumes

        for line in lines[1:]:
            parts = line.split()
            if len(parts) >= 2:
                volumes.append(
                    DockerVolume(
                        driver=parts[0],
                        name=parts[1],
                        mountpoint=None,  # volume ls does not expose mountpoint
                    )
                )
        return volumes

    @classmethod
    def parse(
        cls,
        inspect_output: str,
        stats_output: str,
        network_output: str,
        volume_output: str,
        timestamp: datetime,
    ) -> DockerMetrics:
        """
        Parse all Docker CLI command outputs into unified DockerMetrics.

        Raises:
            ValidationError: If all outputs are None.
        """
        if any(
            x is None
            for x in [inspect_output, stats_output, network_output, volume_output]
        ):
            raise ValidationError("Telemetry command outputs cannot be None.")

        containers = cls.parse_container_metadata(inspect_output)
        stats = cls.parse_container_stats(stats_output)
        networks = cls.parse_networks(network_output)
        volumes = cls.parse_volumes(volume_output)

        return DockerMetrics(
            containers=containers,
            stats=stats,
            networks=networks,
            volumes=volumes,
            timestamp=timestamp,
        )

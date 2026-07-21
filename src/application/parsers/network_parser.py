"""
-------------------------------------------------------
File:
network_parser.py

Purpose:
Parses Linux network device files, address show mappings, routes, and socket state text.

Why this file exists:
Keeps complex token parsing, hex IP address decode routines, and regular expression lookups separate from command executions, keeping the platform clean and testable.

Responsibilities:
- Parse /proc/net/dev network interfaces and counters.
- Parse ip -o addr show IPv4 settings, CIDR, broadcast and scopes.
- Parse ip route show destinations, gateways, dev, protocols, metrics.
- Parse hex IP and ports in /proc/net/tcp and /proc/net/udp.

Used By:
- NetworkCollector

Depends On:
- src.domain.metrics.network_metrics.NetworkMetrics
- src.domain.exceptions.ValidationError
-------------------------------------------------------
"""

from datetime import datetime
import structlog

from src.domain.exceptions import ValidationError
from src.domain.metrics.network_metrics import (
    InterfaceConfiguration,
    NetworkInterfaceMetrics,
    NetworkMetrics,
    RouteMetrics,
    TCPConnectionMetrics,
    UDPConnectionMetrics,
)

logger = structlog.get_logger(__name__)


class NetworkParser:
    """
    Why this class exists:
    A utility class containing static methods for parsing network telemetry files.

    Responsibility:
    Converts network system files stdout to CPUMetrics or NetworkMetrics.

    Who uses it:
    NetworkCollector.
    """

    @staticmethod
    def parse_hex_ipv4(hex_str: str) -> str:
        """
        Convert little-endian hex representation of an IPv4 address to standard dotted format.

        Args:
            hex_str (str): 8-character hex string (e.g. '0100007F' for '127.0.0.1')

        Returns:
            str: Dotted IP representation or 'unknown' on error.
        """
        if len(hex_str) != 8:
            return "unknown"
        try:
            val = int(hex_str, 16)
            # Little endian decode:
            b1 = val & 0xFF
            b2 = (val >> 8) & 0xFF
            b3 = (val >> 16) & 0xFF
            b4 = (val >> 24) & 0xFF
            return f"{b1}.{b2}.{b3}.{b4}"
        except Exception:
            logger.debug("Failed to decode hex IPv4 address", hex=hex_str)
            return "unknown"

    @staticmethod
    def parse_hex_port(hex_str: str) -> int:
        """
        Convert hex representation of a port number to decimal integer.

        Args:
            hex_str (str): Hex string (e.g. '0050' for 80)

        Returns:
            int: Decoded port or 0 on error.
        """
        try:
            return int(hex_str, 16)
        except Exception:
            logger.debug("Failed to decode hex port number", hex=hex_str)
            return 0

    @classmethod
    def parse(
        cls,
        proc_net_dev_output: str,
        ip_addr_output: str,
        ip_route_output: str,
        proc_tcp_output: str,
        proc_udp_output: str,
        timestamp: datetime,
    ) -> NetworkMetrics:
        """
        Parse all stdout outputs together into a NetworkMetrics model.

        Raises:
            ValidationError: If all of the metrics outputs fail parsing.
        """
        if any(out is None for out in [proc_net_dev_output, ip_addr_output, ip_route_output, proc_tcp_output, proc_udp_output]):
            raise ValidationError("Stdout command inputs cannot be None.")

        # 1. Parse /proc/net/dev
        interfaces = []
        for line in proc_net_dev_output.splitlines():
            line = line.strip()
            if not line or ":" not in line:
                continue
            parts = line.split(":", 1)
            if len(parts) < 2:
                continue
            iface_name = parts[0].strip()
            num_parts = parts[1].split()
            if len(num_parts) < 16:
                continue
            try:
                interfaces.append(
                    NetworkInterfaceMetrics(
                        interface_name=iface_name,
                        rx_bytes=int(num_parts[0]),
                        rx_packets=int(num_parts[1]),
                        rx_errors=int(num_parts[2]),
                        rx_drops=int(num_parts[3]),
                        rx_fifo_errors=int(num_parts[4]),
                        rx_frame_errors=int(num_parts[5]),
                        rx_compressed=int(num_parts[6]),
                        rx_multicast=int(num_parts[7]),
                        tx_bytes=int(num_parts[8]),
                        tx_packets=int(num_parts[9]),
                        tx_errors=int(num_parts[10]),
                        tx_drops=int(num_parts[11]),
                        tx_fifo_errors=int(num_parts[12]),
                        collisions=int(num_parts[13]),
                        carrier_errors=int(num_parts[14]),
                        tx_compressed=int(num_parts[15]),
                    )
                )
            except ValueError:
                continue

        # 2. Parse ip -o addr show
        configurations = []
        for line in ip_addr_output.splitlines():
            line = line.strip()
            if not line or " inet " not in line:
                continue
            parts = line.split()
            if len(parts) < 4:
                continue
            
            iface_name = parts[1]
            try:
                inet_idx = parts.index("inet")
                ip_prefix = parts[inet_idx + 1]
                if "/" in ip_prefix:
                    ip_addr, prefix_len_str = ip_prefix.split("/", 1)
                    prefix_length = int(prefix_len_str)
                else:
                    ip_addr = ip_prefix
                    prefix_length = 32
            except (ValueError, IndexError):
                continue

            broadcast_address = None
            if "brd" in parts:
                try:
                    brd_idx = parts.index("brd")
                    if brd_idx + 1 < len(parts):
                        broadcast_address = parts[brd_idx + 1]
                except ValueError:
                    pass

            scope = "unknown"
            if "scope" in parts:
                try:
                    scope_idx = parts.index("scope")
                    if scope_idx + 1 < len(parts):
                        scope = parts[scope_idx + 1]
                except ValueError:
                    pass

            configurations.append(
                InterfaceConfiguration(
                    interface_name=iface_name,
                    ip_address=ip_addr,
                    prefix_length=prefix_length,
                    broadcast_address=broadcast_address,
                    scope=scope,
                )
            )

        # 3. Parse ip route show
        routes = []
        for line in ip_route_output.splitlines():
            line = line.strip()
            if not line:
                continue
            parts = line.split()
            if len(parts) < 2:
                continue
            destination = parts[0]

            gateway = None
            if "via" in parts:
                try:
                    via_idx = parts.index("via")
                    if via_idx + 1 < len(parts):
                        gateway = parts[via_idx + 1]
                except ValueError:
                    pass

            interface = "unknown"
            if "dev" in parts:
                try:
                    dev_idx = parts.index("dev")
                    if dev_idx + 1 < len(parts):
                        interface = parts[dev_idx + 1]
                except ValueError:
                    pass

            protocol = None
            if "proto" in parts:
                try:
                    proto_idx = parts.index("proto")
                    if proto_idx + 1 < len(parts):
                        protocol = parts[proto_idx + 1]
                except ValueError:
                    pass

            metric = None
            if "metric" in parts:
                try:
                    metric_idx = parts.index("metric")
                    if metric_idx + 1 < len(parts):
                        metric = int(parts[metric_idx + 1])
                except ValueError:
                    pass

            routes.append(
                RouteMetrics(
                    destination=destination,
                    gateway=gateway,
                    interface=interface,
                    protocol=protocol,
                    metric=metric,
                )
            )

        # 4. Parse /proc/net/tcp
        tcp_connections = []
        for line in proc_tcp_output.splitlines():
            line = line.strip()
            if not line or line.startswith("sl"):
                continue
            parts = line.split()
            if len(parts) < 4:
                continue
            if ":" not in parts[1] or ":" not in parts[2]:
                continue

            local_ip_hex, local_port_hex = parts[1].split(":", 1)
            remote_ip_hex, remote_port_hex = parts[2].split(":", 1)
            state_hex = parts[3]

            tcp_connections.append(
                TCPConnectionMetrics(
                    local_address=cls.parse_hex_ipv4(local_ip_hex),
                    local_port=cls.parse_hex_port(local_port_hex),
                    remote_address=cls.parse_hex_ipv4(remote_ip_hex),
                    remote_port=cls.parse_hex_port(remote_port_hex),
                    connection_state=state_hex,
                )
            )

        # 5. Parse /proc/net/udp
        udp_connections = []
        for line in proc_udp_output.splitlines():
            line = line.strip()
            if not line or line.startswith("sl"):
                continue
            parts = line.split()
            if len(parts) < 2:
                continue
            if ":" not in parts[1]:
                continue

            local_ip_hex, local_port_hex = parts[1].split(":", 1)
            udp_connections.append(
                UDPConnectionMetrics(
                    local_address=cls.parse_hex_ipv4(local_ip_hex),
                    local_port=cls.parse_hex_port(local_port_hex),
                )
            )

        # Raise error if everything parsed empty
        if not interfaces and not configurations and not routes and not tcp_connections and not udp_connections:
            raise ValidationError("Could not parse any network metrics from any output files.")

        return NetworkMetrics(
            interfaces=interfaces,
            configurations=configurations,
            routes=routes,
            tcp_connections=tcp_connections,
            udp_connections=udp_connections,
            timestamp=timestamp,
        )

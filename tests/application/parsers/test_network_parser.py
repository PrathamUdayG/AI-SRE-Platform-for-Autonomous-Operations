"""
-------------------------------------------------------
File:
test_network_parser.py

Purpose:
Unit tests for the NetworkParser in the Application Layer.

Why this file exists:
Verifies that interfaces, configs, routes, and socket connections are parsed and converted (hex decoding) correctly, and invalid structures raise ValidationError.

Responsibilities:
- Verify normal parsing and IP/port conversions.
- Verify invalid hex entries.
- Verify missing components.
- Verify ValidationError triggers.

Used By:
- pytest runner

Depends On:
- src.application.parsers.network_parser
- src.domain.exceptions.ValidationError
-------------------------------------------------------
"""

from datetime import datetime, timezone
import pytest

from src.application.parsers.network_parser import NetworkParser
from src.domain.exceptions import ValidationError


def test_parse_normal_network_info():
    """Verify that valid /proc/net/dev, ip addr, ip route, /proc/net/tcp/udp parse successfully."""
    dev_data = """
Inter-|   Receive                                                |  Transmit
 face |bytes    packets errs drop fifo frame compressed multicast|bytes    packets errs drop fifo colls carrier compressed
    lo: 100 1 0 0 0 0 0 0 100 1 0 0 0 0 0 0
  eth0: 200 2 1 2 0 0 0 0 300 3 0 0 0 0 0 0
    """
    addr_data = """
1: lo    inet 127.0.0.1/8 scope host lo\\
2: eth0    inet 192.168.1.100/24 brd 192.168.1.255 scope global eth0\\
    """
    route_data = """
default via 192.168.1.1 dev eth0 proto dhcp metric 100
192.168.1.0/24 dev eth0 proto kernel scope link src 192.168.1.100 metric 200
    """
    tcp_data = """
  sl  local_address rem_address   st tx_queue rx_queue tr tm->when retrnsmt   uid  timeout inode
   0: 0100007F:0050 00000000:0000 0A 00000000:00000000 00:00000000 00000000  1000        0 12345 1
   1: 0100007F:1F90 0200A8C0:0050 01 00000000:00000000 00:00000000 00000000  1000        0 12346 1
    """
    udp_data = """
  sl  local_address rem_address   st tx_queue rx_queue tr tm->when retrnsmt   uid  timeout inode
   0: 0100007F:0035 00000000:0000 07 00000000:00000000 00:00000000 00000000  1000        0 12347 1
    """
    now = datetime.now(timezone.utc)

    metrics = NetworkParser.parse(
        proc_net_dev_output=dev_data,
        ip_addr_output=addr_data,
        ip_route_output=route_data,
        proc_tcp_output=tcp_data,
        proc_udp_output=udp_data,
        timestamp=now
    )

    # Verify Interface Metrics
    assert len(metrics.interfaces) == 2
    assert metrics.interfaces[0].interface_name == "lo"
    assert metrics.interfaces[0].rx_bytes == 100
    assert metrics.interfaces[1].interface_name == "eth0"
    assert metrics.interfaces[1].rx_bytes == 200
    assert metrics.interfaces[1].rx_errors == 1

    # Verify IP Configurations
    assert len(metrics.configurations) == 2
    assert metrics.configurations[0].interface_name == "lo"
    assert metrics.configurations[0].ip_address == "127.0.0.1"
    assert metrics.configurations[0].prefix_length == 8
    assert metrics.configurations[1].interface_name == "eth0"
    assert metrics.configurations[1].ip_address == "192.168.1.100"
    assert metrics.configurations[1].prefix_length == 24
    assert metrics.configurations[1].broadcast_address == "192.168.1.255"
    assert metrics.configurations[1].scope == "global"

    # Verify Routes
    assert len(metrics.routes) == 2
    assert metrics.routes[0].destination == "default"
    assert metrics.routes[0].gateway == "192.168.1.1"
    assert metrics.routes[0].interface == "eth0"
    assert metrics.routes[0].protocol == "dhcp"
    assert metrics.routes[0].metric == 100

    # Verify TCP connections
    assert len(metrics.tcp_connections) == 2
    assert metrics.tcp_connections[0].local_address == "127.0.0.1"
    assert metrics.tcp_connections[0].local_port == 80
    assert metrics.tcp_connections[0].remote_address == "0.0.0.0"
    assert metrics.tcp_connections[0].remote_port == 0
    assert metrics.tcp_connections[0].connection_state == "0A"

    assert metrics.tcp_connections[1].local_address == "127.0.0.1"
    assert metrics.tcp_connections[1].local_port == 8080
    assert metrics.tcp_connections[1].remote_address == "192.168.0.2"
    assert metrics.tcp_connections[1].remote_port == 80
    assert metrics.tcp_connections[1].connection_state == "01"

    # Verify UDP connections
    assert len(metrics.udp_connections) == 1
    assert metrics.udp_connections[0].local_address == "127.0.0.1"
    assert metrics.udp_connections[0].local_port == 53


def test_parse_hex_helpers():
    """Verify individual static address/port translation methods."""
    assert NetworkParser.parse_hex_ipv4("0100007F") == "127.0.0.1"
    assert NetworkParser.parse_hex_ipv4("badhex") == "unknown"
    assert NetworkParser.parse_hex_ipv4("") == "unknown"
    assert NetworkParser.parse_hex_port("0050") == 80
    assert NetworkParser.parse_hex_port("invalid") == 0


def test_parse_empty_input_raises_validation_error():
    """Verify that empty inputs raise ValidationError."""
    now = datetime.now(timezone.utc)
    with pytest.raises(ValidationError):
        NetworkParser.parse("", "", "", "", "", now)

    with pytest.raises(ValidationError):
        NetworkParser.parse(None, "", "", "", "", now)

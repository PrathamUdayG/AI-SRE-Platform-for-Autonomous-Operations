"""
-------------------------------------------------------
File:
network_metrics.py

Purpose:
Domain model representing network interface usage, address config, routing, and sockets.

Why this file exists:
Provides a strongly typed, OS-agnostic representation of network telemetry data collected from Linux network systems.

Responsibilities:
- Encapsulate network metrics, routes, configurations, and connections.

Used By:
- NetworkParser
- NetworkCollector

Notes:
This file belongs to the Domain Layer as it defines a core telemetry data structure.
-------------------------------------------------------
"""

from datetime import datetime
from typing import List, Optional
from pydantic import BaseModel, Field


class NetworkInterfaceMetrics(BaseModel):
    """
    Why this class exists:
    Encapsulates raw byte and packet counters for a specific network interface.
    """

    interface_name: str = Field(description="Name of the interface (e.g. eth0)")
    rx_bytes: int = Field(description="Bytes received")
    rx_packets: int = Field(description="Packets received")
    rx_errors: int = Field(description="Receive errors")
    rx_drops: int = Field(description="Receive packets dropped")
    rx_fifo_errors: int = Field(description="Receive FIFO buffer overruns")
    rx_frame_errors: int = Field(description="Receive packet framing errors")
    rx_compressed: int = Field(description="Received compressed packets")
    rx_multicast: int = Field(description="Received multicast packets")

    tx_bytes: int = Field(description="Bytes transmitted")
    tx_packets: int = Field(description="Packets transmitted")
    tx_errors: int = Field(description="Transmit errors")
    tx_drops: int = Field(description="Transmit packets dropped")
    tx_fifo_errors: int = Field(description="Transmit FIFO buffer overruns")
    collisions: int = Field(description="Packet collisions")
    carrier_errors: int = Field(description="Carrier losses during transmit")
    tx_compressed: int = Field(description="Transmitted compressed packets")


class InterfaceConfiguration(BaseModel):
    """
    Why this class exists:
    Encapsulates IP configuration address details for an interface.
    """

    interface_name: str = Field(description="Name of the interface")
    ip_address: str = Field(description="Configured IPv4 address")
    prefix_length: int = Field(description="CIDR prefix length (e.g. 24)")
    broadcast_address: Optional[str] = Field(None, description="Broadcast address")
    scope: str = Field(description="Address scope (e.g. global, host, link)")


class RouteMetrics(BaseModel):
    """
    Why this class exists:
    Encapsulates active network routing table entries.
    """

    destination: str = Field(description="Route destination IP or network")
    gateway: Optional[str] = Field(None, description="Route gateway IP")
    interface: str = Field(description="Interface used for routing")
    protocol: Optional[str] = Field(None, description="Routing protocol (e.g. dhcp, static)")
    metric: Optional[int] = Field(None, description="Route metric score value")


class TCPConnectionMetrics(BaseModel):
    """
    Why this class exists:
    Encapsulates a single active TCP socket state.
    """

    local_address: str = Field(description="Local IP address")
    local_port: int = Field(description="Local socket port")
    remote_address: str = Field(description="Remote IP address")
    remote_port: int = Field(description="Remote socket port")
    connection_state: str = Field(description="Raw hex connection state code")


class UDPConnectionMetrics(BaseModel):
    """
    Why this class exists:
    Encapsulates a single open UDP socket.
    """

    local_address: str = Field(description="Local IP address")
    local_port: int = Field(description="Local socket port")


class NetworkMetrics(BaseModel):
    """
    Why this class exists:
    Main container model for all network telemetry statistics.
    """

    interfaces: List[NetworkInterfaceMetrics] = Field(
        default_factory=list, description="Interface stats"
    )
    configurations: List[InterfaceConfiguration] = Field(
        default_factory=list, description="IP configurations"
    )
    routes: List[RouteMetrics] = Field(
        default_factory=list, description="IP routes"
    )
    tcp_connections: List[TCPConnectionMetrics] = Field(
        default_factory=list, description="TCP socket connections"
    )
    udp_connections: List[UDPConnectionMetrics] = Field(
        default_factory=list, description="UDP socket connections"
    )
    timestamp: datetime = Field(description="UTC timestamp of when the metrics were captured")

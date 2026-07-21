"""
-------------------------------------------------------
File:
test_docker_parser.py

Purpose:
Unit tests for the DockerParser in the Application Layer.

Why this file exists:
Verifies that various Docker CLI commands outputs (inspect JSON, stats, network ls, volume ls) are parsed correctly.

Responsibilities:
- Verify parsing of size units to bytes.
- Verify container inspect JSON deserialization and metadata mapping.
- Verify docker stats parse logic and resource mappings.
- Verify docker network ls and volume ls parse logic.

Used By:
- pytest runner

Depends On:
- src.application.parsers.docker_parser
-------------------------------------------------------
"""

from datetime import datetime, timezone
import pytest

from src.application.parsers.docker_parser import DockerParser


def test_parse_size_in_bytes():
    """Verify parsing size representations into raw bytes."""
    assert DockerParser.parse_size_in_bytes("15.42MiB") == int(15.42 * 1024 * 1024)
    assert DockerParser.parse_size_in_bytes("7.766GiB") == int(7.766 * 1024 * 1024 * 1024)
    assert DockerParser.parse_size_in_bytes("1.24kB") == int(1.24 * 1000)
    assert DockerParser.parse_size_in_bytes("0B") == 0
    assert DockerParser.parse_size_in_bytes("12.3MB") == int(12.3 * 1000 * 1000)
    assert DockerParser.parse_size_in_bytes("100") == 100


def test_parse_container_stats():
    """Verify parsing docker stats stdout."""
    stats_output = (
        "CONTAINER ID   NAME      CPU %     MEM USAGE / LIMIT     MEM %     NET I/O           BLOCK I/O         PIDS\n"
        "d3a82643a6d7   my-cont   0.05%     15.42MiB / 7.766GiB   0.19%     1.24kB / 0B       0B / 12.3MB       2\n"
    )
    stats_list = DockerParser.parse_container_stats(stats_output)
    
    assert len(stats_list) == 1
    s = stats_list[0]
    assert s.container_id == "d3a82643a6d7"
    assert s.name == "my-cont"
    assert s.cpu_percentage == 0.05
    assert s.memory_usage_bytes == int(15.42 * 1024 * 1024)

    assert s.memory_limit_bytes == int(7.766 * 1024 * 1024 * 1024)
    assert s.memory_percentage == 0.19
    assert s.network_rx_bytes == int(1.24 * 1000)
    assert s.network_tx_bytes == 0
    assert s.block_read_bytes == 0
    assert s.block_write_bytes == 12.3 * 1000 * 1000
    assert s.pids_count == 2


def test_parse_container_metadata():
    """Verify parsing docker inspect JSON output."""
    inspect_output = """
    [
        {
            "Id": "d3a82643a6d7",
            "Name": "/my-cont",
            "Config": {
                "Image": "nginx:latest",
                "Cmd": ["nginx", "-g", "daemon off;"],
                "Labels": {
                    "version": "1.0"
                }
            },
            "Image": "sha256:12345",
            "Created": "2026-07-21T14:29:48.123456Z",
            "State": {
                "Status": "running",
                "RestartCount": 2,
                "Pid": 12345
            },
            "HostConfig": {
                "NetworkMode": "bridge"
            },
            "Mounts": [
                {
                    "Source": "/host/path",
                    "Destination": "/container/path",
                    "Mode": "rw",
                    "RW": true,
                    "Propagation": "rprivate"
                }
            ]
        }
    ]
    """
    metadata_list = DockerParser.parse_container_metadata(inspect_output)
    
    assert len(metadata_list) == 1
    m = metadata_list[0]
    assert m.container_id == "d3a82643a6d7"
    assert m.name == "my-cont"
    assert m.image == "nginx:latest"
    assert m.image_id == "sha256:12345"
    assert m.state == "running"
    assert m.restart_count == 2
    assert m.pid == 12345
    assert m.command == "nginx -g daemon off;"
    assert m.labels == {"version": "1.0"}
    assert m.network_mode == "bridge"
    assert len(m.mounts) == 1
    assert m.mounts[0].source == "/host/path"
    assert m.mounts[0].destination == "/container/path"
    assert m.mounts[0].rw is True


def test_parse_networks_and_volumes():
    """Verify parsing networks and volumes."""
    net_output = (
        "NETWORK ID     NAME      DRIVER    SCOPE\n"
        "d3a82643a6d7   bridge    bridge    local\n"
    )
    vol_output = (
        "DRIVER    VOLUME NAME\n"
        "local     my-vol\n"
    )
    
    networks = DockerParser.parse_networks(net_output)
    volumes = DockerParser.parse_volumes(vol_output)
    
    assert len(networks) == 1
    assert networks[0].network_id == "d3a82643a6d7"
    assert networks[0].name == "bridge"
    assert networks[0].driver == "bridge"
    assert networks[0].scope == "local"
    
    assert len(volumes) == 1
    assert volumes[0].driver == "local"
    assert volumes[0].name == "my-vol"

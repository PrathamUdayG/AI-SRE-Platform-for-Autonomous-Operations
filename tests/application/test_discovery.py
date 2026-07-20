# tests/application/test_discovery.py
"""Unit tests for the infrastructure discovery pipeline components."""

from unittest.mock import AsyncMock, MagicMock

import pytest

from src.application.discovery.parsers import (
    CPUParser,
    FilesystemParser,
    MemoryParser,
    NetworkParser,
    OSParser,
    TimezoneParser,
    UptimeParser,
)
from src.application.services.discovery_service import DiscoveryService
from src.domain.discovery.commands import DiscoveryCommands
from src.domain.dtos.discovery_result import DiscoveryResult
from src.domain.entities.server import Server
from src.domain.exceptions import ConnectionFailedError, NotFoundError

# ---------- Mock Command Output Consts ----------
OS_RELEASE_MOCK = """
NAME="Ubuntu"
VERSION="22.04.2 LTS (Jammy Jellyfish)"
ID=ubuntu
ID_LIKE=debian
PRETTY_NAME="Ubuntu 22.04.2 LTS"
VERSION_ID="22.04"
"""

LSCPU_MOCK = """
Architecture:            x86_64
CPU op-mode(s):        32-bit, 64-bit
Address sizes:         39 bits physical, 48 bits virtual
Byte Order:            Little Endian
CPU(s):                  4
On-line CPU(s) list:   0-3
Vendor ID:             GenuineIntel
Model name:            Intel(R) Xeon(R) Gold 6140 CPU @ 2.30GHz
CPU family:            6
Model:                 85
Thread(s) per core:      2
Core(s) per socket:    2
Socket(s):               1
"""

FREE_M_MOCK = """
               total        used        free      shared  buff/cache   available
Mem:            7934        2142        2189         298        3602        5192
Swap:           2048           0        2048
"""

DF_HT_MOCK = """
Filesystem     Type      Size  Used Avail Use% Mounted on
udev           devtmpfs  3.9G     0  3.9G   0% /dev
tmpfs          tmpfs     794M  1.2M  793M   1% /run
/dev/sda1      ext4       49G   12G   35G  26% /
tmpfs          tmpfs     3.9G     0  3.9G   0% /dev/shm
/dev/sdb1      ext4      100G   20G   80G  20% /data
"""

IP_ADDR_MOCK = """
1: lo    inet 127.0.0.1/8 scope host lo\\
2: eth0    inet 192.168.1.10/24 brd 192.168.1.255 scope global eth0\\
2: eth0    inet6 fe80::215:5dff:fe00:1a2b/64 scope link\\
"""

TIMEDATECTL_MOCK = """
               Local time: Mon 2026-07-20 10:55:00 UTC
           Universal time: Mon 2026-07-20 10:55:00 UTC
                 RTC time: Mon 2026-07-20 10:55:00 UTC
                Time zone: Europe/London (BST, +0100)
System clock synchronized: yes
              NTP service: active
          RTC in local TZ: no
"""

UPTIME_MOCK = " 10:55:00 up  2:15,  1 user,  load average: 0.08, 0.02, 0.01"


# ---------- Parser Tests ----------
def test_os_parser():
    """Verify OS release string parsing."""
    os_name = OSParser.parse(OS_RELEASE_MOCK)
    assert os_name == "Ubuntu 22.04.2 LTS"

    os_fallback = OSParser.parse('NAME="Debian"')
    assert os_fallback == "Debian"

    os_unknown = OSParser.parse("")
    assert os_unknown == "Unknown Linux"


def test_cpu_parser():
    """Verify lscpu details mapping."""
    cpu_info = CPUParser.parse(LSCPU_MOCK)
    assert cpu_info.model == "Intel(R) Xeon(R) Gold 6140 CPU @ 2.30GHz"
    assert cpu_info.cores == 4
    assert cpu_info.sockets == 1
    assert cpu_info.threads_per_core == 2
    assert cpu_info.architecture == "x86_64"


def test_memory_parser():
    """Verify free memory extraction."""
    mem_info = MemoryParser.parse(FREE_M_MOCK)
    assert mem_info.total_mb == 7934.0
    assert mem_info.used_mb == 2142.0
    assert mem_info.free_mb == 2189.0
    assert mem_info.buff_cache_mb == 3602.0
    assert mem_info.available_mb == 5192.0


def test_filesystem_parser():
    """Verify df filesystem mounts extraction."""
    disks = FilesystemParser.parse(DF_HT_MOCK)
    assert len(disks) == 2

    # Check root disk
    assert disks[0].device == "/dev/sda1"
    assert disks[0].mount_point == "/"
    assert disks[0].fstype == "ext4"
    assert disks[0].total_gb == 49.0
    assert disks[0].used_gb == 12.0
    assert disks[0].percentage == 26.0

    # Check /data disk
    assert disks[1].device == "/dev/sdb1"
    assert disks[1].mount_point == "/data"
    assert disks[1].total_gb == 100.0


def test_network_parser():
    """Verify IP and interface network parsing."""
    interfaces = NetworkParser.parse(IP_ADDR_MOCK)
    assert len(interfaces) == 2

    assert interfaces[0].name == "lo"
    assert "127.0.0.1" in interfaces[0].ip_addresses

    assert interfaces[1].name == "eth0"
    assert "192.168.1.10" in interfaces[1].ip_addresses


def test_timezone_parser():
    """Verify timedatectl timezone parsing."""
    tz = TimezoneParser.parse(TIMEDATECTL_MOCK)
    assert tz == "Europe/London (BST, +0100)"


def test_uptime_parser():
    """Verify uptime parsing."""
    uptime = UptimeParser.parse(UPTIME_MOCK)
    assert uptime == "2:15"


# ---------- Command Catalog Test ----------
def test_command_catalog():
    """Verify command catalog returns expected commands."""
    assert DiscoveryCommands.HOSTNAME == "hostname"
    assert DiscoveryCommands.OS_INFO == "cat /etc/os-release"
    assert "free" in DiscoveryCommands.MEMORY_INFO
    assert "df" in DiscoveryCommands.DISK_INFO


# ---------- DiscoveryService Tests ----------
@pytest.mark.asyncio
async def test_discover_server_not_found():
    """Verify DiscoveryService raises NotFoundError for unregistered server."""
    mock_server_repo = MagicMock()
    mock_server_repo.get_by_id = AsyncMock(return_value=None)
    mock_discovery_repo = MagicMock()
    mock_resolver = MagicMock()

    service = DiscoveryService(mock_server_repo, mock_discovery_repo, mock_resolver)

    with pytest.raises(NotFoundError):
        await service.discover_server(server_id=999)


@pytest.mark.asyncio
async def test_discover_server_success():
    """Verify end-to-end discovery orchestration with mocked SSH connector."""
    # Mock server database record
    mock_server = Server(
        id=1,
        hostname="production-web",
        ip_address="10.0.0.5",
        operating_system="Linux",
        cpu_cores=4,
        memory_gb=8.0,
    )

    mock_server_repo = MagicMock()
    mock_server_repo.get_by_id = AsyncMock(return_value=mock_server)

    # Mock SSH Connector
    mock_connector_inst = MagicMock()

    # Return different mock outputs for each executed command
    async def mock_execute(cmd, timeout=None):
        if cmd == DiscoveryCommands.HOSTNAME:
            return "production-web"
        elif cmd == DiscoveryCommands.OS_INFO:
            return OS_RELEASE_MOCK
        elif cmd == DiscoveryCommands.KERNEL_INFO:
            return "5.15.0-72-generic"
        elif cmd == DiscoveryCommands.ARCH:
            return "x86_64"
        elif cmd == DiscoveryCommands.CPU_INFO:
            return LSCPU_MOCK
        elif cmd == DiscoveryCommands.MEMORY_INFO:
            return FREE_M_MOCK
        elif cmd == DiscoveryCommands.DISK_INFO:
            return DF_HT_MOCK
        elif cmd == DiscoveryCommands.NETWORK_INFO:
            return IP_ADDR_MOCK
        elif cmd == DiscoveryCommands.TIMEZONE:
            return TIMEDATECTL_MOCK
        elif cmd == DiscoveryCommands.UPTIME:
            return UPTIME_MOCK
        return ""

    mock_connector_inst.connect = AsyncMock()
    mock_connector_inst.execute = AsyncMock(side_effect=mock_execute)
    mock_connector_inst.disconnect = AsyncMock()

    mock_resolver = MagicMock()
    mock_resolver.resolve = MagicMock(return_value=mock_connector_inst)

    # Mock Discovery Snapshot Repository
    mock_discovery_repo = MagicMock()
    mock_discovery_repo.save = AsyncMock(side_effect=lambda s: s)

    # Trigger Service Discovery
    service = DiscoveryService(mock_server_repo, mock_discovery_repo, mock_resolver)
    result = await service.discover_server(server_id=1)

    # Assertions
    assert isinstance(result, DiscoveryResult)
    assert result.server_id == 1
    assert result.hostname == "production-web"
    assert result.operating_system == "Ubuntu 22.04.2 LTS"
    assert result.kernel_version == "5.15.0-72-generic"
    assert result.cpu.cores == 4
    assert result.memory.total_mb == 7934.0
    assert len(result.disks) == 2
    assert len(result.network_interfaces) == 2

    mock_connector_inst.connect.assert_called_once()
    mock_connector_inst.disconnect.assert_called_once()
    mock_discovery_repo.save.assert_called_once()


@pytest.mark.asyncio
async def test_discover_server_ssh_failure():
    """Verify service raises ConnectionFailedError on SSH failure."""
    mock_server = Server(
        id=1,
        hostname="prod-web",
        ip_address="10.0.0.5",
        operating_system="Linux",
        cpu_cores=4,
        memory_gb=8.0,
    )
    mock_server_repo = MagicMock()
    mock_server_repo.get_by_id = AsyncMock(return_value=mock_server)

    mock_connector_inst = MagicMock()
    mock_connector_inst.connect = AsyncMock(
        side_effect=RuntimeError("SSH Connection Timeout")
    )
    mock_connector_inst.disconnect = AsyncMock()

    mock_resolver = MagicMock()
    mock_resolver.resolve = MagicMock(return_value=mock_connector_inst)

    mock_discovery_repo = MagicMock()

    service = DiscoveryService(mock_server_repo, mock_discovery_repo, mock_resolver)

    with pytest.raises(ConnectionFailedError):
        await service.discover_server(server_id=1)

    mock_connector_inst.disconnect.assert_called_once()

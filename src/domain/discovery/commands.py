# src/domain/discovery/commands.py
"""Central catalog of discovery commands for remote Linux hosts."""


class DiscoveryCommands:
    """Central catalog of system commands used to discover Linux infrastructure configuration."""

    HOSTNAME = "hostname"
    OS_INFO = "cat /etc/os-release"
    KERNEL_INFO = "uname -r"
    ARCH = "uname -m"
    CPU_INFO = "lscpu"
    MEMORY_INFO = "free -m"
    DISK_INFO = "df -hT"
    NETWORK_INFO = "ip -o addr show"
    TIMEZONE = "timedatectl"
    UPTIME = "uptime"

"""
-------------------------------------------------------
File:
test_system_parser.py

Purpose:
Unit tests for the SystemParser in the Application Layer.

Why this file exists:
Verifies that static system configuration tools outputs are correctly parsed and translated.

Responsibilities:
- Verify hostnamectl key-value parsing.
- Verify uname -a layout decoding.
- Verify /etc/os-release properties parsing.
- Verify lscpu details mapping.
- Verify uptime format conversions to seconds.
- Verify fallback logic and validation triggers.

Used By:
- pytest runner

Depends On:
- src.application.parsers.system_parser
- src.domain.exceptions.ValidationError
-------------------------------------------------------
"""

from datetime import datetime, timezone
import pytest

from src.application.parsers.system_parser import SystemParser
from src.domain.exceptions import ValidationError


def test_parse_normal_system_metadata():
    """Verify standard CLI tools output parsing succeeds."""
    hostnamectl_data = """
   Static hostname: my-ubuntu-host
         Icon name: computer-vm
           Chassis: vm
        Machine ID: 3d5b0a394a53488f8d9b23b1c67d710f
           Boot ID: f938b8c2c8f844bda2300b95ebff4f2a
    Virtualization: kvm
  Operating System: Ubuntu 22.04.3 LTS
            Kernel: Linux 5.15.0-88-generic
      Architecture: x86_64
    """

    uname_data = (
        "Linux my-ubuntu-host 5.15.0-88-generic #98-Ubuntu SMP Mon Oct 2 x86_64 GNU/Linux"
    )

    os_release_data = """
NAME="Ubuntu"
VERSION_ID="22.04"
PRETTY_NAME="Ubuntu 22.04.3 LTS"
    """

    lscpu_data = """
Architecture:                    x86_64
CPU(s):                          4
Vendor ID:                       GenuineIntel
Model name:                      Intel(R) Core(TM) i7-10700 CPU @ 2.90GHz
Thread(s) per core:              2
Core(s) per socket:              2
Socket(s):                       1
Hypervisor vendor:               KVM
    """

    uptime_data = " 14:22:00 up 12 days,  3:15,  1 user,  load average: 0.10, 0.05, 0.01"
    timezone_data = "Europe/London\n"

    now = datetime.now(timezone.utc)

    metrics = SystemParser.parse(
        hostnamectl_output=hostnamectl_data,
        uname_output=uname_data,
        os_release_output=os_release_data,
        lscpu_output=lscpu_data,
        uptime_output=uptime_data,
        timezone_output=timezone_data,
        timestamp=now,
    )

    # 1. Identity
    assert metrics.host_identity.hostname == "my-ubuntu-host"
    assert metrics.host_identity.machine_id == "3d5b0a394a53488f8d9b23b1c67d710f"
    assert metrics.host_identity.boot_id == "f938b8c2c8f844bda2300b95ebff4f2a"

    # 2. OS
    assert metrics.os_info.distribution_name == "Ubuntu"
    assert metrics.os_info.distribution_version == "22.04"
    assert metrics.os_info.pretty_name == "Ubuntu 22.04.3 LTS"
    assert metrics.os_info.kernel_release == "5.15.0-88-generic"
    assert metrics.os_info.architecture == "x86_64"

    # 3. CPU
    assert metrics.cpu_info.cpu_model == "Intel(R) Core(TM) i7-10700 CPU @ 2.90GHz"
    assert metrics.cpu_info.vendor == "GenuineIntel"
    assert metrics.cpu_info.logical_cpu_count == 4
    assert metrics.cpu_info.physical_cpu_count == 1
    assert metrics.cpu_info.threads_per_core == 2
    assert metrics.cpu_info.cores_per_socket == 2

    # 4. Hardware
    assert metrics.hardware.virtualization_type == "kvm"
    assert metrics.hardware.hypervisor_vendor == "KVM"

    # 5. Uptime / State
    # 12 days * 86400 + 3 hours * 3600 + 15 min * 60 = 1036800 + 10800 + 900 = 1048500
    assert metrics.system_state.system_uptime == 1048500.0
    assert metrics.system_state.boot_time is not None

    # 6. Timezone / Mode
    assert metrics.timezone == "Europe/London"
    assert metrics.operating_mode == "static"


def test_uptime_parse_variants():
    """Verify various uptime string formats convert correctly to seconds."""
    p = SystemParser.parse_uptime_to_seconds
    assert p(" 14:22:00 up 50 min,  1 user,  load average: 0.10") == 3000.0
    assert p(" 14:22:00 up 3:15,  1 user") == 11700.0
    assert p(" 14:22:00 up 1 day,  2:30,  2 users") == 95400.0
    assert p("up 5 mins") == 300.0
    assert p("") == 0.0


def test_parse_empty_or_none_raises_validation_error():
    """Verify that empty inputs raise ValidationError."""
    now = datetime.now(timezone.utc)
    with pytest.raises(ValidationError):
        SystemParser.parse("", "", "", "", "", "", now)

    with pytest.raises(ValidationError):
        SystemParser.parse(None, "", "", "", "", "", now)

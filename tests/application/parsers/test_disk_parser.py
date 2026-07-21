"""
-------------------------------------------------------
File:
test_disk_parser.py

Purpose:
Unit tests for the DiskParser in the Application Layer.

Why this file exists:
Verifies that df partition information and low-level device controller metrics are parsed correctly, and edge cases such as missing files, invalid integers, or empty files raise ValidationError.

Responsibilities:
- Verify standard parsing outputs.
- Verify mount point name concatenations.
- Verify handling of non-integer values.
- Verify empty inputs.
- Verify malformed rows.

Used By:
- pytest runner

Depends On:
- src.application.parsers.disk_parser
- src.domain.exceptions.ValidationError
-------------------------------------------------------
"""

from datetime import datetime, timezone
import pytest

from src.application.parsers.disk_parser import DiskParser
from src.domain.exceptions import ValidationError


def test_parse_normal_disk_info():
    """Verify that valid df and diskstats outputs parse successfully."""
    df_data = """
    Filesystem     Type        1B-blocks         Used    Available Use% Mounted on
    /dev/sda1      ext4      31260487680  10485760000  19178967040  36% /
    tmpfs          tmpfs      8255475712            0   8255475712   0% /dev/shm
    """
    stats_data = """
       8       0 sda 102434 23098 5439812 129384 54318 29018 4392811 543921 0 129848 643928
       8       1 sda1 102400 23000 5400000 129000 54000 29000 4390000 543000 0 129000 643000
    """
    now = datetime.now(timezone.utc)

    metrics = DiskParser.parse(df_data, stats_data, now)

    # 1. Verify filesystems
    assert len(metrics.filesystems) == 2
    
    fs1 = metrics.filesystems[0]
    assert fs1.filesystem == "/dev/sda1"
    assert fs1.fstype == "ext4"
    assert fs1.total_bytes == 31260487680
    assert fs1.used_bytes == 10485760000
    assert fs1.available_bytes == 19178967040
    assert fs1.use_percent == 36
    assert fs1.mount_point == "/"

    fs2 = metrics.filesystems[1]
    assert fs2.filesystem == "tmpfs"
    assert fs2.fstype == "tmpfs"
    assert fs2.total_bytes == 8255475712
    assert fs2.used_bytes == 0
    assert fs2.available_bytes == 8255475712
    assert fs2.use_percent == 0
    assert fs2.mount_point == "/dev/shm"

    # 2. Verify disk IO
    assert len(metrics.disk_io) == 2
    
    io1 = metrics.disk_io[0]
    assert io1.major_number == 8
    assert io1.minor_number == 0
    assert io1.device_name == "sda"
    assert io1.reads_completed == 102434
    assert io1.reads_merged == 23098
    assert io1.sectors_read == 5439812
    assert io1.read_time_ms == 129384
    assert io1.writes_completed == 54318
    assert io1.writes_merged == 29018
    assert io1.sectors_written == 4392811
    assert io1.write_time_ms == 543921
    assert io1.io_in_progress == 0
    assert io1.io_time_ms == 129848
    assert io1.weighted_io_time_ms == 643928
    assert metrics.timestamp == now


def test_parse_missing_filesystems_but_valid_io():
    """Verify parser succeeds even if filesystems list is empty, provided disk IO is valid."""
    df_data = "Filesystem     Type        1B-blocks         Used    Available Use% Mounted on"
    stats_data = "   8       0 sda 102434 23098 5439812 129384 54318 29018 4392811 543921 0 129848 643928"
    now = datetime.now(timezone.utc)

    metrics = DiskParser.parse(df_data, stats_data, now)
    assert len(metrics.filesystems) == 0
    assert len(metrics.disk_io) == 1
    assert metrics.disk_io[0].device_name == "sda"


def test_parse_invalid_df_integer_skips_line():
    """Verify that partition rows with invalid integers are skipped instead of crashing."""
    df_data = """
    Filesystem     Type        1B-blocks         Used    Available Use% Mounted on
    /dev/sda1      ext4      invalid_total  10485760000  19178967040  36% /
    tmpfs          tmpfs      8255475712            0   8255475712   0% /dev/shm
    """
    stats_data = "   8       0 sda 102434 23098 5439812 129384 54318 29018 4392811 543921 0 129848 643928"
    now = datetime.now(timezone.utc)

    metrics = DiskParser.parse(df_data, stats_data, now)
    # The first row should be skipped due to value error, leaving only the second filesystem
    assert len(metrics.filesystems) == 1
    assert metrics.filesystems[0].filesystem == "tmpfs"


def test_parse_empty_input_raises_validation_error():
    """Verify that completely empty inputs raise ValidationError."""
    now = datetime.now(timezone.utc)

    with pytest.raises(ValidationError):
        DiskParser.parse("", "", now)

    with pytest.raises(ValidationError):
        DiskParser.parse(None, None, now)


def test_parse_malformed_columns_raises_validation_error():
    """Verify malformed stats or df layouts raise ValidationError."""
    now = datetime.now(timezone.utc)

    # Missing column counts
    with pytest.raises(ValidationError):
        DiskParser.parse("Filesystem Type 123", "8 0 sda", now)

"""Parsing and conversion of NTP dates contained in datagrams."""

import datetime
import struct
import time
from typing import NamedTuple

# 63 zero bits followed by a one in the least signifigant bit is a special
# case meaning "immediately."
IMMEDIATELY = struct.pack(">Q", 1)

# timetag * (1 / 2 ** 32) == l32bits + (r32bits / 1 ** 32)
NTP_TIMESTAMP_TO_SECONDS = 1.0 / 2.0**32.0
SECONDS_TO_NTP_TIMESTAMP = 2.0**32.0

# From NTP lib.
SYSTEM_EPOCH = datetime.date(*time.gmtime(0)[0:3])
NTP_EPOCH = datetime.date(1900, 1, 1)
# _NTP_DELTA is 2208988800
NTP_DELTA = (SYSTEM_EPOCH - NTP_EPOCH).days * 24 * 3600


class Timestamp(NamedTuple):
    """NTP timestamp representation."""

    seconds: int
    fraction: int


class NtpError(Exception):
    """Base class for ntp module errors."""


def parse_timestamp(timestamp: int) -> Timestamp:
    """Parse NTP timestamp as Timetag."""
    seconds = timestamp >> 32
    fraction = timestamp & 0xFFFFFFFF
    return Timestamp(seconds, fraction)


def ntp_to_system_time(timestamp: bytes) -> float:
    """Convert a NTP timestamp to system time in seconds."""
    try:
        timestamp = struct.unpack(">Q", timestamp)[0]
    except Exception as e:
        raise NtpError(e) from e
    return timestamp * NTP_TIMESTAMP_TO_SECONDS - NTP_DELTA


def system_time_to_ntp(seconds: float) -> bytes:
    """Convert a system time in seconds to NTP timestamp."""
    try:
        seconds = seconds + NTP_DELTA
    except TypeError as e:
        raise NtpError(e) from e
    return struct.pack(">Q", int(seconds * SECONDS_TO_NTP_TIMESTAMP))


def ntp_time_to_system_epoch(seconds: float) -> float:
    """Convert a NTP time in seconds to system time in seconds."""
    return seconds - NTP_DELTA


def system_time_to_ntp_epoch(seconds: float) -> float:
    """Convert a system time in seconds to NTP time in seconds."""
    return seconds + NTP_DELTA

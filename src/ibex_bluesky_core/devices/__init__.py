"""Common utilities for use across devices."""

from __future__ import annotations

import binascii
import os
import zlib
from typing import Type

from ophyd_async.core import SignalRW, T
from ophyd_async.epics.signal import epics_signal_rw


def get_pv_prefix() -> str:
    """Return the PV prefix for the current instrument."""
    prefix = os.getenv("MYPVPREFIX")

    if prefix is None:
        raise EnvironmentError("MYPVPREFIX environment variable not available - please define")

    return prefix


def dehex_and_decompress(value: bytes) -> bytes:
    """Decompresses the inputted string, assuming it is in hex encoding.

    Args:
        value: The string to be decompressed, encoded in hex

    Returns A decompressed version of the inputted string

    """
    return zlib.decompress(binascii.unhexlify(value))


def compress_and_hex(value: str) -> bytes:
    """Compress the inputted string and encode it as hex.

    Args:
        value: The string to be compressed

    Returns A compressed and hexed version of the inputted string

    """
    compr = zlib.compress(bytes(value, "utf-8"))
    return binascii.hexlify(compr)


def isis_epics_signal_rw(datatype: Type[T], read_pv: str, name: str = "") -> SignalRW[T]:
    """Make a RW signal with ISIS' PV naming standard ie. read_pv as TITLE, write_pv as TITLE:SP."""
    write_pv = f"{read_pv}:SP"
    return epics_signal_rw(datatype, read_pv, write_pv, name)

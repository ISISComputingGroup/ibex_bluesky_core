"""Common utilities for use across devices."""

from __future__ import annotations

import binascii
import zlib
from typing import TypeVar

from ophyd_async.core import SignalDatatype, SignalRW
from ophyd_async.epics.core import epics_signal_rw

T = TypeVar("T", bound=SignalDatatype)


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


def isis_epics_signal_rw(datatype: type[T], read_pv: str, name: str = "") -> SignalRW[T]:
    """Make a RW signal with ISIS' PV naming standard ie. read_pv as TITLE, write_pv as TITLE:SP."""
    write_pv = f"{read_pv}:SP"
    return epics_signal_rw(datatype, read_pv, write_pv, name)

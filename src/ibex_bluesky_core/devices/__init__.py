"""ISIS-specific bluesky devices and device-related utilities.

The devices in this module are implemented using the :py:obj:`ophyd_async` library,
which in turn reads or writes to the underlying EPICS PVs to control equipment.
"""

from __future__ import annotations

import binascii
import zlib
from typing import TypeVar

from ophyd_async.core import SignalDatatype, SignalRW, StrictEnum
from ophyd_async.epics.core import epics_signal_rw

T = TypeVar("T", bound=SignalDatatype)

__all__ = ["NoYesChoice", "compress_and_hex", "dehex_and_decompress", "isis_epics_signal_rw"]


def dehex_and_decompress(value: bytes) -> bytes:
    """Decompresses the inputted string, assuming it is in hex encoding.

    Args:
        value: The string to be decompressed, encoded in hex

    Returns:
        A decompressed version of the inputted string

    """
    return zlib.decompress(binascii.unhexlify(value))


def compress_and_hex(value: str) -> bytes:
    """Compress the inputted string and encode it as hex.

    Args:
        value: The string to be compressed

    Returns:
        A compressed and hexed version of the inputted string

    """
    compr = zlib.compress(bytes(value, "utf-8"))
    return binascii.hexlify(compr)


def isis_epics_signal_rw(datatype: type[T], read_pv: str, name: str = "") -> SignalRW[T]:
    """Make a RW signal with ISIS' PV naming standard.

    For a PV like ``IN:INSTNAME:SOME_PARAMETER``:

    - The ``read_pv`` will be set to ``IN:INSTNAME:SOME_PARAMETER``
    - The ``write_pv`` will be set to ``IN:INSTNAME:SOME_PARAMETER:SP``
    """
    write_pv = f"{read_pv}:SP"
    return epics_signal_rw(datatype, read_pv, write_pv, name)


class NoYesChoice(StrictEnum):
    """No-Yes enum for an mbbi/mbbo or bi/bo with capitalised "No"/"Yes" options."""

    NO = "No"
    YES = "Yes"

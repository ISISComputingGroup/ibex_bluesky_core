from __future__ import annotations

from typing import Type

from ophyd_async.core import SignalRW, T
from ophyd_async.epics.signal import epics_signal_rw


def isis_epics_signal_rw(datatype: Type[T], read_pv: str, name: str = "") -> SignalRW[T]:
    """Utility function for making a RW signal using the ISIS PV naming standard ie. read_pv being TITLE,
    write_pv being TITLE:SP
    """
    write_pv = f"{read_pv}:SP"
    return epics_signal_rw(datatype, read_pv, write_pv, name)

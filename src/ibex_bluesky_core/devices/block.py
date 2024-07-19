"""ophyd-async devices and utilities for communicating with IBEX blocks."""

from typing import Generic, Type, TypeVar

from bluesky.protocols import Movable
from ophyd_async.core import AsyncStatus, HintedSignal, SignalRW, StandardReadable
from ophyd_async.epics.signal import epics_signal_rw

from ibex_bluesky_core.devices import get_pv_prefix

"""Block data type"""
T = TypeVar("T")


class Block(StandardReadable, Movable, Generic[T]):
    """Device representing an IBEX block of arbitrary data type."""

    def __init__(self, block_name: str, datatype: Type[T]) -> None:
        """Create a new Block device."""
        pv_prefix = get_pv_prefix()

        with self.add_children_as_readables(HintedSignal):
            self.value: SignalRW[T] = epics_signal_rw(
                datatype, f"{pv_prefix}CS:SB:{block_name}", f"{pv_prefix}CS:SB:{block_name}:SP"
            )

        super().__init__(name=block_name)

    def set(self, value: T) -> AsyncStatus:
        """Set the setpoint of this block."""
        return self.value.set(value, wait=False)

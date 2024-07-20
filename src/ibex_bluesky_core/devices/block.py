"""ophyd-async devices and utilities for communicating with IBEX blocks."""

from typing import Generic, Type, TypeVar

from bluesky.protocols import Locatable, Location
from ophyd_async.core import AsyncStatus, HintedSignal, SignalR, SignalRW, StandardReadable
from ophyd_async.epics.signal import epics_signal_r, epics_signal_rw

"""Block data type"""
T = TypeVar("T")


class Block(StandardReadable, Locatable, Generic[T]):
    """Device representing an IBEX read/write block of arbitrary data type."""

    def __init__(self, prefix: str, block_name: str, datatype: Type[T]) -> None:
        """Create a new Block device."""
        with self.add_children_as_readables(HintedSignal):
            self.readback: SignalR[T] = epics_signal_r(datatype, f"{prefix}CS:SB:{block_name}")

        with self.add_children_as_readables():
            self.setpoint: SignalRW[T] = epics_signal_rw(datatype, f"{prefix}CS:SB:{block_name}:SP")

        super().__init__(name=block_name)
        self.readback.set_name(block_name)

    def set(self, value: T) -> AsyncStatus:
        """Set the setpoint of this block.

        The status returned by this object will be marked done when:
        - An EPICS completion callback has been received
          * (To do: make completion callback optional)
        - (To do: an optionally-configured time period)
        - (To do: an optionally-configured readback tolerance)
        """
        return self.setpoint.set(value, wait=True)

    async def locate(self) -> Location[T]:
        """Get the current 'location' (primary value) of this block."""
        return {
            "readback": await self.readback.get_value(),
            "setpoint": await self.setpoint.get_value(),
        }

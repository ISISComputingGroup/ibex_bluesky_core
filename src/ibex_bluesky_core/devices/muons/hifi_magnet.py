"""Device for a HIFI magnet axis."""

import asyncio

from ophyd_async.core import AsyncStatus, HintedSignal, StandardReadable, observe_value
from ophyd_async.epics.core import epics_signal_r, epics_signal_rw, epics_signal_w


class HIFIMagnetAxis(StandardReadable):
    """Device for a HIFI magnet axis."""

    def __init__(self, prefix: str, axis: str) -> None:
        """Create a HIFI magnet axis.

        Args:
            prefix: the PV prefix.
            axis: the axis name where (prefix)CS:SB:Field_(axis)_{Target, Ready, Go)

        """
        with self.add_children_as_readables(HintedSignal):
            self.setpoint = epics_signal_rw(float, f"{prefix}CS:SB:Field_{axis}_Target")

        self.readback = epics_signal_r(float, f"{prefix}CS:SB:Field_{axis}")
        self.ready = epics_signal_r(bool, f"{prefix}CS:SB:Field_{axis}_Ready")
        self.go = epics_signal_w(bool, f"{prefix}CS:SB:Field_{axis}_Go")

        super().__init__(name=f"Field_{axis}_magnet")
        self.setpoint.set_name(f"Field_{axis}_magnet")

    @AsyncStatus.wrap
    async def trigger(self) -> None:  # noqa: D102
        pass

    @AsyncStatus.wrap
    async def set(self, value: float) -> None:
        """Set the setpoint."""
        await self.setpoint.set(value, wait=True, timeout=None)
        await asyncio.sleep(5.0)  # race conditions?
        await self.go.set(True, wait=True, timeout=None)
        await asyncio.sleep(5.0)
        async for stat in observe_value(self.ready):
            if stat:
                break
        await asyncio.sleep(5.0)  # ensure latest readings have been taken

    def __repr__(self) -> str:
        """Debug representation."""
        return f"{self.__class__.__name__}(name={self.name})"

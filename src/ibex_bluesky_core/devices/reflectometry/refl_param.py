"""Device that provides utility functions for a reflectometry server parameter."""

import asyncio

from ophyd_async.core import (
    AsyncStatus,
    HintedSignal,
    SignalR,
    SignalW,
    StandardReadable,
    observe_value,
)
from ophyd_async.epics.core import epics_signal_r, epics_signal_w


class ReflParameter(StandardReadable):
    """Utility device for a reflectometry server parameter."""

    def __init__(self, prefix: str, name: str) -> None:
        """Reflectometry server parameter.

        Args:
            prefix: the PV prefix.
            name: the name of the parameter.

        """
        with self.add_children_as_readables(HintedSignal):
            self.readback: SignalR[float] = epics_signal_r(float, f"{prefix}REFL_01:PARAM:{name}")
        self.setpoint: SignalW[float] = epics_signal_w(float, f"{prefix}REFL_01:PARAM:{name}:SP")
        self.changing: SignalR[bool] = epics_signal_r(
            bool, f"{prefix}REFL_01:PARAM:{name}:CHANGING"
        )
        self.redefine = ReflParameterRedefine(
            prefix=f"{prefix}REFL_01:PARAM:{name}:", name=name + "redefine"
        )
        super().__init__(name=name)
        self.readback.set_name(name)

    @AsyncStatus.wrap
    async def trigger(self) -> None:  # noqa: D102
        pass

    @AsyncStatus.wrap
    async def set(self, value: float) -> None:
        """Set the setpoint."""
        await self.setpoint.set(value, wait=True, timeout=None)
        await asyncio.sleep(0.1)
        async for chg in observe_value(self.changing):
            if not chg:
                break

    def __repr__(self) -> str:
        """Debug representation."""
        return f"{self.__class__.__name__}(name={self.name})"


class ReflParameterRedefine(StandardReadable):
    """Utility device for redefining a reflectometry server parameter."""

    def __init__(self, prefix: str, name: str) -> None:
        with self.add_children_as_readables(HintedSignal):
            self.changed: SignalR[bool] = epics_signal_r(bool, f"{prefix}DEFINE_POS_CHANGED")
        self.define_pos_sp = epics_signal_w(float, f"{prefix}DEFINE_POS:SP")
        super().__init__(name)

    @AsyncStatus.wrap
    async def trigger(self) -> None:  # noqa: D102
        pass

    @AsyncStatus.wrap
    async def set(self, value: float) -> None:
        """Set the setpoint."""
        await self.define_pos_sp.set(value, wait=True, timeout=None)
        await asyncio.sleep(0.1)
        async for chg in observe_value(self.changed):
            if not chg:
                break

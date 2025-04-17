"""Devices specific to Reflectometry beamlines."""

import asyncio
import logging

from bluesky.protocols import NamedMovable
from ophyd_async.core import (
    AsyncStatus,
    SignalR,
    SignalW,
    StandardReadable,
    StandardReadableFormat,
    observe_value,
)
from ophyd_async.epics.core import epics_signal_r, epics_signal_w

from ibex_bluesky_core.utils import get_pv_prefix

logger = logging.getLogger(__name__)

__all__ = ["ReflParameter", "ReflParameterRedefine", "refl_parameter"]


class ReflParameter(StandardReadable, NamedMovable[float]):
    """Utility device for a reflectometry server parameter."""

    def __init__(
        self, prefix: str, name: str, changing_timeout_s: float, *, has_redefine: bool = True
    ) -> None:
        """Reflectometry server parameter.

        Args:
            prefix: the PV prefix.
            name: the name of the parameter.
            changing_timeout_s: seconds to wait for the CHANGING signal to go to False after a set.
            has_redefine: whether this parameter can be redefined.

        """
        with self.add_children_as_readables(StandardReadableFormat.HINTED_SIGNAL):
            self.readback: SignalR[float] = epics_signal_r(float, f"{prefix}REFL_01:PARAM:{name}")
        self.setpoint: SignalW[float] = epics_signal_w(float, f"{prefix}REFL_01:PARAM:{name}:SP")
        self.changing: SignalR[bool] = epics_signal_r(
            bool, f"{prefix}REFL_01:PARAM:{name}:CHANGING"
        )
        if has_redefine:
            self.redefine = ReflParameterRedefine(prefix=f"{prefix}REFL_01:PARAM:{name}:", name="")
        else:
            self.redefine = None
        self.changing_timeout = changing_timeout_s
        super().__init__(name=name)
        self.readback.set_name(name)

    @AsyncStatus.wrap
    async def set(self, value: float) -> None:
        """Set the setpoint.

        This waits for the reflectometry parameter's 'CHANGING' PV to go True to
         indicate it has finished.
        """
        logger.info("setting %s to %s", self.setpoint.source, value)
        await self.setpoint.set(value, wait=True, timeout=None)
        await asyncio.sleep(0.1)
        logger.info("waiting for %s", self.changing.source)
        async for chg in observe_value(self.changing, done_timeout=self.changing_timeout):
            logger.debug("%s: %s", self.changing.source, chg)
            if not chg:
                break

    def __repr__(self) -> str:
        """Debug representation."""
        return f"{self.__class__.__name__}(name={self.name})"


class ReflParameterRedefine(StandardReadable):
    """Utility device for redefining a reflectometry server parameter."""

    def __init__(self, prefix: str, name: str) -> None:
        """Reflectometry server parameter redefinition.

        Args:
            prefix: the reflectometry parameter full address.
            name: the name of the parameter redefinition.

        """
        self.define_pos_sp = epics_signal_w(float, f"{prefix}DEFINE_POS_SP")
        super().__init__(name)

    @AsyncStatus.wrap
    async def set(self, value: float) -> None:
        """Set the setpoint.

        This redefines the position of a reflectometry parameter as the given value, and
        waits for the reflectometry parameter redefinition's 'CHANGED' PV
        to go True to indicate it has finished redefining the position.
        """
        logger.info("setting %s to %s", self.define_pos_sp.source, value)
        await self.define_pos_sp.set(value, wait=True, timeout=None)
        logger.info("waiting for 1s for redefine to finish")
        # The Reflectometry server has a CHANGED PV for a redefine, but it doesn't actually
        # give a monitor update, so just wait an arbitrary length of time for it to be done.
        await asyncio.sleep(1.0)


def refl_parameter(name: str, changing_timeout_s: float = 60.0) -> ReflParameter:
    """Small wrapper around a reflectometry parameter device.

    This automatically applies the current instrument's PV prefix.

    Args:
        name: the reflectometry parameter name.
        changing_timeout_s: time to wait (seconds) for the CHANGING signal to go False after a set.

    Returns a device pointing to a reflectometry parameter.

    """
    prefix = get_pv_prefix()
    return ReflParameter(prefix=prefix, name=name, changing_timeout_s=changing_timeout_s)

"""Utilities for the DAE device - mostly XML helpers."""

from typing import Generic, TypeVar

from bluesky.protocols import Movable
from ophyd_async.core import AsyncStatus, SignalDatatype, StandardReadable, StandardReadableFormat

from ibex_bluesky_core.devices import isis_epics_signal_rw

T = TypeVar("T", bound=SignalDatatype)


class DaeCheckingSignal(StandardReadable, Movable[T], Generic[T]):
    """Device that wraps a signal and checks the result of a set."""

    def __init__(self, datatype: type[T], prefix: str) -> None:
        """Device that wraps a signal and checks the result of a set.

        Args:
            datatype: The datatype of the signal.
            prefix: The PV address of the signal.

        """
        self.prefix = prefix
        with self.add_children_as_readables(StandardReadableFormat.HINTED_SIGNAL):
            self.signal = isis_epics_signal_rw(datatype, self.prefix)
        super().__init__(name="")

    @AsyncStatus.wrap
    async def set(self, value: T) -> None:
        """Check a signal when it is set. Raises if not set.

        Args:
            value: the value to set.

        """
        await self.signal.set(value, wait=True, timeout=None)
        actual_value = await self.signal.get_value()
        if value != actual_value:
            raise OSError(
                f"Signal {self.prefix} could not be set to {value}, actual value was {actual_value}"
            )

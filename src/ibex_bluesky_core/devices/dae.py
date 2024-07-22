"""ophyd-async devices for communicating with the ISIS data acquisition electronics."""

import asyncio
import time
from typing import Dict

from bluesky.protocols import Reading, Triggerable
from event_model import DataKey
from ophyd_async.core import AsyncStatus, SignalR, SignalX, StandardReadable
from ophyd_async.epics.signal import epics_signal_r, epics_signal_x


class Dae(
    StandardReadable,
    Triggerable,
):
    """Device representing the ISIS data acquisition electronics."""

    def __init__(self, prefix: str, name: str = "DAE") -> None:
        """Create a new Dae ophyd-async device."""
        with self.add_children_as_readables():
            self.good_uah: SignalR[float] = epics_signal_r(float, f"{prefix}DAE:GOODUAH")

        self.begin_run: SignalX = epics_signal_x(f"{prefix}DAE:BEGINRUN")
        self.end_run: SignalX = epics_signal_x(f"{prefix}DAE:ENDRUN")

        super().__init__(name=name)

    async def read(self) -> dict[str, Reading]:
        """Take a reading from the DAE.

        For the DAE, this means:
        - Read "intensity"
        - If configured to normalise, do normalisation

        Note that this method should be "fast" (should not wait for an acquisition) - it should
        only read existing PVs.

        In simple setups, e.g. one DAE run per scan point, we can use
        >>> import bluesky.plan_stubs as bps
        >>> dae = Dae(...)
        >>> def plan():
        >>>     yield from bps.trigger_and_read(dae)
        to trigger and wait for an acquisition, and then immediately read.

        In more complex setups where the plan needs fine-grained control about exactly when the DAE
        should begin and end, that is also possible by calling read() without trigger():
        >>> def plan():
        >>>     yield from bps.trigger(dae.begin_run)
        >>> # ... some special logic ...
        >>>     yield from bps.trigger(dae.end_run)
        >>>     yield from bps.create()
        >>>     yield from bps.read(dae)
        >>>     yield from bps.save()
        """
        reading: dict[str, Reading] = await super().read()

        # This is a placeholder for the moment - exactly how to get "intensity" will eventually be
        # passed in through configure(), along with any normalisation that needs to be done.
        intensity = await self.good_uah.get_value()

        reading[self.name] = Reading(
            timestamp=time.time(),
            value=intensity,
        )

        return reading

    async def describe(self) -> Dict[str, DataKey]:
        """Get metadata describing the reading."""
        descriptor: dict[str, DataKey] = await super().describe()

        descriptor[self.name] = DataKey(
            shape=[],
            dtype="number",
            source=self.good_uah.source,
        )

        return descriptor

    @AsyncStatus.wrap
    async def trigger(self) -> None:
        """Trigger counting.

        For the DAE, in the simple case with one run per scan point, this means:
        - Begin a run
        - Wait for configured time/uamps/frames/...
        - End the run

        This method is allowed to be "slow" - i.e. it should wait for data to be
        ready before returning.
        """
        await self.begin_run.trigger(wait=True)
        await asyncio.sleep(2)  # This is a placeholder for the moment
        await self.end_run.trigger(wait=True)

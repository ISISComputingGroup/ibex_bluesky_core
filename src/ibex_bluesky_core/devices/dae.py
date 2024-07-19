"""ophyd-async devices for communicating with the ISIS data acquisition electronics."""

import asyncio
import time
from typing import Dict

from bluesky.protocols import Reading, Triggerable
from event_model import DataKey
from ophyd_async.core import AsyncStatus, Device, SignalR, SignalX
from ophyd_async.epics.signal import epics_signal_r, epics_signal_x
from ophyd_async.protocols import AsyncReadable

from ibex_bluesky_core.devices import get_pv_prefix


class Dae(
    Device,
    AsyncReadable,
    Triggerable,
):
    """Device representing the ISIS data acquisition electronics."""

    def __init__(self) -> None:
        """Create a new Dae ophyd-async device."""
        super().__init__(name="DAE")

        pv_prefix = get_pv_prefix()

        self.good_uah: SignalR[float] = epics_signal_r(float, f"{pv_prefix}DAE:GOODUAH")

        self.begin_run: SignalX = epics_signal_x(f"{pv_prefix}DAE:BEGINRUN")
        self.end_run: SignalX = epics_signal_x(f"{pv_prefix}DAE:ENDRUN")

    async def read(self) -> dict[str, Reading]:
        """Take a reading.

        For the DAE, this means:
        - Read "intensity"
        - If configured to normalise, do normalisation
        """
        # This is a placeholder for the moment - exactly how to get "intensity" will eventually be
        # passed in through configure(), along with any normalisation that needs to be done.
        intensity = await self.good_uah.get_value()

        return {
            self.name: {
                "timestamp": time.time(),
                "value": intensity,
            }
        }

    async def describe(self) -> Dict[str, DataKey]:
        """Get metadata describing the reading."""
        return {
            self.name: {
                "shape": [],
                "dtype": "number",
                "source": self.good_uah.source,
            }
        }

    @AsyncStatus.wrap
    async def trigger(self) -> None:
        """Trigger counting.

        For the DAE, in the simple case with one run per scan point, this means:
        - Begin a run
        - Wait for configured time/uamps/frames/...
        - End the run
        """
        await self.begin_run.trigger(wait=True)
        await asyncio.sleep(2)  # This is a placeholder for the moment
        await self.end_run.trigger(wait=True)

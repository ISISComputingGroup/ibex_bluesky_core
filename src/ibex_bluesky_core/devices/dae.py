"""ophyd-async devices for communicating with the ISIS data acquisition electronics."""

import asyncio
from enum import Enum
import numpy as np
from bluesky.protocols import Triggerable
from ophyd_async.core import AsyncStatus, SignalR, SignalX, StandardReadable, ConfigSignal, SignalRW
from ophyd_async.epics.signal import epics_signal_r, epics_signal_x

from ibex_bluesky_core.utils.isis_epics_signals import isis_epics_signal_rw


class RunstateEnum(str, Enum):
    PROCESSING = "PROCESSING"
    SETUP = "SETUP"
    RUNNING = "RUNNING"
    PAUSED = "PAUSED"
    WAITING = "WAITING"
    VETOING = "VETOING"
    ENDING = "ENDING"
    SAVING = "SAVING"
    RESUMING = "RESUMING"
    PAUSING = "PAUSING"
    BEGINNING = "BEGINNING"
    ABORTING = "ABORTING"
    UPDATING = "UPDATING"
    STORING = "STORING"
    CHANING = "CHANGING"


class Dae(
    StandardReadable,
    Triggerable,
):
    """Device representing the ISIS data acquisition electronics."""

    def __init__(self, prefix: str, name: str = "DAE") -> None:
        """Create a new Dae ophyd-async device."""
        dae_prefix = f"{prefix}DAE:"
        with self.add_children_as_readables():
            self.good_uah: SignalR[float] = epics_signal_r(float, f"{dae_prefix}GOODUAH")

            self.good_frames: SignalR[int] = epics_signal_r(int, f"{dae_prefix}GOODFRAMES")
            self.period_good_frames: SignalR[int] = epics_signal_r(
                int, f"{dae_prefix}GOODFRAMES:PD"
            )
            self.run_number: SignalR[int] = epics_signal_r(int, f"{dae_prefix}IRUNNUMBER")

            self.run_state: SignalR[RunstateEnum] = epics_signal_r(
                RunstateEnum, f"{dae_prefix}RUNSTATE"
            )

            self.title: SignalRW = isis_epics_signal_rw(str, f"{dae_prefix}TITLE")
            self.users: SignalRW = isis_epics_signal_rw(str, f"{dae_prefix}_USERNAME")
            self.rb_number: SignalRW = isis_epics_signal_rw(str, f"{dae_prefix}_RBNUMBER")
            # why does np.typing.NDArray not work?
            # self.spectra_1_period_1: SignalR[np.typing.NDArray] = epics_signal_r(np.typing.NDArray, f"{prefix}DAE"
            #                                                                                         f":SPECTRA:1:1")

        with self.add_children_as_readables(ConfigSignal):
            # add configurable pvs here ie. wiring tables, spectra number, etc. - stuff that'll change the shape of other signals
            # self.
            pass

        self.begin_run: SignalX = epics_signal_x(f"{dae_prefix}BEGINRUN")
        self.end_run: SignalX = epics_signal_x(f"{dae_prefix}ENDRUN")
        self.pause_run: SignalX = epics_signal_x(f"{dae_prefix}PAUSERUN")
        self.resume_run: SignalX = epics_signal_x(f"{dae_prefix}RESUMERUN")
        self.abort_run: SignalX = epics_signal_x(f"{dae_prefix}ABORTRUN")

        super().__init__(name=name)

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

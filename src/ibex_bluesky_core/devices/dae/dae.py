"""ophyd-async devices for communicating with the ISIS data acquisition electronics."""

import asyncio
from enum import Enum

import numpy as np
from bluesky.protocols import Triggerable
from ophyd_async.core import AsyncStatus, SignalR, SignalRW, StandardReadable
from ophyd_async.epics.signal import epics_signal_r, epics_signal_rw

from ibex_bluesky_core.devices import isis_epics_signal_rw
from ibex_bluesky_core.devices.dae.dae_controls import DaeControls
from ibex_bluesky_core.devices.dae.dae_event_mode import DaeEventMode
from ibex_bluesky_core.devices.dae.dae_monitor import DaeMonitor
from ibex_bluesky_core.devices.dae.dae_period import DaePeriod
from ibex_bluesky_core.devices.dae.dae_period_settings import DaePeriodSettings
from ibex_bluesky_core.devices.dae.dae_settings import DaeSettings
from ibex_bluesky_core.devices.dae.dae_tcb_settings import DaeTCBSettings
from src.ibex_bluesky_core.devices.dae.dae_spectra import DaeSpectra


class RunstateEnum(str, Enum):
    """The run state."""

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
    CHANGING = "CHANGING"

    def __str__(self) -> str:
        """Return a string representation of the enum value."""
        return str(self.value)


class Dae(StandardReadable, Triggerable):
    """Device representing the ISIS data acquisition electronics."""

    def __init__(self, prefix: str, name: str = "DAE") -> None:
        """Create a new Dae ophyd-async device."""
        dae_prefix = f"{prefix}DAE:"
        self.good_uah: SignalR[float] = epics_signal_r(float, f"{dae_prefix}GOODUAH")
        self.count_rate: SignalR[float] = epics_signal_r(float, f"{dae_prefix}COUNTRATE")
        self.m_events: SignalR[float] = epics_signal_r(float, f"{dae_prefix}MEVENTS")
        self.sim_mode: SignalR[bool] = epics_signal_r(bool, f"{dae_prefix}SIM_MODE")
        self.neutron_proton_ratio: SignalR[float] = epics_signal_r(float, f"{dae_prefix}NPRATIO")
        self.good_frames: SignalR[int] = epics_signal_r(int, f"{dae_prefix}GOODFRAMES")
        self.raw_frames: SignalR[int] = epics_signal_r(int, f"{dae_prefix}RAWFRAMES")
        self.total_counts: SignalR[int] = epics_signal_r(int, f"{dae_prefix}TOTALCOUNTS")
        self.run_number: SignalR[int] = epics_signal_r(int, f"{dae_prefix}IRUNNUMBER")
        self.run_number_str: SignalR[str] = epics_signal_r(str, f"{dae_prefix}RUNNUMBER")
        self.cycle_number: SignalR[str] = epics_signal_r(str, f"{dae_prefix}ISISCYCLE")
        self.inst_name: SignalR[str] = epics_signal_r(str, f"{dae_prefix}INSTNAME")
        self.run_start_time: SignalR[str] = epics_signal_r(str, f"{dae_prefix}STARTTIME")
        self.run_duration: SignalR[int] = epics_signal_r(int, f"{dae_prefix}RUNDURATION")
        self.num_time_channels: SignalR[int] = epics_signal_r(int, f"{dae_prefix}NUMTIMECHANNELS")
        self.num_spectra: SignalR[int] = epics_signal_r(int, f"{dae_prefix}NUMSPECTRA")

        self.period = DaePeriod(dae_prefix)
        self.period_num: SignalRW = isis_epics_signal_rw(int, f"{dae_prefix}PERIOD")
        self.number_of_periods: SignalRW = isis_epics_signal_rw(int, f"{dae_prefix}NUMPERIODS")

        self.dae_settings = DaeSettings(dae_prefix)
        self.period_settings = DaePeriodSettings(dae_prefix)
        self.tcb_settings = DaeTCBSettings(dae_prefix)

        self.raw_spectra_integrals: SignalR[np.typing.NDArray[np.int32]] = epics_signal_r(
            np.typing.NDArray[np.int32], f"{dae_prefix}SPECINTEGRALS"
        )
        self.raw_spectra_data: SignalR[np.typing.NDArray[np.int32]] = epics_signal_r(
            np.typing.NDArray[np.int32], f"{dae_prefix}SPECDATA"
        )

        self.monitor = DaeMonitor(dae_prefix)
        self.event_mode = DaeEventMode(dae_prefix)

        self.beam_current: SignalR[float] = epics_signal_r(float, f"{dae_prefix}BEAMCURRENT")
        self.total_uamps: SignalR[float] = epics_signal_r(float, f"{dae_prefix}TOTALUAMPS")
        self.run_state: SignalR[RunstateEnum] = epics_signal_r(
            RunstateEnum, f"{dae_prefix}RUNSTATE"
        )
        self.title: SignalRW = isis_epics_signal_rw(str, f"{dae_prefix}TITLE")
        self.show_title_and_users: SignalRW = epics_signal_rw(
            bool, f"{dae_prefix}TITLE:DISPLAY", f"{dae_prefix}TITLE:DISPLAY"
        )

        self.users: SignalRW = isis_epics_signal_rw(str, f"{dae_prefix}_USERNAME")
        self.rb_number: SignalRW = isis_epics_signal_rw(str, f"{dae_prefix}_RBNUMBER")

        self.spectra_1_period_1 = DaeSpectra(dae_prefix, period=1, spectra=1)

        self.controls: DaeControls = DaeControls(dae_prefix)

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
        await self.controls.begin_run.trigger()
        await asyncio.sleep(2)  # This is a placeholder for the moment
        await self.controls.end_run.trigger(wait=True)
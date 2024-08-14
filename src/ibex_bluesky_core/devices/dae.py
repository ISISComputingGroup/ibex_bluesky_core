"""ophyd-async devices for communicating with the ISIS data acquisition electronics."""

import asyncio
from enum import Enum
import numpy as np
from bluesky.protocols import Triggerable
from ophyd_async.core import AsyncStatus, SignalR, SignalX, StandardReadable, ConfigSignal, SignalRW
from ophyd_async.epics.signal import epics_signal_r, epics_signal_x

from ibex_bluesky_core.devices.dae_controls import DaeControls
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
    CHANGING = "CHANGING"

    def __str__(self):
        return str(self.value)


class Dae(
    StandardReadable, Triggerable
):
    """Device representing the ISIS data acquisition electronics."""

    def __init__(self, prefix: str, name: str = "DAE") -> None:
        """Create a new Dae ophyd-async device."""
        dae_prefix = f"{prefix}DAE:"
        with self.add_children_as_readables():
            self.good_uah: SignalR[float] = epics_signal_r(float, f"{dae_prefix}GOODUAH")
            self.count_rate: SignalR[float] = epics_signal_r(float, f"{dae_prefix}COUNTRATE")
            self.m_events: SignalR[float] = epics_signal_r(float, f"{dae_prefix}MEVENTS")
            self.sim_mode : SignalR[bool] = epics_signal_r(bool, f"{dae_prefix}SIM_MODE")

            self.neutron_proton_ratio: SignalR[float] = epics_signal_r(float, f"{dae_prefix}NPRATIO")
            self.good_frames: SignalR[int] = epics_signal_r(int, f"{dae_prefix}GOODFRAMES")
            self.raw_frames: SignalR[int] = epics_signal_r(int, f"{dae_prefix}RAWFRAMES")
            self.total_counts: SignalR[int] = epics_signal_r(int, f"{dae_prefix}TOTALCOUNTS")

            self.period_good_frames: SignalR[int] = epics_signal_r(
                int, f"{dae_prefix}GOODFRAMES_PD"
            )
            self.run_number: SignalR[int] = epics_signal_r(int, f"{dae_prefix}IRUNNUMBER")
            self.run_number_str: SignalR[str] = epics_signal_r(str, f"{dae_prefix}RUNNUMBER")

            self.cycle_number: SignalR[str] = epics_signal_r(str, f"{dae_prefix}ISISCYCLE")

            self.inst_name: SignalR[str] = epics_signal_r(str, f"{dae_prefix}INSTNAME")
            self.run_start_time: SignalR[str] = epics_signal_r(str, f"{dae_prefix}STARTTIME")
            self.run_duration: SignalR[int] = epics_signal_r(int, f"{dae_prefix}RUNDURATION")
            self.num_time_channels: SignalR[int] = epics_signal_r(int, f"{dae_prefix}NUMTIMECHANNELS")
            self.num_spectra: SignalR[int] = epics_signal_r(int, f"{dae_prefix}NUMSPECTRA")

            # TODO move this out to subdevice?
            self.period_run_duration: SignalR[int] = epics_signal_r(int, f"{dae_prefix}RUNDURATION_PD")
            self.period_good_frames: SignalR[int] = epics_signal_r(int, f"{dae_prefix}GOODFRAMES_PD")
            self.period_raw_frames: SignalR[int] = epics_signal_r(int, f"{dae_prefix}RAWFRAMES_PD")
            self.period_good_uah: SignalR[float] = epics_signal_r(float, f"{dae_prefix}GOODUAH_PD")
            self.period_type: SignalR[str] = epics_signal_r(str, f"{dae_prefix}PERIODTYPE")
            self.period_sequence: SignalR[int] = epics_signal_r(int, f"{dae_prefix}PERIODSEQ")

            # TODO hmm are we only going to show 1 of these or more?
            # TODO move this out to subdevice?
            self.monitor_spectrum: SignalR[int] = epics_signal_r(int, f"{dae_prefix}MONITORCOUNTS")
            self.monitor_counts: SignalR[int] = epics_signal_r(int, f"{dae_prefix}MONITORSPECTRUM")
            self.monitor_to: SignalR[float] = epics_signal_r(float, f"{dae_prefix}MONITORTO")
            self.monitor_from: SignalR[float] = epics_signal_r(float, f"{dae_prefix}MONITORFROM")

            # TODO move this out to subdevice?
            self.event_mode_fraction: SignalR[float] = epics_signal_r(float, f"{dae_prefix}EVENTMODEFRACTION")
            self.event_mode_buf_used: SignalR[float] = epics_signal_r(float, f"{dae_prefix}EVENTMODEBUFUSED")
            self.event_mode_file_size: SignalR[float] = epics_signal_r(float, f"{dae_prefix}EVENTMODEFILEMB")
            self.event_mode_data_rate: SignalR[float] = epics_signal_r(float, f"{dae_prefix}EVENTMODEDATARATE")

            self.beam_current: SignalR[float] = epics_signal_r(float, f"{dae_prefix}BEAMCURRENT")
            self.total_uamps: SignalR[float] = epics_signal_r(float, f"{dae_prefix}TOTALUAMPS")

            self.run_state: SignalR[RunstateEnum] = epics_signal_r(
                RunstateEnum, f"{dae_prefix}RUNSTATE"
            )

            self.title: SignalRW = isis_epics_signal_rw(str, f"{dae_prefix}TITLE")
            self.show_title_and_users: SignalRW = isis_epics_signal_rw(bool, f"{dae_prefix}TITLE:DISPLAY")
            self.users: SignalRW = isis_epics_signal_rw(str, f"{dae_prefix}_USERNAME")
            self.rb_number: SignalRW = isis_epics_signal_rw(str, f"{dae_prefix}_RBNUMBER")

            # TODO move these out to period subdevice
            self.period_num: SignalRW = isis_epics_signal_rw(int, f"{dae_prefix}PERIOD")
            self.number_of_periods: SignalRW = isis_epics_signal_rw(int, f"{dae_prefix}NUMPERIODS")

            self.spectra_1_period_1_x: SignalR[np.typing.NDArray[np.float32]] = epics_signal_r(
                np.typing.NDArray[np.float32], f"{prefix}DAE" f":SPEC:1:1:X"
            )

        with self.add_children_as_readables(ConfigSignal):
            # add configurable pvs here ie. wiring tables, spectra number, etc. - stuff that'll change the shape of
            # other signals self.

            pass

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
        # await self.begin_run.trigger(wait=True)
        # await asyncio.sleep(2)  # This is a placeholder for the moment
        # await self.end_run.trigger(wait=True)

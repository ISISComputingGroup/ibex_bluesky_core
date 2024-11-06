"""ophyd-async devices for communicating with the ISIS data acquisition electronics."""

from enum import Enum

from numpy import int32
from numpy.typing import NDArray
from ophyd_async.core import SignalR, SignalRW, StandardReadable
from ophyd_async.epics.signal import epics_signal_r, epics_signal_rw

from ibex_bluesky_core.devices import isis_epics_signal_rw
from ibex_bluesky_core.devices.dae.dae_controls import DaeControls
from ibex_bluesky_core.devices.dae.dae_event_mode import DaeEventMode
from ibex_bluesky_core.devices.dae.dae_monitor import DaeMonitor
from ibex_bluesky_core.devices.dae.dae_period import DaePeriod
from ibex_bluesky_core.devices.dae.dae_period_settings import DaePeriodSettings
from ibex_bluesky_core.devices.dae.dae_settings import DaeSettings
from ibex_bluesky_core.devices.dae.dae_spectra import DaeSpectra
from ibex_bluesky_core.devices.dae.dae_tcb_settings import DaeTCBSettings


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


class Dae(StandardReadable):
    """Device representing the ISIS data acquisition electronics."""

    def __init__(self, prefix: str, name: str = "DAE") -> None:
        """Create a new Dae ophyd-async device."""
        dae_prefix = f"{prefix}DAE:"
        self._prefix = prefix
        self.good_uah: SignalR[float] = epics_signal_r(float, f"{dae_prefix}GOODUAH")
        self.count_rate: SignalR[float] = epics_signal_r(float, f"{dae_prefix}COUNTRATE")
        self.m_events: SignalR[float] = epics_signal_r(float, f"{dae_prefix}MEVENTS")
        self.sim_mode: SignalR[bool] = epics_signal_r(bool, f"{dae_prefix}SIM_MODE")
        self.neutron_proton_ratio: SignalR[float] = epics_signal_r(float, f"{dae_prefix}NPRATIO")
        self.good_frames: SignalR[int] = epics_signal_r(int, f"{dae_prefix}GOODFRAMES")
        self.raw_frames: SignalR[int] = epics_signal_r(int, f"{dae_prefix}RAWFRAMES")
        self.total_counts: SignalR[int] = epics_signal_r(int, f"{dae_prefix}TOTALCOUNTS")

        # Beware that this increments just after a run is ended. So it is generally not correct to
        # read this just after a DAE run has been ended().
        self.current_or_next_run_number: SignalR[int] = epics_signal_r(
            int, f"{dae_prefix}IRUNNUMBER"
        )
        self.current_or_next_run_number_str: SignalR[str] = epics_signal_r(
            str, f"{dae_prefix}RUNNUMBER"
        )

        self.cycle_number: SignalR[str] = epics_signal_r(str, f"{dae_prefix}ISISCYCLE")
        self.inst_name: SignalR[str] = epics_signal_r(str, f"{dae_prefix}INSTNAME")
        self.run_start_time: SignalR[str] = epics_signal_r(str, f"{dae_prefix}STARTTIME")
        self.run_duration: SignalR[int] = epics_signal_r(int, f"{dae_prefix}RUNDURATION")
        self.num_time_channels: SignalR[int] = epics_signal_r(int, f"{dae_prefix}NUMTIMECHANNELS")
        self.num_spectra: SignalR[int] = epics_signal_r(int, f"{dae_prefix}NUMSPECTRA")

        self.period = DaePeriod(dae_prefix)
        self.period_num: SignalRW[int] = isis_epics_signal_rw(int, f"{dae_prefix}PERIOD")
        self.number_of_periods: SignalRW[int] = isis_epics_signal_rw(int, f"{dae_prefix}NUMPERIODS")

        self.dae_settings = DaeSettings(dae_prefix)
        self.period_settings = DaePeriodSettings(dae_prefix)
        self.tcb_settings = DaeTCBSettings(dae_prefix)

        self.raw_spectra_integrals: SignalR[NDArray[int32]] = epics_signal_r(
            NDArray[int32], f"{dae_prefix}SPECINTEGRALS"
        )
        self.raw_spectra_data: SignalR[NDArray[int32]] = epics_signal_r(
            NDArray[int32], f"{dae_prefix}SPECDATA"
        )

        self.monitor = DaeMonitor(dae_prefix)
        self.event_mode = DaeEventMode(dae_prefix)

        self.beam_current: SignalR[float] = epics_signal_r(float, f"{dae_prefix}BEAMCURRENT")
        self.total_uamps: SignalR[float] = epics_signal_r(float, f"{dae_prefix}TOTALUAMPS")
        self.run_state: SignalR[RunstateEnum] = epics_signal_r(
            RunstateEnum, f"{dae_prefix}RUNSTATE"
        )
        self.title: SignalRW[str] = isis_epics_signal_rw(str, f"{dae_prefix}TITLE")
        self.show_title_and_users: SignalRW[bool] = epics_signal_rw(
            bool, f"{dae_prefix}TITLE:DISPLAY", f"{dae_prefix}TITLE:DISPLAY"
        )

        self.users: SignalRW[str] = isis_epics_signal_rw(str, f"{dae_prefix}_USERNAME")
        self.rb_number: SignalRW[str] = isis_epics_signal_rw(str, f"{dae_prefix}_RBNUMBER")

        self.spectra_1_period_1 = DaeSpectra(dae_prefix, period=1, spectra=1)

        self.controls: DaeControls = DaeControls(dae_prefix)

        super().__init__(name=name)

    def __repr__(self) -> str:
        """Get string representation of this class for debugging."""
        return f"{self.__class__.__name__}(name={self.name}, prefix={self._prefix})"

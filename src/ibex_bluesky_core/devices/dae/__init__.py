"""Utilities for the DAE device - mostly XML helpers."""

from typing import Generic, TypeVar

from bluesky.protocols import Movable
from numpy import int32
from ophyd_async.core import (
    Array1D,
    AsyncStatus,
    SignalDatatype,
    SignalR,
    SignalRW,
    SignalW,
    StandardReadable,
    StandardReadableFormat,
    StrictEnum,
)
from ophyd_async.epics.core import epics_signal_r, epics_signal_rw, epics_signal_w

from ibex_bluesky_core.devices import isis_epics_signal_rw
from ibex_bluesky_core.devices.dae._controls import BeginRunEx, BeginRunExBits, DaeControls
from ibex_bluesky_core.devices.dae._event_mode import DaeEventMode
from ibex_bluesky_core.devices.dae._monitor import DaeMonitor
from ibex_bluesky_core.devices.dae._period import DaePeriod
from ibex_bluesky_core.devices.dae._period_settings import (
    DaePeriodSettings,
    DaePeriodSettingsData,
    PeriodSource,
    PeriodType,
    SinglePeriodSettings,
)
from ibex_bluesky_core.devices.dae._settings import DaeSettings, DaeSettingsData, DaeTimingSource
from ibex_bluesky_core.devices.dae._spectra import DaeSpectra
from ibex_bluesky_core.devices.dae._tcb_settings import (
    DaeTCBSettings,
    DaeTCBSettingsData,
    TCBCalculationMethod,
    TCBTimeUnit,
    TimeRegime,
    TimeRegimeMode,
    TimeRegimeRow,
)

__all__ = [
    "BeginRunEx",
    "BeginRunExBits",
    "Dae",
    "DaeCheckingSignal",
    "DaeControls",
    "DaeEventMode",
    "DaeMonitor",
    "DaePeriod",
    "DaePeriodSettings",
    "DaePeriodSettingsData",
    "DaeSettings",
    "DaeSettingsData",
    "DaeSpectra",
    "DaeTCBSettings",
    "DaeTCBSettingsData",
    "DaeTimingSource",
    "PeriodSource",
    "PeriodType",
    "RunstateEnum",
    "SinglePeriodSettings",
    "TCBCalculationMethod",
    "TCBTimeUnit",
    "TimeRegime",
    "TimeRegimeMode",
    "TimeRegimeRow",
]

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


class RunstateEnum(StrictEnum):
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
        self.number_of_periods: DaeCheckingSignal[int] = DaeCheckingSignal(
            int, f"{dae_prefix}NUMPERIODS"
        )

        self.dae_settings = DaeSettings(dae_prefix)
        self.period_settings = DaePeriodSettings(dae_prefix)
        self.tcb_settings = DaeTCBSettings(dae_prefix)

        self.raw_spectra_integrals: SignalR[Array1D[int32]] = epics_signal_r(
            Array1D[int32], f"{dae_prefix}SPECINTEGRALS"
        )
        self.raw_spectra_integrals_nord: SignalR[int] = epics_signal_r(
            int, f"{dae_prefix}SPECINTEGRALS.NORD"
        )

        self.raw_spec_data: SignalR[Array1D[int32]] = epics_signal_r(
            Array1D[int32], f"{dae_prefix}SPECDATA"
        )
        self.raw_spec_data_proc: SignalW[int] = epics_signal_w(int, f"{dae_prefix}SPECDATA.PROC")
        self.raw_spec_data_nord: SignalR[int] = epics_signal_r(int, f"{dae_prefix}SPECDATA.NORD")

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

        self.controls: DaeControls = DaeControls(dae_prefix)

        super().__init__(name=name)

    def __repr__(self) -> str:
        """Get string representation of this class for debugging."""
        return f"{self.__class__.__name__}(name={self.name}, prefix={self._prefix})"

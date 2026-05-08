"""ophyd-async devices and utilities for a DAE period."""

from ophyd_async.core import SignalR, StandardReadable
from ophyd_async.epics.core import epics_signal_r


class DaePeriod(StandardReadable):
    """Subdevice for the current DAE period."""

    def __init__(self, dae_prefix: str, name: str = "") -> None:
        """DAE statistics and diagnostics for the current DAE period."""
        self.run_duration: SignalR[int] = epics_signal_r(int, f"{dae_prefix}RUNDURATION_PD")
        """Run duration (seconds) in the current DAE period."""
        self.good_frames: SignalR[int] = epics_signal_r(int, f"{dae_prefix}GOODFRAMES_PD")
        """DAE good frames in the current DAE period."""
        self.raw_frames: SignalR[int] = epics_signal_r(int, f"{dae_prefix}RAWFRAMES_PD")
        """DAE raw frames in the current DAE period."""
        self.good_uah: SignalR[float] = epics_signal_r(float, f"{dae_prefix}GOODUAH_PD")
        """DAE good uAh in the current DAE period."""
        self.type: SignalR[str] = epics_signal_r(str, f"{dae_prefix}PERIODTYPE")
        """DAE period type."""
        self.sequence: SignalR[int] = epics_signal_r(int, f"{dae_prefix}PERIODSEQ")
        """DAE period sequence."""

        super().__init__(name=name)

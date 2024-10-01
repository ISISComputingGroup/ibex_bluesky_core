"""ophyd-async devices and utilities for a DAE period."""

from ophyd_async.core import SignalR, StandardReadable
from ophyd_async.epics.signal import epics_signal_r


class DaePeriod(StandardReadable):
    """Subdevice for the current DAE period."""

    def __init__(self, dae_prefix: str, name: str = "") -> None:
        """Set up signals for the current DAE period."""
        self.run_duration: SignalR[int] = epics_signal_r(int, f"{dae_prefix}RUNDURATION_PD")
        self.good_frames: SignalR[int] = epics_signal_r(int, f"{dae_prefix}GOODFRAMES_PD")
        self.raw_frames: SignalR[int] = epics_signal_r(int, f"{dae_prefix}RAWFRAMES_PD")
        self.good_uah: SignalR[float] = epics_signal_r(float, f"{dae_prefix}GOODUAH_PD")
        self.type: SignalR[str] = epics_signal_r(str, f"{dae_prefix}PERIODTYPE")
        self.sequence: SignalR[int] = epics_signal_r(int, f"{dae_prefix}PERIODSEQ")

        super().__init__(name=name)

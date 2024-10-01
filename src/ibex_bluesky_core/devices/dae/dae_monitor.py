"""ophyd-async devices and utilities for a DAE monitor."""

from ophyd_async.core import SignalR, StandardReadable
from ophyd_async.epics.signal import epics_signal_r


class DaeMonitor(StandardReadable):
    """Subdevice for the current monitor."""

    def __init__(self, dae_prefix: str, name: str = "") -> None:
        """Set up signals for the current DAE monitor."""
        self.spectrum: SignalR[int] = epics_signal_r(int, f"{dae_prefix}MONITORCOUNTS")
        self.counts: SignalR[int] = epics_signal_r(int, f"{dae_prefix}MONITORSPECTRUM")
        self.to: SignalR[float] = epics_signal_r(float, f"{dae_prefix}MONITORTO")
        self.from_: SignalR[float] = epics_signal_r(float, f"{dae_prefix}MONITORFROM")

        super().__init__(name=name)

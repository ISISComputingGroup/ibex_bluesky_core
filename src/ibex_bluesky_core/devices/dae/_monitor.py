"""ophyd-async devices and utilities for a DAE monitor."""

from ophyd_async.core import SignalR, StandardReadable
from ophyd_async.epics.core import epics_signal_r


class DaeMonitor(StandardReadable):
    """Subdevice for the current monitor."""

    def __init__(self, dae_prefix: str, name: str = "") -> None:
        """DAE monitor statistics and diagnostics."""
        self.spectrum: SignalR[int] = epics_signal_r(int, f"{dae_prefix}MONITORSPECTRUM")
        """Monitor spectrum."""
        self.counts: SignalR[int] = epics_signal_r(int, f"{dae_prefix}MONITORCOUNTS")
        """Monitor counts."""
        self.to: SignalR[float] = epics_signal_r(float, f"{dae_prefix}MONITORTO")
        """Monitor integration upper bound (us)."""
        self.from_: SignalR[float] = epics_signal_r(float, f"{dae_prefix}MONITORFROM")
        """Monitor integration lower bound (us)."""

        super().__init__(name=name)

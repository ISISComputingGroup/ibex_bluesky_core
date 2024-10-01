"""ophyd-async devices and utilities for the DAE event mode statistics."""

from ophyd_async.core import SignalR, StandardReadable
from ophyd_async.epics.signal import epics_signal_r


class DaeEventMode(StandardReadable):
    """Subdevice for event mode statistics."""

    def __init__(self, dae_prefix: str, name: str = "") -> None:
        """Set up signals for DAE event mode statistics."""
        self.fraction: SignalR[float] = epics_signal_r(float, f"{dae_prefix}EVENTMODEFRACTION")
        self.buf_used: SignalR[float] = epics_signal_r(float, f"{dae_prefix}EVENTMODEBUFUSED")
        self.file_size: SignalR[float] = epics_signal_r(float, f"{dae_prefix}EVENTMODEFILEMB")
        self.data_rate: SignalR[float] = epics_signal_r(float, f"{dae_prefix}EVENTMODEDATARATE")
        super().__init__(name=name)

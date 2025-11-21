"""ophyd-async devices and utilities for the DAE event mode statistics."""

from ophyd_async.core import SignalR, StandardReadable
from ophyd_async.epics.core import epics_signal_r


class DaeEventMode(StandardReadable):
    """Subdevice for event mode statistics."""

    def __init__(self, dae_prefix: str, name: str = "") -> None:
        """DAE event mode statistics."""
        self.fraction: SignalR[float] = epics_signal_r(float, f"{dae_prefix}EVENTMODEFRACTION")
        """
        Event mode fraction.

        1 is full event mode, 0 is full histogram mode. Values between 0 and 1 imply that
        some spectra are in event mode and others are in histogram mode.
        """
        self.buf_used: SignalR[float] = epics_signal_r(float, f"{dae_prefix}EVENTMODEBUFUSED")
        """
        Event mode buffer used fraction.
        """
        self.file_size: SignalR[float] = epics_signal_r(float, f"{dae_prefix}EVENTMODEFILEMB")
        """
        Event mode file size (MB).
        """
        self.data_rate: SignalR[float] = epics_signal_r(float, f"{dae_prefix}EVENTMODEDATARATE")
        """
        Event mode data rate (MB/s).
        """
        super().__init__(name=name)

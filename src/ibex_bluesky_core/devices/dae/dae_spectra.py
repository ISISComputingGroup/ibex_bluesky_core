"""ophyd-async devices and utilities for a single DAE spectra."""

from numpy import float32
from numpy.typing import NDArray
from ophyd_async.core import SignalR, StandardReadable
from ophyd_async.epics.signal import epics_signal_r


class DaeSpectra(StandardReadable):
    """Subdevice for a single DAE spectra."""

    def __init__(self, dae_prefix: str, *, spectra: int, period: int, name: str = "") -> None:
        """Set up signals for a single DAE spectra."""
        self.x: SignalR[NDArray[float32]] = epics_signal_r(
            NDArray[float32], f"{dae_prefix}SPEC:{period}:{spectra}:X"
        )
        self.y: SignalR[NDArray[float32]] = epics_signal_r(
            NDArray[float32], f"{dae_prefix}SPEC:{period}:{spectra}:Y"
        )
        self.yc: SignalR[NDArray[float32]] = epics_signal_r(
            NDArray[float32], f"{dae_prefix}SPEC:{period}:{spectra}:YC"
        )
        super().__init__(name=name)

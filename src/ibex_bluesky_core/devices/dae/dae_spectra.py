"""ophyd-async devices and utilities for a single DAE spectra."""

from numpy import float32
from numpy.typing import NDArray
from ophyd_async.core import SignalR, StandardReadable
from ophyd_async.epics.signal import epics_signal_r


class DaeSpectra(StandardReadable):
    """Subdevice for a single DAE spectra."""

    def __init__(self, dae_prefix: str, *, spectra: int, period: int, name: str = "") -> None:
        """Set up signals for a single DAE spectra."""
        # x-axis; time-of-flight.
        self.tof: SignalR[NDArray[float32]] = epics_signal_r(
            NDArray[float32], f"{dae_prefix}SPEC:{period}:{spectra}:X"
        )

        # y-axis; counts / tof
        # This is the number of counts in a ToF bin, normalized by the width of
        # that ToF bin.
        # - Unsuitable for summing counts directly.
        # - Will give a continuous plot for non-uniform bin sizes.
        self.counts_per_time: SignalR[NDArray[float32]] = epics_signal_r(
            NDArray[float32], f"{dae_prefix}SPEC:{period}:{spectra}:Y"
        )

        # y-axis; counts
        # This is unnormalized number of counts per ToF bin.
        # - Suitable for summing counts
        # - This will give a discontinuous plot for non-uniform bin sizes.
        self.counts: SignalR[NDArray[float32]] = epics_signal_r(
            NDArray[float32], f"{dae_prefix}SPEC:{period}:{spectra}:YC"
        )
        super().__init__(name=name)

"""ophyd-async devices and utilities for a single DAE spectra."""

import asyncio

from numpy import float32
from numpy.typing import NDArray
from ophyd_async.core import SignalR, StandardReadable
from ophyd_async.epics.signal import epics_signal_r


class DaeSpectra(StandardReadable):
    """Subdevice for a single DAE spectra."""

    def __init__(self, dae_prefix: str, *, spectra: int, period: int, name: str = "") -> None:
        """Set up signals for a single DAE spectra."""
        # x-axis; time-of-flight.
        # These are bin-centre coordinates.
        self.tof: SignalR[NDArray[float32]] = epics_signal_r(
            NDArray[float32], f"{dae_prefix}SPEC:{period}:{spectra}:X"
        )
        self.tof_size: SignalR[int] = epics_signal_r(
            int, f"{dae_prefix}SPEC:{period}:{spectra}:X.NORD"
        )

        # y-axis; counts / tof
        # This is the number of counts in a ToF bin, normalized by the width of
        # that ToF bin.
        # - Unsuitable for summing counts directly.
        # - Will give a continuous plot for non-uniform bin sizes.
        self.counts_per_time: SignalR[NDArray[float32]] = epics_signal_r(
            NDArray[float32], f"{dae_prefix}SPEC:{period}:{spectra}:Y"
        )
        self.counts_per_time_size: SignalR[int] = epics_signal_r(
            int, f"{dae_prefix}SPEC:{period}:{spectra}:Y.NORD"
        )

        # y-axis; counts
        # This is unnormalized number of counts per ToF bin.
        # - Suitable for summing counts
        # - This will give a discontinuous plot for non-uniform bin sizes.
        self.counts: SignalR[NDArray[float32]] = epics_signal_r(
            NDArray[float32], f"{dae_prefix}SPEC:{period}:{spectra}:YC"
        )
        self.counts_size: SignalR[int] = epics_signal_r(
            int, f"{dae_prefix}SPEC:{period}:{spectra}:YC.NORD"
        )

        super().__init__(name=name)

    async def _read_sized(
        self, array_signal: SignalR[NDArray[float32]], size_signal: SignalR[int]
    ) -> NDArray[float32]:
        array, size = await asyncio.gather(array_signal.get_value(), size_signal.get_value())
        return array[:size]

    async def read_tof(self) -> NDArray[float32]:
        """Read a correctly-sized time-of-flight (x) array representing bin centres."""
        return await self._read_sized(self.tof, self.tof_size)

    async def read_counts(self) -> NDArray[float32]:
        """Read a correctly-sized array of counts."""
        return await self._read_sized(self.counts, self.counts_size)

    async def read_counts_per_time(self) -> NDArray[float32]:
        """Read a correctly-sized array of counts divided by bin width."""
        return await self._read_sized(self.counts_per_time, self.counts_per_time_size)

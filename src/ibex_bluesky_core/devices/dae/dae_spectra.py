"""ophyd-async devices and utilities for a single DAE spectra."""

import asyncio
import logging

import scipp as sc
from event_model.documents.event_descriptor import DataKey
from numpy import float32
from numpy.typing import NDArray
from ophyd_async.core import SignalR, StandardReadable
from ophyd_async.epics.signal import epics_signal_r

VARIANCE_ADDITION = 0.5
logger = logging.getLogger(__name__)


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

        # x-axis; time-of-flight.
        # These are bin-edge coordinates, with a size one more than the corresponding data.
        self.tof_edges: SignalR[NDArray[float32]] = epics_signal_r(
            NDArray[float32], f"{dae_prefix}SPEC:{period}:{spectra}:XE"
        )
        self.tof_edges_size: SignalR[int] = epics_signal_r(
            int, f"{dae_prefix}SPEC:{period}:{spectra}:XE.NORD"
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

    async def read_tof_edges(self) -> NDArray[float32]:
        """Read a correctly-sized time-of-flight (x) array representing bin edges."""
        return await self._read_sized(self.tof_edges, self.tof_edges_size)

    async def read_counts(self) -> NDArray[float32]:
        """Read a correctly-sized array of counts."""
        return await self._read_sized(self.counts, self.counts_size)

    async def read_counts_per_time(self) -> NDArray[float32]:
        """Read a correctly-sized array of counts divided by bin width."""
        return await self._read_sized(self.counts_per_time, self.counts_per_time_size)

    async def read_spectrum_dataarray(self) -> sc.DataArray:
        """Get a scipp DataArray containing the current data from this spectrum.

        Variances are set to the counts - i.e. the standard deviation is sqrt(N), which is typical
        for counts data.

        Data is returned along dimension "tof", which has bin-edge coordinates and units set from
        the units of the underlying PVs.
        """
        logger.debug(
            "Reading spectrum dataarray backed by PVs edges=%s, counts=%s",
            self.tof_edges.source,
            self.counts.source,
        )
        tof_edges, tof_edges_descriptor, counts = await asyncio.gather(
            self.read_tof_edges(),
            self.tof_edges.describe(),
            self.read_counts(),
        )

        if tof_edges.size != counts.size + 1:
            raise ValueError(
                "Time-of-flight edges must have size one more than the data. "
                "You may be trying to read too many time channels. "
                f"Edges size was {tof_edges.size}, counts size was {counts.size}."
            )

        datakey: DataKey = tof_edges_descriptor[self.tof_edges.name]
        unit = datakey.get("units", None)
        if unit is None:
            raise ValueError("Could not determine engineering units of tof edges.")

        # See doc\architectural_decisions\005-variance-addition.md
        # for justfication of the VARIANCE_ADDITION to variances

        return sc.DataArray(
            data=sc.Variable(
                dims=["tof"],
                values=counts,
                variances=counts + VARIANCE_ADDITION,
                unit=sc.units.counts,
            ),
            coords={"tof": sc.array(dims=["tof"], values=tof_edges, unit=sc.Unit(unit))},
        )

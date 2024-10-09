"""ophyd-async devices and utilities for a single DAE spectra."""

import asyncio
from bluesky.protocols import Triggerable
import scipp as sc
import typing
import numpy as np
from event_model.documents.event_descriptor import DataKey
from numpy import float32
from numpy.typing import NDArray
from ophyd_async.core import SignalR, StandardReadable, soft_signal_r_and_setter, AsyncStageable, AsyncStatus
from ophyd_async.epics.signal import epics_signal_r


# def soft_signal_r_and_setter(
#     datatype: type[T] | None = None,
#     initial_value: T | None = None,
#     name: str = "",
#     units: str | None = None,
#     precision: int | None = None,
# ) -> tuple[SignalR[T], Callable[[T], None]]:
#     """Returns a tuple of a read-only Signal and a callable through
#     which the signal can be internally modified within the device.
#     May pass metadata, which are propagated into describe.
#     Use soft_signal_rw if you want a device that is externally modifiable
#     """
#     metadata = SignalMetadata(units=units, precision=precision)
#     backend = SoftSignalBackend(datatype, initial_value, metadata=metadata)
#     signal = SignalR(backend, name=name)

#     return (signal, backend.set_value, lambda u: metadata.units = u)


# def get_units(sig: SignalR[Any]) -> str:
#     pass


class DaeSpectra(StandardReadable, Triggerable):
    """Subdevice for a single DAE spectra."""


    def __init__(self, dae_prefix: str, *, spectra: int, period: int, name: str = "") -> None:
        """Set up signals for a single DAE spectra."""
        # x-axis; time-of-flight.
        # These are bin-centre coordinates.
        self._tof_raw: SignalR[NDArray[float32]] = epics_signal_r(
            NDArray[float32], f"{dae_prefix}SPEC:{period}:{spectra}:X"
        )
        self.tof_size: SignalR[int] = epics_signal_r(
            int, f"{dae_prefix}SPEC:{period}:{spectra}:X.NORD"
        )

        # x-axis; time-of-flight.
        # These are bin-edge coordinates, with a size one more than the corresponding data.
        self._tof_edges_raw: SignalR[NDArray[float32]] = epics_signal_r(
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
        self._counts_per_time_raw: SignalR[NDArray[float32]] = epics_signal_r(
            NDArray[float32], f"{dae_prefix}SPEC:{period}:{spectra}:Y"
        )
        self.counts_per_time_size: SignalR[int] = epics_signal_r(
            int, f"{dae_prefix}SPEC:{period}:{spectra}:Y.NORD"
        )

        # y-axis; counts
        # This is unnormalized number of counts per ToF bin.
        # - Suitable for summing counts
        # - This will give a discontinuous plot for non-uniform bin sizes.
        self._counts_raw: SignalR[NDArray[float32]] = epics_signal_r(
            NDArray[float32], f"{dae_prefix}SPEC:{period}:{spectra}:YC"
        )
        self.counts_size: SignalR[int] = epics_signal_r(
            int, f"{dae_prefix}SPEC:{period}:{spectra}:YC.NORD"
        )

        self.tof, self._tof_setter = soft_signal_r_and_setter(NDArray[float32], [])
        self.tof_edges, self._tof_edges_setter = soft_signal_r_and_setter(NDArray[float32], [])
        self.counts_per_time, self._counts_per_time_setter = soft_signal_r_and_setter(NDArray[float32], [])
        self.counts, self._counts_setter = soft_signal_r_and_setter(NDArray[float32], [])
        self.stddev, self._stddev_setter = soft_signal_r_and_setter(NDArray[float32], [])

        super().__init__(name=name)


    @AsyncStatus.wrap
    async def trigger(self) -> None:

        self._tof_setter(await self._read_sized(self._tof_raw, self.tof_size))
        self._tof_edges_setter(await self._read_sized(self._tof_edges_raw, self.tof_edges_size))
        self._counts_per_time_setter(await self._read_sized(self._counts_per_time_raw, self.counts_per_time_size))
        self._counts_setter(await self._read_sized(self._counts_raw, self.counts_size))

        stddev = await self.counts.get_value()
        self._stddev_setter(np.sqrt(stddev))
        

    async def _read_sized(
        self, array_signal: SignalR[NDArray[float32]], size_signal: SignalR[int]
    ) -> NDArray[float32]:
        array, size = await asyncio.gather(array_signal.get_value(), size_signal.get_value())
        return array[:size]

    async def read_tof(self) -> NDArray[float32]:
        """Read a correctly-sized time-of-flight (x) array representing bin centres."""
        tof = await self.tof.get_value()
        return typing.cast(NDArray[float32], tof)

    async def read_tof_edges(self) -> NDArray[float32]:
        """Read a correctly-sized time-of-flight (x) array representing bin edges."""
        tof_edges = await self.tof_edges.get_value()
        return typing.cast(NDArray[float32], tof_edges)

    async def read_counts(self) -> NDArray[float32]:
        """Read a correctly-sized array of counts."""
        counts = await self.counts.get_value()
        return typing.cast(NDArray[float32], counts)

    async def read_counts_per_time(self) -> NDArray[float32]:
        """Read a correctly-sized array of counts divided by bin width."""
        counts_per_time = await self.counts_per_time.get_value()
        return typing.cast(NDArray[float32], counts_per_time)
    
    async def read_counts_uncertainties(self) -> NDArray[float32]:
        """Read a correctly-sized array of uncertainties for each count."""
        stddev = await self.stddev.get_value()
        return typing.cast(NDArray[float32], stddev)

    async def read_spectrum_dataarray(self) -> sc.DataArray:
        """Get a scipp DataArray containing the current data from this spectrum.

        Variances are set to the counts - i.e. the standard deviation is sqrt(N), which is typical
        for counts data.

        Data is returned along dimension "tof", which has bin-edge coordinates and units set from
        the units of the underlying PVs.
        """
        tof_edges, tof_edges_descriptor, counts = await asyncio.gather(
            self.read_tof_edges(),
            self._tof_edges_raw.describe(),
            self.read_counts(),
        )

        if tof_edges.size != counts.size + 1:
            raise ValueError(
                "Time-of-flight edges must have size one more than the data. "
                "You may be trying to read too many time channels. "
                f"Edges size was {tof_edges.size}, counts size was {counts.size}."
            )

        datakey: DataKey = tof_edges_descriptor[self._tof_edges_raw.name]
        unit = datakey.get("units", None)
        if unit is None:
            raise ValueError("Could not determine engineering units of tof edges.")

        return sc.DataArray(
            data=sc.Variable(dims=["tof"], values=counts, variances=counts, unit=sc.units.counts),
            coords={"tof": sc.array(dims=["tof"], values=tof_edges, unit=sc.Unit(unit))},
        )

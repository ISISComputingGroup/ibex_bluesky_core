"""DAE data reduction strategies."""

import asyncio
import logging
import math
from abc import ABC, abstractmethod
from collections.abc import Awaitable, Callable, Collection, Sequence
from typing import TYPE_CHECKING

import numpy as np
import numpy.typing as npt
import scipp as sc
from ophyd_async.core import (
    Array1D,
    Device,
    DeviceVector,
    SignalR,
    StandardReadable,
    soft_signal_r_and_setter,
)
from scippneutron import conversion

from ibex_bluesky_core.devices.dae.dae_spectra import DaeSpectra
from ibex_bluesky_core.devices.simpledae.strategies import Reducer

logger = logging.getLogger(__name__)

if TYPE_CHECKING:
    from ibex_bluesky_core.devices.simpledae import SimpleDae


INTENSITY_PRECISION = 6


async def sum_spectra(spectra: Collection[DaeSpectra]) -> sc.Variable | sc.DataArray:
    """Read and sum a number of spectra from the DAE.

    Returns a scipp scalar, which has .value and .variance properties for accessing the sum
    and variance respectively of the summed counts.

    More info on scipp scalars can be found here: https://scipp.github.io/generated/functions/scipp.scalar.html
    """
    logger.info("Summing %d spectra using scipp", len(spectra))
    summed_counts = sc.scalar(value=0, unit=sc.units.counts, dtype="float64")
    for spec in asyncio.as_completed([s.read_spectrum_dataarray() for s in spectra]):
        summed_counts += (await spec).sum()
    logger.debug("Summed counts: %s", summed_counts)
    return summed_counts


def tof_bounded_spectra(
    bounds: sc.Variable,
) -> Callable[[Collection[DaeSpectra]], Awaitable[sc.Variable | sc.DataArray]]:
    """Sum a set of neutron spectra between the specified time of flight bounds.

    Args:
        bounds: A scipp array of size 2, no variances, unit of us,
            where the second element must be larger than the first.

    Returns a scipp scalar, which has .value and .variance properties for accessing the sum
    and variance respectively of the summed counts.

    More info on scipp arrays and scalars can be found here: https://scipp.github.io/generated/functions/scipp.scalar.html

    """
    bounds_value = 2
    if "tof" not in bounds.dims:
        raise ValueError("Should contain tof dims")
    if bounds.sizes["tof"] != bounds_value:
        raise ValueError("Should contain lower and upper bound")

    async def sum_spectra_with_tof(spectra: Collection[DaeSpectra]) -> sc.Variable | sc.DataArray:
        """Sum spectra bounded by a time of flight upper and lower bound."""
        summed_counts = sc.scalar(value=0, unit=sc.units.counts, dtype="float64")
        for spec in asyncio.as_completed([s.read_spectrum_dataarray() for s in spectra]):
            tof_bound_spectra = await spec
            summed_counts += tof_bound_spectra.rebin({"tof": bounds}).sum()
        return summed_counts

    return sum_spectra_with_tof


def wavelength_bounded_spectra(
    bounds: sc.Variable, total_flight_path_length: sc.Variable
) -> Callable[[Collection[DaeSpectra]], Awaitable[sc.Variable | sc.DataArray]]:
    """Sum a set of neutron spectra between the specified wavelength bounds.

    Args:
        bounds: A scipp array of size 2 of wavelength bounds, in units of angstrom,
            where the second element must be larger than the first.
        total_flight_path_length: A scipp scalar of Ltotal (total flight path length), the path
            length from neutron source to detector or monitor, in units of meters.

    Time of flight is converted to wavelength using scipp neutron's library function
        `wavelength_from_tof`, more info on which can be found here:
        https://scipp.github.io/scippneutron/generated/modules/scippneutron.conversion.tof.wavelength_from_tof.html

    Returns a scipp scalar, which has .value and .variance properties for accessing the sum
    and variance respectively of the summed counts.

    """
    bounds_value = 2

    if "tof" not in bounds.dims:
        raise ValueError("Should contain tof dims")
    if bounds.sizes["tof"] != bounds_value:
        raise ValueError("Should contain lower and upper bound")

    async def sum_spectra_with_wavelength(
        spectra: Collection[DaeSpectra],
    ) -> sc.Variable | sc.DataArray:
        """Sum a set of spectra between the specified wavelength bounds."""
        summed_counts = sc.scalar(value=0, unit=sc.units.counts, dtype="float64")
        for spec in asyncio.as_completed([s.read_spectrum_dataarray() for s in spectra]):
            wavelength_bounded_spectra = await spec
            wavelength_coord = conversion.tof.wavelength_from_tof(
                tof=wavelength_bounded_spectra.coords["tof"], Ltotal=total_flight_path_length
            )
            wavelength_bounded_spectra.coords["tof"] = wavelength_coord
            summed_counts += wavelength_bounded_spectra.rebin({"tof": bounds}).sum()
        return summed_counts

    return sum_spectra_with_wavelength


class ScalarNormalizer(Reducer, StandardReadable, ABC):
    """Sum a set of user-specified spectra, then normalize by a scalar signal."""

    def __init__(
        self,
        prefix: str,
        detector_spectra: Sequence[int],
        sum_detector: Callable[
            [Collection[DaeSpectra]], Awaitable[sc.Variable | sc.DataArray]
        ] = sum_spectra,
    ) -> None:
        """Init.

        Args:
            prefix: the PV prefix of the instrument to get spectra from (e.g. IN:DEMO:)
            detector_spectra: a sequence of spectra numbers (detectors) to sum.
            sum_detector: takes spectra objects, reads from them, and returns a scipp scalar
                describing the detector intensity. Defaults to summing over the entire spectrum.

        """
        self.detectors = DeviceVector(
            {
                i: DaeSpectra(dae_prefix=prefix + "DAE:", spectra=i, period=0)
                for i in detector_spectra
            }
        )

        self.det_counts, self._det_counts_setter = soft_signal_r_and_setter(float, 0.0)
        self.intensity, self._intensity_setter = soft_signal_r_and_setter(
            float, 0.0, precision=INTENSITY_PRECISION
        )

        self.det_counts_stddev, self._det_counts_stddev_setter = soft_signal_r_and_setter(
            float, 0.0
        )
        self.intensity_stddev, self._intensity_stddev_setter = soft_signal_r_and_setter(
            float, 0.0, precision=INTENSITY_PRECISION
        )
        self.sum_detector = sum_detector

        super().__init__(name="")

    @abstractmethod
    def denominator(self, dae: "SimpleDae") -> SignalR[int] | SignalR[float]:
        """Get the normalization denominator, which is assumed to be a scalar signal."""

    async def reduce_data(self, dae: "SimpleDae") -> None:
        """Apply the normalization."""
        logger.info("starting reduction")
        summed_counts, denominator = await asyncio.gather(
            self.sum_detector(self.detectors.values()), self.denominator(dae).get_value()
        )

        self._det_counts_setter(float(summed_counts.value))

        if denominator == 0.0:  # To avoid zero division
            self._intensity_setter(0.0)
            intensity_var = 0.0
        else:
            intensity = summed_counts / denominator
            self._intensity_setter(intensity.value)
            intensity_var = intensity.variance if intensity.variance is not None else 0.0

        detector_counts_var = 0.0 if summed_counts.variance is None else summed_counts.variance

        self._det_counts_stddev_setter(math.sqrt(detector_counts_var))
        self._intensity_stddev_setter(math.sqrt(intensity_var))
        logger.info("reduction complete")

    def additional_readable_signals(self, dae: "SimpleDae") -> list[Device]:
        """Publish interesting signals derived or used by this reducer."""
        return [
            self.det_counts,
            self.intensity,
            self.denominator(dae),
            self.det_counts_stddev,
            self.intensity_stddev,
        ]


class PeriodGoodFramesNormalizer(ScalarNormalizer):
    """Sum a set of user-specified spectra, then normalize by period good frames."""

    def denominator(self, dae: "SimpleDae") -> SignalR[int]:
        """Get normalization denominator (period good frames)."""
        return dae.period.good_frames


class GoodFramesNormalizer(ScalarNormalizer):
    """Sum a set of user-specified spectra, then normalize by total good frames."""

    def denominator(self, dae: "SimpleDae") -> SignalR[int]:
        """Get normalization denominator (total good frames)."""
        return dae.good_frames


class MonitorNormalizer(Reducer, StandardReadable):
    """Normalize a set of user-specified detector spectra by user-specified monitor spectra."""

    def __init__(
        self,
        prefix: str,
        detector_spectra: Sequence[int],
        monitor_spectra: Sequence[int],
        sum_detector: Callable[
            [Collection[DaeSpectra]], Awaitable[sc.Variable | sc.DataArray]
        ] = sum_spectra,
        sum_monitor: Callable[
            [Collection[DaeSpectra]], Awaitable[sc.Variable | sc.DataArray]
        ] = sum_spectra,
    ) -> None:
        """Init.

        Args:
            prefix: the PV prefix of the instrument to get spectra from (e.g. IN:DEMO:)
            detector_spectra: a sequence of spectra numbers (detectors) to sum.
            monitor_spectra: a sequence of spectra number (monitors) to sum and normalize by.
            sum_detector: takes spectra objects, reads from them, and returns a scipp scalar
                describing the detector intensity. Defaults to summing over the entire spectrum.
            sum_monitor: takes spectra objects, reads from them, and returns a scipp scalar
                describing the monitor intensity. Defaults to summing over the entire spectrum.

        Scipp scalars are described in further detail here: https://scipp.github.io/generated/functions/scipp.scalar.html

        """
        dae_prefix = prefix + "DAE:"
        self.detectors = DeviceVector(
            {i: DaeSpectra(dae_prefix=dae_prefix, spectra=i, period=0) for i in detector_spectra}
        )
        self.monitors = DeviceVector(
            {i: DaeSpectra(dae_prefix=dae_prefix, spectra=i, period=0) for i in monitor_spectra}
        )

        self.det_counts, self._det_counts_setter = soft_signal_r_and_setter(float, 0.0)
        self.mon_counts, self._mon_counts_setter = soft_signal_r_and_setter(float, 0.0)
        self.intensity, self._intensity_setter = soft_signal_r_and_setter(
            float, 0.0, precision=INTENSITY_PRECISION
        )

        self.det_counts_stddev, self._det_counts_stddev_setter = soft_signal_r_and_setter(
            float, 0.0
        )
        self.mon_counts_stddev, self._mon_counts_stddev_setter = soft_signal_r_and_setter(
            float, 0.0
        )
        self.intensity_stddev, self._intensity_stddev_setter = soft_signal_r_and_setter(
            float, 0.0, precision=INTENSITY_PRECISION
        )
        self.sum_detector = sum_detector
        self.sum_monitor = sum_monitor

        super().__init__(name="")

    async def reduce_data(self, dae: "SimpleDae") -> None:
        """Apply the normalization."""
        logger.info("starting reduction")
        detector_counts, monitor_counts = await asyncio.gather(
            self.sum_detector(self.detectors.values()),
            self.sum_monitor(self.monitors.values()),
        )

        if monitor_counts.value == 0.0:  # To avoid zero division
            self._intensity_setter(0.0)
            intensity_var = 0.0

        else:
            intensity = detector_counts / monitor_counts
            self._intensity_setter(float(intensity.value))
            intensity_var = intensity.variance if intensity.variance is not None else 0.0

        self._intensity_stddev_setter(math.sqrt(intensity_var))

        self._det_counts_setter(float(detector_counts.value))
        self._mon_counts_setter(float(monitor_counts.value))

        detector_counts_var = 0.0 if detector_counts.variance is None else detector_counts.variance
        monitor_counts_var = 0.0 if monitor_counts.variance is None else monitor_counts.variance

        self._det_counts_stddev_setter(math.sqrt(detector_counts_var))
        self._mon_counts_stddev_setter(math.sqrt(monitor_counts_var))
        logger.info("reduction complete")

    def additional_readable_signals(self, dae: "SimpleDae") -> list[Device]:
        """Publish interesting signals derived or used by this reducer."""
        return [
            self.det_counts,
            self.mon_counts,
            self.intensity,
            self.det_counts_stddev,
            self.mon_counts_stddev,
            self.intensity_stddev,
        ]


class PeriodSpecIntegralsReducer(Reducer, StandardReadable):
    """A DAE Reducer which simultaneously exposes integrals of many spectra in the current period.

    Two types of integrals are available: detectors and monitors. Other than defaults, their
    behaviour is identical. No normalization is performed in this reducer - exactly how the
    detector and monitor integrals are used is defined downstream.

    By itself, the data from this reducer is not suitable for use in a scan - but it provides
    raw data which may be useful for further processing as part of callbacks (e.g. LiveDispatchers).
    """

    def __init__(
        self,
        *,
        monitors: npt.NDArray[np.int64],
        detectors: npt.NDArray[np.int64],
    ) -> None:
        """Init.

        Args:
            monitors: an array representing the mapping of monitors to acquire integrals from.
                For example, passing np.array([1]) selects spectrum 1.
            detectors: an array representing the mapping of detectors to acquire integrals from.
                For example, passing np.array([5, 6, 7, 8]) would select detector spectra 5-8
                inclusive, and so the output of this reducer would be an array of dimension 4.

        """
        self._detectors = detectors
        self._monitors = monitors

        self.det_integrals, self._det_integrals_setter = soft_signal_r_and_setter(
            Array1D[np.int32], np.ndarray([], dtype=np.int32)
        )
        self.mon_integrals, self._mon_integrals_setter = soft_signal_r_and_setter(
            Array1D[np.int32], np.ndarray([], dtype=np.int32)
        )

        super().__init__(name="")

    @property
    def detectors(self) -> npt.NDArray[np.int64]:
        """Get the detectors used by this reducer."""
        return self._detectors

    @property
    def monitors(self) -> npt.NDArray[np.int64]:
        """Get the monitors used by this reducer."""
        return self._monitors

    async def _trigger_and_get_specdata(self, dae: "SimpleDae") -> npt.NDArray[np.int32]:
        await dae.controls.update_run.trigger()
        await dae.raw_spec_data_proc.set(1, wait=True)
        (raw_data, nord) = await asyncio.gather(
            dae.raw_spec_data.get_value(),
            dae.raw_spec_data_nord.get_value(),
        )
        return raw_data[:nord]

    async def reduce_data(self, dae: "SimpleDae") -> None:
        """Expose detector & monitor integrals.

        After this method returns, it is valid to read from det_integrals and
        mon_integrals.

        Note:
            Could use SPECINTEGRALS PV here, which seems more efficient initially,
            but it gets bounded by some areadetector settings under-the-hood which
            may be a bit surprising on some instruments.

            We can't just change these settings in this reducer, as they only apply
            to new events that come in.

        """
        logger.info("starting reduction")
        (
            raw_data,
            num_periods,
            num_spectra,
            num_time_channels,
            current_period,
        ) = await asyncio.gather(
            self._trigger_and_get_specdata(dae),
            dae.number_of_periods.signal.get_value(),
            dae.num_spectra.get_value(),
            dae.num_time_channels.get_value(),
            dae.period_num.get_value(),
        )

        # Raw data includes time channel 0, which contains "junk" data
        # This could potentially be useful for diagnostics, but is not useful as part of a scan.
        # So it gets unconditionally chopped out.
        # Spectrum 0 is also present. This is left so that passing detectors=[1] selects spectrum 1.
        raw_data = raw_data.reshape((num_periods, num_spectra + 1, num_time_channels + 1))
        all_current_period_data = raw_data[current_period - 1, :, 1:]

        # After this sum, we are left with a 1D array of size nspectra
        det_integrals = np.sum(all_current_period_data[self._detectors], axis=1)
        mon_integrals = np.sum(all_current_period_data[self._monitors], axis=1)

        self._det_integrals_setter(det_integrals)
        self._mon_integrals_setter(mon_integrals)

        logger.info("reduction complete")

    def additional_readable_signals(self, dae: "SimpleDae") -> list[Device]:
        """Publish interesting signals derived or used by this reducer."""
        return [
            self.mon_integrals,
            self.det_integrals,
        ]

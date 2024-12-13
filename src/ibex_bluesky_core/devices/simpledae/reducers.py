"""DAE data reduction strategies."""

import asyncio
import logging
import math
from abc import ABC, abstractmethod
from collections.abc import Awaitable, Collection, Sequence
from typing import TYPE_CHECKING, Callable

import scipp as sc
from ophyd_async.core import (
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

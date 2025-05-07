"""DAE data reduction strategies."""

import asyncio
import logging
import math
from abc import ABC, abstractmethod
from collections.abc import Awaitable, Callable, Collection, Sequence
from typing import TYPE_CHECKING
from bluesky.protocols import NamedMovable
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
import bluesky.plan_stubs as bps
from ibex_bluesky_core.devices.dae import DaeSpectra
from ibex_bluesky_core.devices.simpledae._strategies import Reducer

from devices.dae._spectra import PolarisationDevice, SpectraDevice

logger = logging.getLogger(__name__)

if TYPE_CHECKING:
    from ibex_bluesky_core.devices.simpledae import SimpleDae


INTENSITY_PRECISION = 6
VARIANCE_ADDITION = 0.5


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


def polarization(a: sc.Variable, b: sc.Variable) -> sc.Variable:
    """Calculate polarization value and propagate uncertainties.

    This function computes the polarization given by the formula (a-b)/(a+b)
    and propagates the uncertainties associated with a and b.

    Args:
        a: scipp Variable
        b: scipp Variable

    Returns:
        polarization_value: This quantity is calculated as (a-b)/(a+b)

    On SANS instruments e.g. LARMOR, A and B correspond to intensity in different DAE
    periods (before/after switching a flipper) and the output is interpreted as a neutron polarization ratio
    Or reflectometry instruments e.g. POLREF, the situation is the same as on LARMOR
    On muon instruments, A and B correspond to measuring from forward/backward detector banks, and the output is interpreted as a muon asymmetry

    """
    if a.unit != b.unit:
        raise ValueError("The units of a and b are not equivalent.")
    if a.sizes != b.sizes:
        raise ValueError("Dimensions/shape of a and b must match.")

    # This line allows for dims, units, and dtype to be handled by scipp
    polarization_value = (a - b) / (a + b)

    variances_a = a.variances
    variances_b = b.variances
    values_a = a.values
    values_b = b.values

    # Calculate partial derivatives
    partial_a = 2 * values_b / (values_a + values_b) ** 2
    partial_b = -2 * values_a / (values_a + values_b) ** 2

    variance_return = (partial_a**2 * variances_a) + (partial_b**2 * variances_b)

    # Propagate uncertainties
    polarization_value.variances = variance_return

    return polarization_value


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

        if denominator == 0.0:
            raise ValueError("Cannot normalize; denominator is zero. Check beamline configuration.")

        # See doc\architectural_decisions\005-variance-addition.md
        # for justification of this addition to variances.
        summed_counts.variance += VARIANCE_ADDITION

        intensity = summed_counts / denominator

        self._det_counts_setter(float(summed_counts.value))
        self._det_counts_stddev_setter(math.sqrt(summed_counts.variance))

        self._intensity_setter(intensity.value)
        self._intensity_stddev_setter(math.sqrt(intensity.variance))

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

        if monitor_counts.value == 0.0:
            raise ValueError(
                "Cannot normalize; got zero monitor counts. Check beamline configuration."
            )

        # See doc\architectural_decisions\005-variance-addition.md
        # for justification of this addition to variances.
        detector_counts.variance += VARIANCE_ADDITION

        intensity = detector_counts / monitor_counts

        self._intensity_setter(float(intensity.value))
        self._det_counts_setter(float(detector_counts.value))
        self._mon_counts_setter(float(monitor_counts.value))

        self._intensity_stddev_setter(math.sqrt(intensity.variance))
        self._det_counts_stddev_setter(math.sqrt(detector_counts.variance))
        self._mon_counts_stddev_setter(math.sqrt(monitor_counts.variance))

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


class WavelengthBoundedNormalizer(Reducer, StandardReadable):
    def __init__(
        self,
        prefix: str,
        detector_spectra: Sequence[int],
        monitor_spectra: Sequence[int],
        intervals: list[sc.Variable], 
        total_flight_path_length: sc.Variable
    ) -> None:
        
        self.total_flight_path_length = total_flight_path_length
        self.intervals = intervals

        dae_prefix = prefix + "DAE:"

        self.detectors = DeviceVector(
            {i: DaeSpectra(dae_prefix=dae_prefix, spectra=i, period=0) for i in detector_spectra}
        )
        self.monitors = DeviceVector(
            {i: DaeSpectra(dae_prefix=dae_prefix, spectra=i, period=0) for i in monitor_spectra}
        )

        self.spectra = DeviceVector(
            {i: SpectraDevice() for i in range(len(intervals))}
        )

        super().__init__(name="")

    async def reduce_data(self, dae: "SimpleDae") -> None:
        """Apply the normalisation."""
        logger.info("starting normalisation")

        for i in range(len(self.intervals)):

            interval = self.intervals[i]
            spectra = self.spectra[i]

            detector_counts_sc, monitor_counts_sc = await asyncio.gather(
                wavelength_bounded_spectra(bounds=interval, total_flight_path_length=self.total_flight_path_length)(self.detectors.values()),
                wavelength_bounded_spectra(bounds=interval, total_flight_path_length=self.total_flight_path_length)(self.monitors.values()),
            )

            if monitor_counts_sc.value == 0.0:
                raise ValueError(
                    "Cannot normalize; got zero monitor counts. Check beamline configuration."
                )

            # See doc\architectural_decisions\005-variance-addition.md
            # for justification of this addition to variances.
            detector_counts_sc.variance += VARIANCE_ADDITION
            intensity_sc = detector_counts_sc / monitor_counts_sc

            intensity = float(intensity_sc.value)
            det_counts = float(detector_counts_sc.value)
            mon_counts = float(monitor_counts_sc.value)

            intensity_stddev = math.sqrt(intensity_sc.variance)
            det_counts_stddev = math.sqrt(detector_counts_sc.variance)
            mon_counts_stddev = math.sqrt(monitor_counts_sc.variance)

            spectra.setter(det_counts=det_counts, det_counts_stddev=det_counts_stddev, mon_counts=mon_counts, mon_counts_stddev=mon_counts_stddev, intensity=intensity, intensity_stddev=intensity_stddev)

    def additional_readable_signals(self, dae: "SimpleDae") -> list[Device]:
        return self.spectra


class Polariser(Reducer, StandardReadable):
    def __init__(
        self,
        reducer_a: Reducer,
        reducer_b: Reducer,
        intervals: list[sc.Variable],
    ) -> None:
        
        self.reducer_a = reducer_a
        self.reducer_b = reducer_b
        self.intervals = intervals

        self.polarisation_devices = DeviceVector(
            {i: PolarisationDevice(intensity_precision=INTENSITY_PRECISION) for i in range(len(intervals))}
        )

    async def reduce_data(self, dae: "SimpleDae") -> None:
        """Apply the polarisation."""
        logger.info("starting polarisation")

        for i in range(len(self.intervals)):

            p_device = self.polarisation_devices[i]

            _intensity_a = await self.reducer_a.intensities[i].get_value()
            _intensity_b = await self.reducer_b.intensities[i].get_value()
            _intensity_a_stddev = await self.reducer_a.intensity_stddevs[i].get_value()
            _intensity_b_stddev = await self.reducer_b.intensity_stddevs[i].get_value()

            intensity_a_sc = sc.scalar(value=_intensity_a, variance=_intensity_a_stddev, dtype=float)
            intensity_b_sc = sc.scalar(value=_intensity_b, variance=_intensity_b_stddev, dtype=float)

            polarisation_sc = polarization(intensity_a_sc, intensity_b_sc)        
            polarisation_ratio_sc = intensity_a_sc / intensity_b_sc

            polarisation = float(polarisation_sc.value)
            polarisation_ratio = float(polarisation_ratio_sc.value)
            polarisation_stddev = float(polarisation_sc.variance)
            polarisation_ratio_stddev = float(polarisation_ratio_sc.variance)

            p_device.setter(polarisation=polarisation, polarisation_stddev=polarisation_stddev, polarisation_ratio=polarisation_ratio, polarisation_ratio_stddev=polarisation_ratio_stddev)
        
    def additional_readable_signals(self, dae: "SimpleDae") -> list[Device]:
        return self.polarisation_devices


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

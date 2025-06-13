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
from scippneutron.conversion.tof import dspacing_from_tof

from ibex_bluesky_core.devices.dae import DaeSpectra
from ibex_bluesky_core.devices.simpledae._strategies import Reducer

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
        bounds: A scipp :external+scipp:py:obj:`array <scipp.array>` of size 2, no variances, unit
            of us, where the second element must be larger than the first.


    :rtype:
        scipp :external+scipp:py:obj:`scalar <scipp.scalar>`
    Returns a scipp :external+scipp:py:obj:`scalar <scipp.scalar>`, which has .value and .variance
    properties for accessing the sum and variance respectively of the summed counts.

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
        bounds: A scipp :external+scipp:py:obj:`array <scipp.array>` of size 2 of wavelength bounds,
            in units of angstrom, where the second element must be larger than the first.
        total_flight_path_length: A scipp :external+scipp:py:obj:`scalar <scipp.scalar>` of Ltotal
            (total flight path length), the path length from neutron source to detector or monitor,
            in units of meters.

    :rtype:
        scipp :external+scipp:py:obj:`scalar <scipp.scalar>`

    Time of flight is converted to wavelength using scipp neutron's library function
    `wavelength_from_tof`, more info on which can be found here:
    :external+scippneutron:py:obj:`wavelength_from_tof
    <scippneutron.conversion.tof.wavelength_from_tof>`

    Returns a scipp :external+scipp:py:obj:`scalar <scipp.scalar>`, which has .value and .variance
    properties for accessing the sum and variance respectively of the summed counts.

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


def polarization(
    a: sc.Variable | sc.DataArray, b: sc.Variable | sc.DataArray
) -> sc.Variable | sc.DataArray:
    """Calculate polarization value and propagate uncertainties.

    This function computes the polarization given by the formula (a-b)/(a+b)
    and propagates the uncertainties associated with a and b.

    Args:
        a: scipp :external+scipp:py:obj:`Variable <scipp.Variable>`
            or :external+scipp:py:obj:`DataArray <scipp.DataArray>`
        b: scipp :external+scipp:py:obj:`Variable <scipp.Variable>`
            or :external+scipp:py:obj:`DataArray <scipp.DataArray>`

    :return:
        polarization_value: (a - b) / (a + b)

    :rtype:
        scipp :external+scipp:py:obj:`Variable <scipp.Variable>`
        or :external+scipp:py:obj:`DataArray <scipp.DataArray>`

    On SANS instruments e.g. LARMOR, A and B correspond to intensity in different DAE
    periods (before/after switching a flipper) and the output is interpreted as a neutron
    polarization ratio.
    On reflectometry instruments e.g. POLREF, the situation is the same as on LARMOR
    On muon instruments, A and B correspond to measuring from forward/backward detector
    banks, and the output is interpreted as a muon asymmetry.

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

        all_current_period_data = await dae.trigger_and_get_specdata()

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


class DSpacingMappingReducer(Reducer, StandardReadable):
    """A DAE Reducer which exposes an array of d-spacings at each scan point.

    This reducer produces one dimensional arrays of d-spacing, generated by
    converting the time-of-flight coordinates of each configured spectrum to
    d-spacing, rebinning all spectra to a common set of d-spacing bins, and
    then summing all spectra together. The conversion method used is
    :external+scippneutron:py:obj:`scippneutron.conversion.tof.dspacing_from_tof`.

    For a description of the basic theory behind conversions between
    time-of-flight and d-spacing, see the
    `introductory slides <https://www.oxfordneutronschool.org/2024/Lectures/Boothroyd-Introductory%20Theory.pdf>`_
    from the Oxford Neutron School, or the
    `ISIS introduction to ToF neutron diffraction <https://www.isis.stfc.ac.uk/Pages/TOF-neutron-diffraction.aspx>`_.
    """

    def __init__(
        self,
        *,
        prefix: str,
        detectors: npt.NDArray[np.int64],
        l_total: sc.Variable,
        two_theta: sc.Variable,
        dspacing_bin_edges: sc.Variable,
    ) -> None:
        """Create a new DSpacingMappingReducer.

        Args:
            prefix: PV prefix for the :py:obj:`SimpleDae`.
            detectors: numpy :external+numpy:py:obj:`array <numpy.array>` of detector
                spectra to select.
                For example, ``np.array([1, 2, 3])`` selects spectra 1-3 inclusive.
                All detectors in this list are assumed to have the same time
                channel boundaries.
            l_total: scipp :external+scipp:py:obj:`Variable <scipp.Variable>`
                describing the total flight path length of each
                selected detector. Must have the same length as detectors, have units
                of length, and have a scipp dimension label of "spec"
            two_theta: scipp :external+scipp:py:obj:`Variable <scipp.Variable>`
                describing the two theta scattering angle of
                each selected detector. Must have the same length as detectors, have
                units of angle, and have a scipp dimension label of "spec"
            dspacing_bin_edges: scipp :external+scipp:py:obj:`Variable <scipp.Variable>`
                describing the required d-spacing bin-edges.
                This must be bin edge coordinates, aligned along a scipp dimension label of
                "tof", have a unit of length, for example Angstroms
                (:external+scipp:py:obj:`scipp.units.angstrom <scipp.units>`),
                and must be strictly ascending.

        """
        self._detectors = detectors
        self._l_total = l_total
        self._two_theta = two_theta
        self._dspacing_bin_edges = dspacing_bin_edges

        if self._l_total.shape != self._detectors.shape:
            raise ValueError("l_total and detectors must have same shape")
        if self._two_theta.shape != self._detectors.shape:
            raise ValueError("two theta and detectors must have same shape")

        self._first_det = DaeSpectra(
            dae_prefix=prefix + "DAE:", spectra=int(detectors[0]), period=0
        )

        self.dspacing, self._dspacing_setter = soft_signal_r_and_setter(
            Array1D[np.float64], np.array([], dtype=np.float64)
        )

        super().__init__(name="")

    async def reduce_data(self, dae: "SimpleDae") -> None:
        """Expose calculated d-spacing.

        This will be in units of counts, which may be fractional due to rebinning.

        The binning of the data, and hence the length of the d-spacing
        array, has bin edges specified by self.dspacing_bins.
        """
        logger.info("starting reduction reads")
        (
            current_period_data,
            first_spec_dataarray,
        ) = await asyncio.gather(
            dae.trigger_and_get_specdata(detectors=self._detectors),
            self._first_det.read_spectrum_dataarray(),
        )
        logger.info("starting reduction")

        # Since l_total and two_theta are aligned along a "spec" dimension,
        # the d-spacing array here is then 2-dimensional in [spec, tof]
        # This represents the (independent) d-spacing bin boundaries for
        # each detector pixel.
        dspacing = dspacing_from_tof(
            tof=first_spec_dataarray.coords["tof"],
            Ltotal=self._l_total,
            two_theta=self._two_theta,
        )

        data = sc.DataArray(
            data=sc.array(
                dims=["spec", "tof"],
                values=current_period_data,
                unit=sc.units.counts,
                dtype="float64",
            ),
            coords={
                "tof": dspacing,
            },
        )

        binned_data = data.rebin({"tof": self._dspacing_bin_edges})
        summed_data = binned_data.sum(dim="spec")

        self._dspacing_setter(summed_data.values)
        logger.info("reduction complete")

    def additional_readable_signals(self, dae: "SimpleDae") -> list[Device]:
        """Publish interesting signals derived or used by this reducer."""
        return [self.dspacing]

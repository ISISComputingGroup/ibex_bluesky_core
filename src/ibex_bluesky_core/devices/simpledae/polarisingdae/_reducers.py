"""Data reduction strategies for polarising DAEs."""

import asyncio
import logging
import math
from collections.abc import Awaitable, Callable, Collection, Sequence

import scipp as sc
from ophyd_async.core import Device, DeviceVector, Reference, StandardReadable

from ibex_bluesky_core.devices.dae import Dae, DaeSpectra, PolarisedWavelengthBand, WavelengthBand
from ibex_bluesky_core.devices.simpledae._reducers import INTENSITY_PRECISION, VARIANCE_ADDITION
from ibex_bluesky_core.devices.simpledae._strategies import Reducer

logger = logging.getLogger(__name__)


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
    periods (before/after switching a flipper) and the output is interpreted as a neutron
    polarization ratio. Or reflectometry instruments e.g. POLREF, the situation is
    the same as on LARMOR. On muon instruments, A and B correspond to measuring from
    forward/backward detector banks, and the output is interpreted as a muon asymmetry

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


class WavelengthBoundedNormalizer(Reducer, StandardReadable):
    """Sum a set of wavelength-bounded spectra, then normalise by monitor intensity."""

    def __init__(
        self,
        prefix: str,
        detector_spectra: Sequence[int],
        monitor_spectra: Sequence[int],
        sum_wavelength_bands: list[
            Callable[[Collection[DaeSpectra]], Awaitable[sc.Variable | sc.DataArray]]
        ],
    ) -> None:
        """Init.

        Args:
            prefix: the PV prefix of the instrument to get spectra from (e.g. IN:DEMO:)
            detector_spectra: a sequence of spectra numbers (detectors) to sum.
            monitor_spectra: a sequence of spectra numbers (monitors) to sum.
            sum_wavelength_bands: takes a sequence of summing functions, each of which takes
                spectra objects and returns a scipp scalar describing the detector intensity.

        """
        self.sum_wavelength_bands = sum_wavelength_bands

        dae_prefix = prefix + "DAE:"

        self.detectors = DeviceVector(
            {i: DaeSpectra(dae_prefix=dae_prefix, spectra=i, period=0) for i in detector_spectra}
        )
        self.monitors = DeviceVector(
            {i: DaeSpectra(dae_prefix=dae_prefix, spectra=i, period=0) for i in monitor_spectra}
        )

        self.wavelength_bands = DeviceVector(
            {i: WavelengthBand() for i in range(len(self.sum_wavelength_bands))}
        )

        super().__init__(name="")

    async def reduce_data(self, dae: "Dae") -> None:
        """Apply the normalisation."""
        logger.info("starting normalisation")

        for i in range(len(self.sum_wavelength_bands)):
            sum_wavelength_band = self.sum_wavelength_bands[i]
            wavelength_band = self.wavelength_bands[i]
            detector_counts_sc, monitor_counts_sc = await asyncio.gather(
                sum_wavelength_band(self.detectors.values()),
                sum_wavelength_band(self.monitors.values()),
            )

            if monitor_counts_sc.value == 0.0:
                raise ValueError(
                    f"""Cannot normalize; got zero monitor counts in wavelength band {i}.
                     Check beamline configuration."""
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

            wavelength_band.setter(
                det_counts=det_counts,
                det_counts_stddev=det_counts_stddev,
                mon_counts=mon_counts,
                mon_counts_stddev=mon_counts_stddev,
                intensity=intensity,
                intensity_stddev=intensity_stddev,
            )

    def additional_readable_signals(self, dae: Dae) -> list[Device]:
        """Publish interesting signals derived or used by this reducer."""
        return list(self.wavelength_bands.values())


class PolarisingReducer(Reducer, StandardReadable):
    """Calculate polarisation from 'spin-up' and 'spin-down' states of a polarising DAE."""

    def __init__(
        self,
        intervals: list[sc.Variable],
        reducer_up: WavelengthBoundedNormalizer,
        reducer_down: WavelengthBoundedNormalizer,
    ) -> None:
        """Init.

        Args:
            intervals: a sequence of scipp describing the wavelength intervals over which
                to calculate polarisation.
            reducer_up: A data reduction strategy, defines the post-processing on raw DAE data.
                Used to retrieve intensity values from the up-spin state.
            reducer_down: A data reduction strategy, defines the post-processing on raw DAE data.
                Used to retrieve intensity values from the down-spin state.

        """
        self.intervals = intervals
        self.reducer_up = Reference(reducer_up)
        self.reducer_down = Reference(reducer_down)
        self.wavelength_bands = DeviceVector(
            {
                i: PolarisedWavelengthBand(intensity_precision=INTENSITY_PRECISION)
                for i in range(len(intervals))
            }
        )
        super().__init__(name="")

    async def reduce_data(self, dae: Dae) -> None:
        """Apply the polarisation."""
        logger.info("starting polarisation")

        if len(self.reducer_up().wavelength_bands) != len(self.reducer_down().wavelength_bands):
            raise ValueError("Mismatched number of wavelength bands")

        for i in range(len(self.intervals)):
            wavelength_band = self.wavelength_bands[i]

            intensity_up = await self.reducer_up().wavelength_bands[i].intensity.get_value()
            intensity_down = await self.reducer_down().wavelength_bands[i].intensity.get_value()

            if intensity_up == 0.0 or intensity_down == 0.0:
                raise ValueError("Cannot calculate polarisation; zero intensity detected")

            intensity_up_stddev = (
                await self.reducer_up().wavelength_bands[i].intensity_stddev.get_value()
            )
            intensity_down_stddev = (
                await self.reducer_down().wavelength_bands[i].intensity_stddev.get_value()
            )
            intensity_up_sc = sc.scalar(
                value=intensity_up, variance=intensity_up_stddev, dtype=float
            )
            intensity_down_sc = sc.scalar(
                value=intensity_down, variance=intensity_down_stddev, dtype=float
            )

            polarisation_sc = polarization(intensity_up_sc, intensity_down_sc)
            polarisation_ratio_sc = intensity_up_sc / intensity_down_sc

            polarisation = float(polarisation_sc.value)
            polarisation_ratio = float(polarisation_ratio_sc.value)
            polarisation_stddev = float(polarisation_sc.variance)
            polarisation_ratio_stddev = float(polarisation_ratio_sc.variance)

            wavelength_band.setter(
                polarisation=polarisation,
                polarisation_stddev=polarisation_stddev,
                polarisation_ratio=polarisation_ratio,
                polarisation_ratio_stddev=polarisation_ratio_stddev,
            )

    def additional_readable_signals(self, dae: Dae) -> list[Device]:
        """Publish interesting signals derived or used by this reducer."""
        return list(self.wavelength_bands.values())

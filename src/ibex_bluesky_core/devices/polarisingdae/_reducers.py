"""Data reduction strategies for polarising DAEs."""

import asyncio
import logging
import math
import typing
from collections.abc import Awaitable, Callable, Collection, Sequence

import scipp as sc
from ophyd_async.core import Device, DeviceVector, Reference, StandardReadable

from ibex_bluesky_core.devices.dae import Dae, DaeSpectra
from ibex_bluesky_core.devices.polarisingdae._spectra import (
    _PolarisedWavelengthBand,
    _WavelengthBand,
)
from ibex_bluesky_core.devices.simpledae import INTENSITY_PRECISION, VARIANCE_ADDITION, Reducer
from ibex_bluesky_core.utils import calculate_polarisation

logger = logging.getLogger(__name__)


class MultiWavelengthBandNormalizer(Reducer, StandardReadable):
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

        self._wavelength_bands = DeviceVector(
            {i: _WavelengthBand() for i in range(len(self.sum_wavelength_bands))}
        )

        super().__init__(name="")

    async def reduce_data(self, dae: "Dae") -> None:
        """Apply the normalisation."""
        logger.info("starting normalisation")

        for i in range(len(self.sum_wavelength_bands)):
            sum_wavelength_band = self.sum_wavelength_bands[i]
            wavelength_band = self._wavelength_bands[i]
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
        return list(self._wavelength_bands.values())

    @property
    def det_counts_names(self) -> list[str]:
        return [band.det_counts.name for band in self._wavelength_bands.values()]

    @property
    def det_counts_stddev_names(self) -> list[str]:
        return [band.det_counts_stddev.name for band in self._wavelength_bands.values()]

    @property
    def mon_counts_names(self) -> list[str]:
        return [band.mon_counts.name for band in self._wavelength_bands.values()]

    @property
    def mon_counts_stddev_names(self) -> list[str]:
        return [band.mon_counts_stddev.name for band in self._wavelength_bands.values()]

    @property
    def intensity_names(self) -> list[str]:
        return [band.intensity.name for band in self._wavelength_bands.values()]

    @property
    def intensity_stddev_names(self) -> list[str]:
        return [band.intensity_stddev.name for band in self._wavelength_bands.values()]


class PolarisationReducer(Reducer, StandardReadable):
    """Calculate polarisation from 'spin-up' and 'spin-down' states of a polarising DAE."""

    def __init__(
        self,
        intervals: list[sc.Variable],
        reducer_up: MultiWavelengthBandNormalizer,
        reducer_down: MultiWavelengthBandNormalizer,
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
        self._wavelength_bands = DeviceVector(
            {
                i: _PolarisedWavelengthBand(intensity_precision=INTENSITY_PRECISION)
                for i in range(len(intervals))
            }
        )
        super().__init__(name="")

    async def reduce_data(self, dae: Dae) -> None:
        """Apply the polarisation."""
        logger.info("starting polarisation")

        if len(self.reducer_up().additional_readable_signals(dae)) != len(
            self.reducer_down().additional_readable_signals(dae)
        ):
            raise ValueError("Mismatched number of wavelength bands")

        for i in range(len(self.intervals)):
            wavelength_band = self._wavelength_bands[i]

            band_up = typing.cast(
                _WavelengthBand, self.reducer_up().additional_readable_signals(dae)[i]
            )
            intensity_up = await band_up.intensity.get_value()

            band_down = typing.cast(
                _WavelengthBand, self.reducer_down().additional_readable_signals(dae)[i]
            )
            intensity_down = await band_down.intensity.get_value()

            if intensity_up + intensity_down == 0.0:
                raise ValueError("Cannot calculate polarisation; zero intensity sum detected")

            intensity_up_stddev = await band_up.intensity_stddev.get_value()
            intensity_down_stddev = await band_down.intensity_stddev.get_value()
            intensity_up_sc = sc.scalar(
                value=intensity_up, variance=intensity_up_stddev, dtype=float
            )
            intensity_down_sc = sc.scalar(
                value=intensity_down, variance=intensity_down_stddev, dtype=float
            )

            polarisation_sc = calculate_polarisation(intensity_up_sc, intensity_down_sc)
            polarisation_ratio_sc = intensity_up_sc / intensity_down_sc

            polarisation_val = float(polarisation_sc.value)
            polarisation_ratio = float(polarisation_ratio_sc.value)
            polarisation_stddev = float(polarisation_sc.variance)
            polarisation_ratio_stddev = float(polarisation_ratio_sc.variance)

            wavelength_band.setter(
                polarisation=polarisation_val,
                polarisation_stddev=polarisation_stddev,
                polarisation_ratio=polarisation_ratio,
                polarisation_ratio_stddev=polarisation_ratio_stddev,
            )

    def additional_readable_signals(self, dae: Dae) -> list[Device]:
        """Publish interesting signals derived or used by this reducer."""
        return list(self._wavelength_bands.values())

    @property
    def polarisation_names(self) -> list[str]:
        return [band.polarisation.name for band in self._wavelength_bands.values()]

    @property
    def polarisation_stddev_names(self) -> list[str]:
        return [band.polarisation_stddev.name for band in self._wavelength_bands.values()]

    @property
    def polarisation_ratio(self) -> list[str]:
        return [band.polarisation_ratio.name for band in self._wavelength_bands.values()]

    @property
    def polarisation_ratio_stddev(self) -> list[str]:
        return [band.polarisation_ratio_stddev.name for band in self._wavelength_bands.values()]

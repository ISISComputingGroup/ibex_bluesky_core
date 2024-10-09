"""DAE data reduction strategies."""

import asyncio
from abc import ABCMeta, abstractmethod
from typing import TYPE_CHECKING, Collection, Sequence

import numpy as np
import scipp as sc
import math
from ophyd_async.core import (
    Device,
    DeviceVector,
    SignalR,
    StandardReadable,
    soft_signal_r_and_setter,
)

from ibex_bluesky_core.devices.dae.dae_spectra import DaeSpectra
from ibex_bluesky_core.devices.simpledae.strategies import Reducer

if TYPE_CHECKING:
    from ibex_bluesky_core.devices.simpledae import SimpleDae


async def sum_spectra(spectra: Collection[DaeSpectra]) -> sc.Variable | sc.DataArray:
    """Read and sum a number of spectra from the DAE.

    Returns a scipp scalar, which has .value and .variance properties for accessing the sum
    and variance respectively of the summed counts.
    """
    summed_counts = sc.scalar(value=0, unit=sc.units.counts, dtype="float64")
    for spec in asyncio.as_completed([s.read_spectrum_dataarray() for s in spectra]):
        summed_counts += (await spec).sum()
    return summed_counts


class ScalarNormalizer(Reducer, StandardReadable, metaclass=ABCMeta):
    """Sum a set of user-specified spectra, then normalize by a scalar signal."""

    def __init__(self, prefix: str, detector_spectra: Sequence[int]) -> None:
        """Init.

        Args:
            prefix: the PV prefix of the instrument to get spectra from (e.g. IN:DEMO:)
            detector_spectra: a sequence of spectra numbers (detectors) to sum.

        """
        self.detectors = DeviceVector(
            {
                i: DaeSpectra(dae_prefix=prefix + "DAE:", spectra=i, period=0)
                for i in detector_spectra
            }
        )

        self.det_counts, self._det_counts_setter = soft_signal_r_and_setter(float, 0.0)
        self.intensity, self._intensity_setter = soft_signal_r_and_setter(float, 0.0, precision=6)

        self.det_counts_stddev, self._det_counts_stddev_setter = soft_signal_r_and_setter(float, 0.0)
        self.intensity_stddev, self._intensity_stddev_setter = soft_signal_r_and_setter(float, 0.0, precision=6)

        super().__init__(name="")

    @abstractmethod
    def denominator(self, dae: "SimpleDae") -> SignalR[int] | SignalR[float]:
        """Get the normalization denominator, which is assumed to be a scalar signal."""

    async def reduce_data(self, dae: "SimpleDae") -> None:
        """Apply the normalization."""
        summed_counts, denominator = await asyncio.gather(
            sum_spectra(self.detectors.values()), self.denominator(dae).get_value()
        )

        self._det_counts_setter(float(summed_counts.value))
        self._intensity_setter(float(summed_counts.value) / denominator)

        detector_counts_var = 0.0 if summed_counts.variance is None else summed_counts.variance

        var_temp = (summed_counts / denominator).variance
        intensity_var = var_temp if var_temp is not None else 0.0

        self._det_counts_stddev_setter(math.sqrt(detector_counts_var))
        self._intensity_stddev_setter(math.sqrt(intensity_var))

        for spec in self.detectors.values():
            stddev = await spec.read_counts()
            spec._stddev_setter(np.sqrt(stddev))

    def additional_readable_signals(self, dae: "SimpleDae") -> list[Device]:
        """Publish interesting signals derived or used by this reducer."""
        return [
            self.det_counts,
            self.intensity,
            self.denominator(dae),
            self.det_counts_stddev,
            self.intensity_stddev,
        ]
    
    def readable_detector_count_uncertainties(self, dae: "SimpleDae") -> list[Device]:
        """Publish individual uncertainty signals for all detectors."""

        return [self.detectors[i].stddev for i in self.detectors]


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
        self, prefix: str, detector_spectra: Sequence[int], monitor_spectra: Sequence[int]
    ) -> None:
        """Init.

        Args:
            prefix: the PV prefix of the instrument to get spectra from (e.g. IN:DEMO:)
            detector_spectra: a sequence of spectra numbers (detectors) to sum.
            monitor_spectra: a sequence of spectra number (monitors) to sum and normalize by.

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
        self.intensity, self._intensity_setter = soft_signal_r_and_setter(float, 0.0, precision=6)

        self.det_counts_stddev, self._det_counts_stddev_setter = soft_signal_r_and_setter(float, 0.0)
        self.mon_counts_stddev, self._mon_counts_stddev_setter = soft_signal_r_and_setter(float, 0.0)
        self.intensity_stddev, self._intensity_stddev_setter = soft_signal_r_and_setter(float, 0.0, precision=6)

        super().__init__(name="")

    async def reduce_data(self, dae: "SimpleDae") -> None:
        """Apply the normalization."""
        detector_counts, monitor_counts = await asyncio.gather(
            sum_spectra(self.detectors.values()), sum_spectra(self.monitors.values())
        )

        self._det_counts_setter(float(detector_counts.value))
        self._mon_counts_setter(float(monitor_counts.value))
        self._intensity_setter(float((detector_counts / monitor_counts).value))

        detector_counts_var = 0.0 if detector_counts.variance is None else detector_counts.variance
        monitor_counts_var = 0.0 if monitor_counts.variance is None else monitor_counts.variance
        intensity_var = 0.0 if monitor_counts_var == 0.0 else (detector_counts / monitor_counts).variance

        self._det_counts_stddev_setter(math.sqrt(detector_counts_var))
        self._mon_counts_stddev_setter(math.sqrt(monitor_counts_var))
        self._intensity_stddev_setter(math.sqrt(intensity_var))

        for spec in self.detectors.values():
            stddev = await spec.read_counts()
            spec._stddev_setter(np.sqrt(stddev))

        for spec in self.monitors.values():
            stddev = await spec.read_counts()
            spec._stddev_setter(np.sqrt(stddev))

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
    
    def readable_detector_count_uncertainties(self, dae: "SimpleDae") -> list[Device]:
        """Publish individual uncertainty signals for all detectors."""

        return [self.detectors[i].stddev for i in self.detectors]

    def readable_monitor_count_uncertainties(self, dae: "SimpleDae") -> list[Device]:
        """Publish individual uncertainty signals for all monitors."""

        return [self.monitors[i].stddev for i in self.monitors]

from ophyd_async.core import StandardReadable, soft_signal_r_and_setter

__all__ = ["_PolarisedWavelengthBand", "_WavelengthBand"]


class _WavelengthBand(StandardReadable):
    """Subdevice for a single wavelength band.

    Represents a few measurements within a specific wavelength band.
    Has a setter method to assign values to the published signals.
    """

    def __init__(self, *, name: str = "") -> None:
        self.det_counts, self._det_counts_setter = soft_signal_r_and_setter(float, 0.0)
        self.mon_counts, self._mon_counts_setter = soft_signal_r_and_setter(float, 0.0)

        self.intensity, self._intensity_setter = soft_signal_r_and_setter(float, 0.0)
        self.det_counts_stddev, self._det_counts_stddev_setter = soft_signal_r_and_setter(
            float, 0.0
        )
        self.mon_counts_stddev, self._mon_counts_stddev_setter = soft_signal_r_and_setter(
            float, 0.0
        )
        self.intensity_stddev, self._intensity_stddev_setter = soft_signal_r_and_setter(float, 0.0)

        self.intensity.set_name("intensity")
        self.intensity_stddev.set_name("intensity_stddev")

        super().__init__(name=name)

    def setter(
        self,
        *,
        det_counts: float,
        det_counts_stddev: float,
        mon_counts: float,
        mon_counts_stddev: float,
        intensity: float,
        intensity_stddev: float,
    ) -> None:
        self._intensity_setter(intensity)
        self._det_counts_setter(det_counts)
        self._mon_counts_setter(mon_counts)

        self._intensity_stddev_setter(intensity_stddev)
        self._det_counts_stddev_setter(det_counts_stddev)
        self._mon_counts_stddev_setter(mon_counts_stddev)


class _PolarisedWavelengthBand(StandardReadable):
    """Subdevice that holds polarisation info for two wavelength bands.

    Represents the polarisation information calculated using measurements
    taken from two `WavelengthBand` objects, one published from an "up state"
    `WavelengthBoundedNormalizer`and the other from a "down state"
    `WavelengthBoundedNormalizer`. Has a setter method to assign values to
    the published signals.
    """

    def __init__(self, *, name: str = "", intensity_precision: int = 6) -> None:
        with self.add_children_as_readables():
            self.polarisation, self._polarisation_setter = soft_signal_r_and_setter(
                float, 0.0, precision=intensity_precision
            )
            self.polarisation_stddev, self._polarisation_stddev_setter = soft_signal_r_and_setter(
                float, 0.0, precision=intensity_precision
            )
            self.polarisation_ratio, self._polarisation_ratio_setter = soft_signal_r_and_setter(
                float, 0.0, precision=intensity_precision
            )
            self.polarisation_ratio_stddev, self._polarisation_ratio_stddev_setter = (
                soft_signal_r_and_setter(float, 0.0, precision=intensity_precision)
            )

        self.polarisation.set_name("polarisation")
        self.polarisation_stddev.set_name("polarisation_stddev")
        self.polarisation_ratio.set_name("polarisation_ratio")
        self.polarisation_ratio_stddev.set_name("polarisation_ratio_stddev")

        super().__init__(name=name)

    def setter(
        self,
        *,
        polarisation: float,
        polarisation_stddev: float,
        polarisation_ratio: float,
        polarisation_ratio_stddev: float,
    ) -> None:
        self._polarisation_setter(polarisation)
        self._polarisation_stddev_setter(polarisation_stddev)
        self._polarisation_ratio_setter(polarisation_ratio)
        self._polarisation_ratio_stddev_setter(polarisation_ratio_stddev)

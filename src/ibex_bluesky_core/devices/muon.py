"""Muon specific bluesky device helpers."""

import asyncio
import logging

import numpy as np
import numpy.typing as npt
import scipp as sc
from lmfit import Model, Parameter
from lmfit.model import ModelResult
from numpy.typing import NDArray
from ophyd_async.core import (
    Device,
    StandardReadable,
    soft_signal_r_and_setter,
)

from ibex_bluesky_core.devices.dae import Dae, DaeSpectra
from ibex_bluesky_core.devices.simpledae import Reducer
from ibex_bluesky_core.utils import calculate_polarisation

logger = logging.getLogger(__name__)


def damped_oscillator(
        t: NDArray,
        B: float,  # noqa: N803
        A_0: float,  # noqa: N803
        omega_0: float,
        phi_0: float,
        lambda_0: float,
) -> NDArray:
    return B + A_0 * np.cos(omega_0 * t + phi_0) * np.exp(-t * lambda_0)


class MuonAsymmetryReducer(Reducer, StandardReadable):
    r"""DAE reducer which exposes a computed asymmetry quantity.

    This reducer takes two lists of detectors; a forward scattering set of detectors,
    :math:`F`, and a backward scattering set, :math:`B`.

    The spin-asymmetry is computed with:

    .. math::

        a = \frac{F - \alpha B}{F + \alpha B}

    Where :math:`\alpha` is a user-specified scalar constant, :math:`F` is an array of
    total forward-scattering detector counts against time, and :math:`B` is an array of
    backward-scattering detector counts against time. This results in an array of
    asymmetry (:math:`a`) against time.

    Finally, the array of asymmetry against time (:math:`t`) is fitted with one of the
    following models:

    .. math::

        a = B + A_0 cos({ω_0} {t} + {φ_0}) e^{-λ_0 t}

        a = B + A_0 cos({ω_0} {t} + {φ_0}) e^{-λ_0 t} + A_1 cos({ω_1} {t} + {φ_1}) e^{-λ_1 t}

    The resulting fit parameters, along with their uncertainties, are exposed as
    signals from this reducer.

    """

    def __init__(
        self,
        *,
        prefix: str,
        forward_detectors: npt.NDArray[np.int64],
        backward_detectors: npt.NDArray[np.int64],
        alpha: float = 1.0,
        time_bin_edges: sc.Variable | None = None,
    ) -> None:
        """Create a new Muon asymmetry reducer.

        Args:
            prefix: PV prefix for the :py:obj:`SimpleDae`.
            forward_detectors: numpy :external+numpy:py:obj:`array <numpy.array>` of detector
                spectra to select for forward-scattering.
                For example, ``np.array([1, 2, 3])`` selects spectra 1-3 inclusive.
                All detectors in this list are assumed to have the same time
                channel boundaries.
            backward_detectors: numpy :external+numpy:py:obj:`array <numpy.array>` of detector
                spectra to select for backward-scattering.
            alpha: Scaling factor used in asymmetry calculation, applied to backward detector
                counts. Defaults to 1.
            time_bin_edges: Optional scipp :external+scipp:py:obj:`Variable <scipp.Variable>`
                describing bin-edges for rebinning the data before fitting.
                This must be bin edge coordinates, aligned along a scipp dimension label of
                "tof", have a unit of time, for example nanoseconds and must be strictly ascending.
                Use :py:obj:`None` to not apply any rebinning to the data.

        """
        self._forward_detectors = forward_detectors
        self._backward_detectors = backward_detectors
        self._alpha = alpha
        self._time_bin_edges = time_bin_edges

        self._first_det = DaeSpectra(
            dae_prefix=prefix + "DAE:", spectra=int(forward_detectors[0]), period=0
        )

        self.B, self._B_setter = soft_signal_r_and_setter(float, 0.0)
        self.B_err, self._B_err_setter = soft_signal_r_and_setter(float, 0.0)

        self.A_0, self._A_0_setter = soft_signal_r_and_setter(float, 0.0)
        self.A_0_err, self._A_0_err_setter = soft_signal_r_and_setter(float, 0.0)

        self.omega_0, self._omega_0_setter = soft_signal_r_and_setter(float, 0.0)
        self.omega_0_err, self._omega_0_err_setter = soft_signal_r_and_setter(float, 0.0)

        self.phi_0, self._phi_0_setter = soft_signal_r_and_setter(float, 0.0)
        self.phi_0_err, self._phi_0_err_setter = soft_signal_r_and_setter(float, 0.0)

        self.lambda_0, self._lambda_0_setter = soft_signal_r_and_setter(float, 0.0)
        self.lambda_0_err, self._lambda_0_err_setter = soft_signal_r_and_setter(float, 0.0)

        super().__init__(name="")

    def _rebin_and_sum(self, counts: NDArray, time_coord: sc.Variable) -> sc.DataArray:
        da = sc.DataArray(
            data=sc.array(
                dims=["spec", "tof"],
                values=counts,
                variances=counts,
                unit=sc.units.counts,
                dtype="float64",
            ),
            coords={
                "tof": time_coord,
            },
        )
        da = da.sum(dim="spec")

        if self._time_bin_edges is not None:
            da = da.rebin({"tof": self._time_bin_edges})

        return da

    def _fit_data(self, asymmetry: sc.DataArray) -> ModelResult | None:
        model = Model(damped_oscillator)

        bin_edges = asymmetry.coords["tof"].to(unit=sc.units.ns, dtype="float64").values
        bin_centers = (bin_edges[:-1] + bin_edges[1:]) / 2

        result = model.fit(
            asymmetry.values,
            t=bin_centers,
            weights=1.0 / (asymmetry.variances**0.5),
            B=Parameter("B", value=0.0),
            A_0=Parameter("A_0", value=1, min=0),
            omega_0=Parameter("omega_0", value=0.1),
            phi_0=Parameter("phi_0", value=0),
            lambda_0=Parameter("lambda_0", value=0.0),
            nan_policy="omit",
        )

        return result

    def _calculate_asymmetry(
        self, current_period_data: NDArray, first_spec_dataarray: sc.DataArray
    ) -> sc.DataArray:
        forward = self._rebin_and_sum(
            current_period_data[self._forward_detectors, :], first_spec_dataarray.coords["tof"]
        )
        backward = self._rebin_and_sum(
            current_period_data[self._backward_detectors, :], first_spec_dataarray.coords["tof"]
        )
        forward.variances += 0.5
        backward.variances += 0.5
        return calculate_polarisation(forward, backward, self._alpha)

    async def reduce_data(self, dae: Dae) -> None:
        """Fitting asymmetry to a set of DAE data."""
        logger.info("starting reduction reads")
        (
            current_period_data,
            first_spec_dataarray,
        ) = await asyncio.gather(
            dae.trigger_and_get_specdata(),
            self._first_det.read_spectrum_dataarray(),
        )

        logger.info("starting reduction")

        asymmetry = self._calculate_asymmetry(current_period_data, first_spec_dataarray)
        fit_result = self._fit_data(asymmetry)

        if fit_result is None:
            raise ValueError(
                "MuonAsymmetryReducer failed to fit asymmetry model to muon data.\n"
                "Check beamline setup."
            )

        self._B_setter(fit_result.params["B"].value)
        self._B_err_setter(fit_result.params["B"].stderr)
        self._A_0_setter(fit_result.params["A_0"].value)
        self._A_0_err_setter(fit_result.params["A_0"].stderr)
        self._omega_0_setter(fit_result.params["omega_0"].value)
        self._omega_0_err_setter(fit_result.params["omega_0"].stderr)
        self._phi_0_setter(fit_result.params["phi_0"].value)
        self._phi_0_err_setter(fit_result.params["phi_0"].stderr)
        self._lambda_0_setter(fit_result.params["lambda_0"].value)
        self._lambda_0_err_setter(fit_result.params["lambda_0"].stderr)
        logger.info("reduction complete")

    def additional_readable_signals(self, dae: Dae) -> list[Device]:
        """Publish interesting signals derived or used by this reducer."""
        return [self.B]

"""Muon-specific bluesky devices and utilities."""

import asyncio
import logging
import typing

import lmfit
import numpy as np
import numpy.typing as npt
import scipp as sc
from lmfit import Model
from lmfit.model import ModelResult
from numpy.typing import NDArray
from ophyd_async.core import (
    Device,
    StandardReadable,
    soft_signal_r_and_setter,
)

from ibex_bluesky_core.devices.dae import Dae, DaeSpectra
from ibex_bluesky_core.devices.simpledae import (
    VARIANCE_ADDITION,
    Reducer,
)
from ibex_bluesky_core.utils import calculate_polarisation

logger = logging.getLogger(__name__)

__all__ = [
    "MuonAsymmetryReducer",
    "MuonLifetimeReducer",
    "damped_oscillator",
    "double_damped_oscillator",
    "muon_lifetime",
]


def damped_oscillator(
    t: NDArray[np.floating],
    B: float,  # ruff:ignore[invalid-argument-name]
    A_0: float,  # ruff:ignore[invalid-argument-name]
    omega_0: float,
    phi_0: float,
    lambda_0: float,
) -> NDArray[np.floating]:
    r"""Equation for a damped oscillator with an offset, as a function of time :math:`t`.

    .. math::

        B + A_0 \cos(\omega_0 t + \phi_0) e^{-\lambda_0 t}
    """
    return B + A_0 * np.cos(omega_0 * t + phi_0) * np.exp(-t * lambda_0)


def double_damped_oscillator(  # ruff:ignore[too-many-arguments, too-many-positional-arguments] (model is just this complex)
    t: NDArray[np.floating],
    B: float,  # ruff:ignore[invalid-argument-name]
    A_0: float,  # ruff:ignore[invalid-argument-name]
    omega_0: float,
    phi_0: float,
    lambda_0: float,
    A_1: float,  # ruff:ignore[invalid-argument-name]
    omega_1: float,
    phi_1: float,
    lambda_1: float,
) -> NDArray[np.floating]:
    r"""Equation for two damped oscillators with an offset, as a function of time :math:`t`.

    .. math::

        B + A_0 \cos(\omega_0 t + \phi_0) e^{-\lambda_0 t}
            + A_1 \cos(\omega_1 t + \phi_1) e^{-\lambda_1 t}
    """
    return (
        B
        + A_0 * np.cos(omega_0 * t + phi_0) * np.exp(-t * lambda_0)
        + A_1 * np.cos(omega_1 * t + phi_1) * np.exp(-t * lambda_1)
    )


def muon_lifetime(
    t: NDArray[np.floating],
    N_0: float,  # ruff:ignore[invalid-argument-name]
    lambda_0: float,
    N_1: float,  # ruff:ignore[invalid-argument-name]
    lambda_1: float,
) -> NDArray[np.floating]:
    r"""Equation for a muon decay/lifetime, as a function of time :math:`t`.

    .. math::

        N_0 e^{-\lambda_0 t} + N_1 e^{-\lambda_1 t}
    """
    return N_0 * np.exp(-lambda_0 * t) + N_1 * np.exp(-lambda_1 * t)


def _create_fit_parameter_signals(
    owner: object, model: Model, fit_parameters: lmfit.Parameters
) -> tuple[dict[str, typing.Callable[[float], None]], dict[str, typing.Callable[[float], None]]]:
    missing = set(model.param_names) - set(fit_parameters.keys())
    if missing:
        raise ValueError(f"Missing parameters: {missing}")

    parameter_setters: dict[str, typing.Callable[[float], None]] = {}
    parameter_error_setters: dict[str, typing.Callable[[float], None]] = {}

    for param in model.param_names:
        signal, setter = soft_signal_r_and_setter(float, 0.0)
        setattr(owner, param, signal)
        parameter_setters[param] = setter

        error_signal, error_setter = soft_signal_r_and_setter(float, 0.0)
        setattr(owner, f"{param}_err", error_signal)
        parameter_error_setters[param] = error_setter

    return parameter_setters, parameter_error_setters


def _fit_model(
    model: Model, fit_parameters: lmfit.Parameters, data: sc.DataArray
) -> ModelResult | None:
    bin_edges = data.coords["tof"].to(unit=sc.units.ns, dtype="float64").values
    bin_centers = (bin_edges[:-1] + bin_edges[1:]) / 2

    return model.fit(
        data.values,
        t=bin_centers,
        weights=1.0 / (data.variances**0.5),
        params=fit_parameters,
        nan_policy="omit",
    )


def _fit_and_publish_params(
    owner: object,
    fit_data: typing.Callable[[sc.DataArray], ModelResult | None],
    parameter_setters: dict[str, typing.Callable[[float], None]],
    parameter_error_setters: dict[str, typing.Callable[[float], None]],
    data: sc.DataArray,
) -> None:
    fit_result = fit_data(data)

    if fit_result is None:
        raise ValueError(
            f"{owner.__class__.__name__} failed to fit model to muon data.\nCheck beamline setup."
        )

    for param, setter in parameter_setters.items():
        result = fit_result.params[param]

        setter(result.value)
        parameter_error_setters[param](result.stderr)


def _muon_fit_readable_signals(owner: object, model: Model) -> list[Device]:
    signal_values = []
    signal_errors = []

    for param in model.param_names:
        signal_values.append(getattr(owner, param))
        signal_errors.append(getattr(owner, f"{param}_err"))

    return signal_values + signal_errors


def _rebin_and_sum(
    counts: NDArray[np.int32], time_coord: sc.Variable, time_bin_edges: sc.Variable | None
) -> sc.DataArray:
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

    if time_bin_edges is not None:
        da = da.rebin({"tof": time_bin_edges})

    return da


class MuonAsymmetryReducer(Reducer, StandardReadable):
    r"""DAE reducer which exposes a fitted asymmetry quantity.

    This reducer takes two lists of detectors; a forward scattering set of detectors,
    :math:`F`, and a backward scattering set, :math:`B`.

    The spin-asymmetry is computed with:

    .. math::

        a = \frac{F - \alpha B}{F + \alpha B}

    Where :math:`\alpha` is a user-specified scalar constant, :math:`F` is an array of
    total forward-scattering detector counts against time, and :math:`B` is an array of
    backward-scattering detector counts against time. This results in an array of
    asymmetry (:math:`a`) against time.

    Finally, the array of asymmetry (:math:`a`) against time (:math:`t`, in nanoseconds)
    is fitted using a user-specified model - for example, one of the two models below
    (which are implemented by
    :py:obj:`damped_oscillator <ibex_bluesky_core.devices.muon.damped_oscillator>` and
    :py:obj:`double_damped_oscillator <ibex_bluesky_core.devices.muon.double_damped_oscillator>`).

    .. math::

        a = B + A_0 cos({ω_0} {t} + {φ_0}) e^{-λ_0 t}

        a = B + A_0 cos({ω_0} {t} + {φ_0}) e^{-λ_0 t} + A_1 cos({ω_1} {t} + {φ_1}) e^{-λ_1 t}

    The resulting fit parameters, along with their uncertainties, are exposed as
    signals from this reducer. For example, for a model like:

    .. code-block:: python

        def my_model(t, m, c):
            return m * t + c

        model = lmfit.Model(my_model)

    The exposed signals will include ``m``, ``m_err``, ``c``, and ``c_err``.

    .. note::

        The independent variable must be called `t` (time).

    An example setup showing how to fit a linear model to asymmetry using this
    reducer is:

    .. code-block:: python

        def linear(t, m, c):
            return m * t + c

        # lmfit Parameters describing initial guesses and fitting constraints
        parameters = lmfit.Parameters()
        parameters.add("m", 0)
        parameters.add("c", 0, min=0, max=1000)

        controller = RunPerPointController(save_run=True)
        waiter = PeriodGoodFramesWaiter(500)
        reducer = MuonAsymmetryReducer(
            prefix=prefix,
            # Selects spectra 1-4 for forwards-scattering, spectra 5-8 for backwards-scattering
            forward_detectors=np.array([1, 2, 3, 4]),
            backward_detectors=np.array([5, 6, 7, 8]),
            # Optional: rebin the muon data to these time bins before fitting.
            time_bin_edges=sc.linspace(
                start=0, stop=200, num=100, unit=sc.units.ns, dtype="float64", dim="tof"
            ),
            # Scalar multiplier applied to backwards detectors in asymmetry calculation.
            alpha=1.0,
            model=lmfit.Model(linear),
            fit_parameters=parameters
        )

        dae = SimpleDae(
            prefix=prefix,
            controller=controller,
            waiter=waiter,
            reducer=reducer
        )

    """

    def __init__(  # ruff:ignore[too-many-arguments] (complex function, mitigated by kw-only arguments)
        self,
        *,
        prefix: str,
        forward_detectors: npt.NDArray[np.int32],
        backward_detectors: npt.NDArray[np.int32],
        alpha: float = 1.0,
        time_bin_edges: sc.Variable | None = None,
        model: Model,
        fit_parameters: lmfit.Parameters,
    ) -> None:
        """Create a new Muon asymmetry reducer.

        Args:
            prefix: PV prefix for the
                :py:obj:`SimpleDae <ibex_bluesky_core.devices.simpledae.SimpleDae>`.
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
                "tof", have a unit of time, for example nanoseconds, and must be strictly ascending.
                Use :py:obj:`None` to not apply any rebinning to the data.
            model: :external:py:obj:`lmfit.model.Model` object describing the model to fit to
                the muon data. The independent variable must be :math:`t` (time, in nanoseconds).
            fit_parameters: :external:py:obj:`lmfit.parameter.Parameters` object describing
                the initial parameters (and constraints) for each fit parameter.

        """
        self._forward_detectors = forward_detectors
        self._backward_detectors = backward_detectors
        self._alpha = alpha
        self._time_bin_edges = time_bin_edges

        self._first_det = DaeSpectra(
            dae_prefix=prefix + "DAE:", spectra=int(forward_detectors[0]), period=0
        )

        self._model = model
        self._fit_parameters = fit_parameters

        super().__init__(name="")

        self._parameter_setters, self._parameter_error_setters = _create_fit_parameter_signals(
            self, model, fit_parameters
        )

    def _fit_data(self, data: sc.DataArray) -> ModelResult | None:
        return _fit_model(self._model, self._fit_parameters, data)

    def _calculate_asymmetry(
        self, current_period_data: NDArray[np.int32], first_spec_dataarray: sc.DataArray
    ) -> sc.DataArray:
        forward = _rebin_and_sum(
            current_period_data[self._forward_detectors, :],
            first_spec_dataarray.coords["tof"],
            self._time_bin_edges,
        )
        backward = _rebin_and_sum(
            current_period_data[self._backward_detectors, :],
            first_spec_dataarray.coords["tof"],
            self._time_bin_edges,
        )
        forward.variances += VARIANCE_ADDITION
        backward.variances += VARIANCE_ADDITION
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
        _fit_and_publish_params(
            self, self._fit_data, self._parameter_setters, self._parameter_error_setters, asymmetry
        )

        logger.info("reduction complete")

    def additional_readable_signals(self, dae: Dae) -> list[Device]:
        """Publish interesting signals derived or used by this reducer.

        :meta private:
        """
        return _muon_fit_readable_signals(self, self._model)

    # As we have dynamic attributes, tell pyright that __getattr__ may return any type.
    __getattr__: typing.Callable[[str], typing.Any]


class MuonLifetimeReducer(Reducer, StandardReadable):
    r"""DAE reducer which exposes fitted muon decay rates.

    This reducer takes a list of detectors, sums the spectra together element wise, as
    to preserve time of flight dimensionality and normalizes by good frames. This results
    in an array of noramalized counts (:math:`C`) against time.

    The array of normalized counts (:math:`C`) against time (:math:`t`, in nanoseconds)
    is fitted using a user-specified model - for example,
    :py:obj:`muon_decay <ibex_bluesky_core.devices.muon.muon_decay>`

    The resulting fit parameters, along with their uncertainties, are exposed as
    signals from this reducer. For example, for a model like:

    .. code-block:: python

        def my_model(t, m, c):
            return m * t + c

        model = lmfit.Model(my_model)

    The exposed signals will include ``m``, ``m_err``, ``c``, and ``c_err``.

    .. note::

        The independent variable must be called `t` (time).

    An example setup showing how to fit a linear model to muon lifetime using this
    reducer is:

    .. code-block:: python
        def linear(t, m, c):
            return m * t + c

        # lmfit Parameters describing initial guesses and fitting constraints
        parameters = lmfit.Parameters()
        parameters.add("m", 0)
        parameters.add("c", 0, min=0, max=1000)

        controller = RunPerPointController(save_run=True)
        waiter = PeriodGoodFramesWaiter(500)
        reducer = MuonLifetimeReducer(
            prefix=prefix,
            # Selects spectra 1-4
            detectors=[1, 2, 3, 4],
            model=lmfit.Model(linear),
            fit_parameters=parameters
        )

        dae = SimpleDae(
            prefix=prefix,
            controller=controller,
            waiter=waiter,
            reducer=reducer
        )
    """

    def __init__(
        self,
        *,
        prefix: str,
        detectors: npt.NDArray[np.int32],
        time_bin_edges: sc.Variable | None = None,
        model: Model,
        fit_parameters: lmfit.Parameters,
    ) -> None:
        """Create a new Muon lifetime reducer.

        Args:
            prefix: PV prefix for the
                :py:obj:`SimpleDae <ibex_bluesky_core.devices.simpledae.SimpleDae>`.
            detectors: numpy :external+numpy:py:obj:`array <numpy.array>` of detector
                spectra to select.
                For example, ``np.array([1, 2, 3])`` selects spectra 1-3 inclusive.
                All detectors in this list are assumed to have the same time
                channel boundaries.
            time_bin_edges: Optional scipp :external+scipp:py:obj:`Variable <scipp.Variable>`
                describing bin-edges for rebinning the data before fitting.
                This must be bin edge coordinates, aligned along a scipp dimension label of
                "tof", have a unit of time, for example nanoseconds, and must be strictly ascending.
                Use :py:obj:`None` to not apply any rebinning to the data.
            model: :external:py:obj:`lmfit.model.Model` object describing the model to fit to
                the muon data. The independent variable must be :math:`t` (time, in nanoseconds).
            fit_parameters: :external:py:obj:`lmfit.parameter.Parameters` object describing
                the initial parameters (and constraints) for each fit parameter.

        """
        self.detectors = detectors
        self._model = model
        self._fit_parameters = fit_parameters
        self._time_bin_edges = time_bin_edges

        self._first_det = DaeSpectra(
            dae_prefix=prefix + "DAE:", spectra=int(detectors[0]), period=0
        )

        super().__init__(name="")

        self._parameter_setters, self._parameter_error_setters = _create_fit_parameter_signals(
            self, self._model, fit_parameters
        )

    def _fit_data(self, data: sc.DataArray) -> ModelResult | None:
        return _fit_model(self._model, self._fit_parameters, data)

    async def reduce_data(self, dae: Dae) -> None:
        """Apply the normalization.

        :meta private:
        """
        logger.info("starting reduction reads")
        (
            current_period_data,
            first_spec_dataarray,
            denominator,
        ) = await asyncio.gather(
            dae.trigger_and_get_specdata(),
            self._first_det.read_spectrum_dataarray(),
            dae.period.good_frames.get_value(),
        )

        logger.info("starting reduction")

        da = _rebin_and_sum(
            current_period_data, first_spec_dataarray.coords["tof"], self._time_bin_edges
        )
        da.variances += VARIANCE_ADDITION

        _fit_and_publish_params(
            self,
            self._fit_data,
            self._parameter_setters,
            self._parameter_error_setters,
            da / denominator,  # Normalize by good frames
        )
        logger.info("reduction complete")

    def additional_readable_signals(self, dae: Dae) -> list[Device]:
        """Publish interesting signals derived or used by this reducer.

        :meta private:
        """
        return _muon_fit_readable_signals(self, self._model)

    # As we have dynamic attributes, tell pyright that __getattr__ may return any type.
    __getattr__: typing.Callable[[str], typing.Any]

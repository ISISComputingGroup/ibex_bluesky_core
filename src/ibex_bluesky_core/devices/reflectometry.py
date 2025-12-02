"""Devices specific to Reflectometry beamlines."""

import asyncio
import logging

import numpy as np
import numpy.typing as npt
import scipp as sc
from bluesky.protocols import NamedMovable
from ophyd_async.core import (
    AsyncStatus,
    Device,
    SignalR,
    SignalW,
    StandardReadable,
    StandardReadableFormat,
    observe_value,
    soft_signal_r_and_setter,
)
from ophyd_async.epics.core import epics_signal_r, epics_signal_rw, epics_signal_w

from ibex_bluesky_core.devices import NoYesChoice
from ibex_bluesky_core.devices.dae import Dae
from ibex_bluesky_core.devices.simpledae import Reducer
from ibex_bluesky_core.fitting import Gaussian
from ibex_bluesky_core.utils import get_pv_prefix

logger = logging.getLogger(__name__)

__all__ = ["AngleMappingReducer", "ReflParameter", "ReflParameterRedefine", "refl_parameter"]


class ReflParameter(StandardReadable, NamedMovable[float]):
    """Utility device for a reflectometry server parameter."""

    def __init__(
        self, prefix: str, name: str, changing_timeout_s: float, *, has_redefine: bool = True
    ) -> None:
        """Reflectometry server parameter.

        Args:
            prefix: the PV prefix.
            name: the name of the parameter.
            changing_timeout_s: seconds to wait for the CHANGING signal to go to False after a set.
            has_redefine: whether this parameter can be redefined.

        """
        with self.add_children_as_readables(StandardReadableFormat.HINTED_SIGNAL):
            self.readback: SignalR[float] = epics_signal_r(float, f"{prefix}REFL_01:PARAM:{name}")
        self.setpoint: SignalW[float] = epics_signal_w(float, f"{prefix}REFL_01:PARAM:{name}:SP")
        self.changing: SignalR[bool] = epics_signal_r(
            bool, f"{prefix}REFL_01:PARAM:{name}:CHANGING"
        )
        if has_redefine:
            self.redefine = ReflParameterRedefine(prefix=prefix, name=name)
        else:
            self.redefine = None
        self.changing_timeout = changing_timeout_s
        super().__init__(name=name)
        self.readback.set_name(name)

    @AsyncStatus.wrap
    async def set(self, value: float) -> None:
        """Set the setpoint.

        This waits for the reflectometry parameter's 'CHANGING' PV to go True to
         indicate it has finished.
        """
        logger.info("setting %s to %s", self.setpoint.source, value)
        await self.setpoint.set(value, wait=True, timeout=None)
        await asyncio.sleep(0.1)
        logger.info("waiting for %s", self.changing.source)
        async for chg in observe_value(self.changing, done_timeout=self.changing_timeout):
            logger.debug("%s: %s", self.changing.source, chg)
            if not chg:
                break

    def __repr__(self) -> str:
        """Debug representation."""
        return f"{self.__class__.__name__}(name={self.name})"


class ReflParameterRedefine(StandardReadable):
    """Utility device for redefining a reflectometry server parameter."""

    def __init__(self, prefix: str, name: str) -> None:
        """Reflectometry server parameter redefinition.

        Args:
            prefix: the reflectometry parameter full address.
            name: the name of the parameter redefinition.

        """
        self.define_pos_sp = epics_signal_w(float, f"{prefix}REFL_01:PARAM:{name}:DEFINE_POS_SP")
        self.manager_mode = epics_signal_rw(NoYesChoice, f"{prefix}CS:MANAGER")
        super().__init__(name)

    @AsyncStatus.wrap
    async def set(self, value: float) -> None:
        """Set the setpoint.

        This redefines the position of a reflectometry parameter as the given value, and
        waits for the reflectometry parameter redefinition's 'CHANGED' PV
        to go True to indicate it has finished redefining the position.
        """
        in_manager_mode = await self.manager_mode.get_value()
        if in_manager_mode != NoYesChoice.YES:
            raise ValueError(f"Cannot redefine {self.define_pos_sp.source} as not in manager mode.")
        logger.info("setting %s to %s", self.define_pos_sp.source, value)
        await self.define_pos_sp.set(value, wait=True, timeout=None)
        logger.info("waiting for 1s for redefine to finish")
        # The Reflectometry server has a CHANGED PV for a redefine, but it doesn't actually
        # give a monitor update, so just wait an arbitrary length of time for it to be done.
        await asyncio.sleep(1.0)


def refl_parameter(
    name: str, changing_timeout_s: float = 60.0, has_redefine: bool = True
) -> ReflParameter:
    """Small wrapper around a reflectometry parameter device.

    This automatically applies the current instrument's PV prefix.

    Args:
        name: the reflectometry parameter name.
        changing_timeout_s: time to wait (seconds) for the CHANGING signal to go False after a set.
        has_redefine: whether this parameter can be redefined.

    Returns a device pointing to a reflectometry parameter.

    """
    prefix = get_pv_prefix()
    return ReflParameter(
        prefix=prefix, name=name, changing_timeout_s=changing_timeout_s, has_redefine=has_redefine
    )


class AngleMappingReducer(Reducer, StandardReadable):
    """Reflectometry angle-mapping reducer."""

    def __init__(
        self,
        *,
        detectors: npt.NDArray[np.int32],
        angle_map: npt.NDArray[np.float64],
        flood: sc.Variable | None = None,
    ) -> None:
        """Angle-mapping reducer describing parameters of beam on a 1-D angular detector.

        This :py:obj:`~ibex_bluesky_core.devices.simpledae.Reducer` fits the
        counts on each pixel of a detector, against the relative angular positions
        of those pixels. It then exposes fitted quantities, and their standard deviations,
        as signals from this reducer.

        The fitting model used is a :py:obj:`~ibex_bluesky_core.fitting.Gaussian`.
        Uncertainties from the counts data are taken into account on these fits -
        the variances are set to `counts + 0.5`
        (see :doc:`ADR5 </architectural_decisions/005-variance-addition>`
        for justification).

        Optionally, a flood map can be provided to normalise for pixel efficiencies
        before fitting. This flood map is provided as a :py:obj:`scipp.Variable`,
        which means that it may contain variances.

        .. warning::

            The uncertainties (signals ending in ``_err``) from this reducer are
            obtained from :py:obj:`lmfit`. The exact method is described in
            lmfit's :py:obj:`~lmfit.minimizer.MinimizerResult` documentation.
            For a perfect fit, which might result from fitting a limited number
            of points or flat data, uncertainties may be zero.

            Because the uncertainties may be zero, using them in an 'outer' fit is
            discouraged; an uncertainty of zero implies infinite weighting,
            which will likely cause the outer fit to fail to converge.

        Args:
            detectors: numpy array of detector spectra to include.
            angle_map: numpy array of relative pixel angles for each
                selected detector
            flood: Optional :py:obj:`scipp.Variable` describing a flood-correction.
                This array should be aligned along a "spectrum" dimension; counts are
                divided by this array before being used in fits. This is used to
                normalise the intensities detected by each detector pixel.

        """
        self.amp, self._amp_setter = soft_signal_r_and_setter(float, 0.0)
        """Amplitude of fitted Gaussian"""
        self.amp_err, self._amp_err_setter = soft_signal_r_and_setter(float, 0.0)
        """Amplitude standard deviation of fitted Gaussian.

        This is the standard error reported by :py:obj:`lmfit.model.Model.fit`.
        """
        self.sigma, self._sigma_setter = soft_signal_r_and_setter(float, 0.0)
        """Width (sigma) of fitted Gaussian"""
        self.sigma_err, self._sigma_err_setter = soft_signal_r_and_setter(float, 0.0)
        """Width (sigma) standard deviation of fitted Gaussian.

        This is the standard error reported by :py:obj:`lmfit.model.Model.fit`.
        """
        self.x0, self._x0_setter = soft_signal_r_and_setter(float, 0.0)
        """Centre (x0) of fitted Gaussian"""
        self.x0_err, self._x0_err_setter = soft_signal_r_and_setter(float, 0.0)
        """Centre (x0) standard deviation of fitted Gaussian.

        This is the standard error reported by :py:obj:`lmfit.model.Model.fit`.
        """
        self.background, self._background_setter = soft_signal_r_and_setter(float, 0.0)
        """Background of fitted Gaussian"""
        self.background_err, self._background_err_setter = soft_signal_r_and_setter(float, 0.0)
        """Background standard deviation of fitted Gaussian.

        This is the standard error reported by :py:obj:`lmfit.model.Model.fit`.
        """

        self.r_squared, self._r_squared_setter = soft_signal_r_and_setter(float, 0.0)
        """R-squared (goodness of fit) parameter reported by :py:obj:`lmfit.model.Model.fit`."""

        super().__init__()
        self._detectors = detectors
        self._angle_map = angle_map
        self._flood = flood if flood is not None else sc.scalar(value=1.0, dtype="float64")
        self._fit_method = Gaussian()

    def additional_readable_signals(self, dae: Dae) -> list[Device]:
        """Expose fit parameters as readable signals.

        :meta private:
        """
        return [
            self.amp,
            self.amp_err,
            self.sigma,
            self.sigma_err,
            self.x0,
            self.x0_err,
            self.background,
            self.background_err,
        ]

    async def reduce_data(self, dae: Dae) -> None:
        """Perform the 'reduction'.

        :meta private:
        """
        data = await dae.trigger_and_get_specdata()

        # Filter to relevant detectors
        data = data[self._detectors]

        # Sum in ToF
        data = data.sum(axis=1)

        data = sc.array(dims=["spectrum"], values=data, variances=data + 0.5)
        data /= self._flood

        fit_method = Gaussian()

        # Generate initial guesses and fit
        guess = fit_method.guess()(self._angle_map, data.values)
        result = fit_method.model().fit(
            data.values, x=self._angle_map, **guess, weights=1 / (data.variances**0.5)
        )

        self._amp_setter(result.params["amp"].value)
        self._amp_err_setter(result.params["amp"].stderr)
        self._x0_setter(result.params["x0"].value)
        self._x0_err_setter(result.params["x0"].stderr)
        self._sigma_setter(result.params["sigma"].value)
        self._sigma_err_setter(result.params["sigma"].stderr)
        self._background_setter(result.params["background"].value)
        self._background_err_setter(result.params["background"].stderr)

        self._r_squared_setter(result.rsquared)

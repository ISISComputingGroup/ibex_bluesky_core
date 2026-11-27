"""SANS rocking scan plan."""

import functools
import logging
from collections.abc import Callable, Generator, Sequence
from typing import Any, ParamSpec, TypedDict

import matplotlib.pyplot as plt
import numpy as np
from bluesky.preprocessors import subs_wrapper
from bluesky.utils import Msg
from lmfit.model import ModelResult
from matplotlib.axes import Axes
from ophyd_async.plan_stubs import ensure_connected

from ibex_bluesky_core.callbacks import ISISCallbacks
from ibex_bluesky_core.devices.simpledae import (
    MultiRegionOfInterestReducer,
    PeriodPerPointController,
    SimpleDae,
    Waiter,
    check_dae_strategies,
)
from ibex_bluesky_core.fitting import FitMethod
from ibex_bluesky_core.plan_stubs import call_qt_aware
from ibex_bluesky_core.utils import average_model_results

__all__ = ["RockingScanResult", "rocking_scan"]

logger = logging.getLogger(__name__)

P = ParamSpec("P")


class RockingScanResult(TypedDict):
    """Result from the rocking scan plan."""

    fits: dict[str, ModelResult | None]
    """Fit of each region of interest, keyed by ROI name. A value is :py:obj:`None` if
    that fit failed."""
    fit_avg: ModelResult | None
    """Average fit of all regions of interest, or :py:obj:`None` if any fit failed."""


def _region_callbacks(
    reducer: MultiRegionOfInterestReducer,
    roi_name: str,
    x: str,
    ax: Axes,
    fit_method: FitMethod,
) -> ISISCallbacks:
    """Create the standard set of callbacks, including a fit, for a single ROI."""
    return ISISCallbacks(
        x=x,
        y=getattr(reducer, roi_name).name,
        yerr=getattr(reducer, f"{roi_name}_err").name,
        fit=fit_method,
        add_peak_stats=False,
        ax=ax,
        live_fit_logger_postfix=f"_{roi_name}",
        human_readable_file_postfix=f"_{roi_name}",
        save_plot_to_png=False,
        set_title_to_fit_result=True,
    )


def rocking_scan(
    dae: SimpleDae[PeriodPerPointController, Waiter, MultiRegionOfInterestReducer],
    *,
    x: str,
    fit_method: FitMethod,
    average_method: Callable[[Sequence[ModelResult]], ModelResult] = average_model_results,
) -> Callable[
    [Callable[P, Generator[Msg, None, Any]]],
    Callable[P, Generator[Msg, None, RockingScanResult]],
]:
    """SANS rocking scan decorator.

    Decorates a plan, fitting the same model independently to each region of interest
    exposed by the DAE's
    :py:obj:`~ibex_bluesky_core.devices.simpledae.MultiRegionOfInterestReducer`. Once the
    plan has finished, the fits are averaged.

    The decorated plan is responsible for moving axes, configuring the DAE (for example,
    setting the number of periods) and reading *dae* at each point. Calling the decorated
    plan returns a :py:obj:`RockingScanResult` instead of the plan's own return value.
    For example::

        @rocking_scan(dae, x=block.name, fit_method=Gaussian.fit())
        def my_scan(start: float, stop: float, num: int):
            yield from bps.mv(dae.number_of_periods, num)
            yield from bp.scan([dae], block, start, stop, num=num)


        result = yield from my_scan(-1, 1, 21)

    Args:
        dae: The DAE being read by the plan. Its reducer must have at least one ROI.
        x: Name of the field to use as the independent variable in fits and plots,
            typically the name of the scanned movable.
        fit_method: Method of fitting to apply to each region.
        average_method: Method of averaging the results from the fits of all ROIs.

    Returns:
        A decorator which wraps a plan function.

    """

    def decorator(
        f: Callable[P, Generator[Msg, None, Any]],
    ) -> Callable[P, Generator[Msg, None, RockingScanResult]]:
        @functools.wraps(f)
        def wrapper(*args: P.args, **kwargs: P.kwargs) -> Generator[Msg, None, RockingScanResult]:
            return (
                yield from _rocking_scan_wrapper(
                    f(*args, **kwargs),
                    dae,
                    x=x,
                    fit_method=fit_method,
                    average_method=average_method,
                )
            )

        return wrapper

    return decorator


def _rocking_scan_wrapper(
    plan: Generator[Msg, None, Any],
    dae: SimpleDae[PeriodPerPointController, Waiter, MultiRegionOfInterestReducer],
    *,
    x: str,
    fit_method: FitMethod,
    average_method: Callable[[Sequence[ModelResult]], ModelResult],
) -> Generator[Msg, None, RockingScanResult]:
    logger.info("Starting rocking scan")

    check_dae_strategies(
        dae,
        expected_controller=PeriodPerPointController,
        expected_reducer=MultiRegionOfInterestReducer,
    )

    roi_names = list(dae.reducer.detector_rois)

    yield from ensure_connected(dae)
    yield from call_qt_aware(plt.close, "all")
    _, axes = yield from call_qt_aware(plt.subplots, nrows=len(roi_names), squeeze=False)

    callbacks = {
        roi_name: _region_callbacks(dae.reducer, roi_name, x, ax, fit_method)
        for roi_name, ax in zip(roi_names, np.ravel(axes), strict=True)
    }

    yield from subs_wrapper(plan, [sub for cb in callbacks.values() for sub in cb.subs])

    fits = {roi_name: cb.live_fit.result for roi_name, cb in callbacks.items()}
    fits_values = list(fits.values())

    none_indices = [i for i, v in enumerate(fits_values) if v is None]
    if not none_indices:
        fit_avg = average_method(fits_values)
    else:
        for i in none_indices:
            logger.warning("Fit for ROI '%s' is None", list(fits)[i])
        fit_avg = None

    logger.info("Finished rocking scan, fits = %s, avg = %s", fits, fit_avg)

    return {
        "fits": fits,
        "fit_avg": fit_avg,
    }

"""Reflectometry rocking scan plan."""

import functools
import logging
from collections.abc import Callable, Generator
from typing import Any, ParamSpec, TypedDict

import matplotlib.pyplot as plt
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

    fit_a: ModelResult | None
    """Fit of region A, or :py:obj:`None` if the fit failed."""
    fit_b: ModelResult | None
    """Fit of region B, or :py:obj:`None` if the fit failed."""
    fit_avg: ModelResult | None
    "Average fit of regions A and B, or :py:obj:`None` if either fit failed."


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
    roi_a: str,
    roi_b: str,
    fit_method: FitMethod,
    average_method: Callable[[ModelResult, ModelResult], ModelResult] = average_model_results,
) -> Callable[
    [Callable[P, Generator[Msg, None, Any]]],
    Callable[P, Generator[Msg, None, RockingScanResult]],
]:
    """Rocking scan decorator.

    Decorates a plan, fitting the same model independently to each of two
    regions of interest exposed by the DAE's
    :py:obj:`~ibex_bluesky_core.devices.simpledae.MultiRegionOfInterestReducer`. Once the
    plan has finished, the two fits are averaged.

    The decorated plan is responsible for moving axes, configuring the DAE (for example,
    setting the number of periods) and reading *dae* at each point. Calling the decorated
    plan returns a :py:obj:`RockingScanResult` instead of the plan's own return value.
    For example::

        @rocking_scan(dae, x=block.name, roi_a="a", roi_b="b")
        def my_scan(start: float, stop: float, num: int):
            yield from bps.mv(dae.number_of_periods, num)
            yield from bp.scan([dae], block, start, stop, num=num)


        result = yield from my_scan(-1, 1, 21)

    Args:
        dae: The DAE being read by the plan. Its reducer must expose both *roi_a* and *roi_b*.
        x: Name of the field to use as the independent variable in fits and plots,
            typically the name of the scanned movable.
        roi_a: Name of the first region of interest on the reducer.
        roi_b: Name of the second region of interest on the reducer.
        fit_method: Method of fitting to apply to each region.
        average_method: Method of averaging the results from the fits of the two ROIs.

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
                    roi_a=roi_a,
                    roi_b=roi_b,
                    fit_method=fit_method,
                    average_method=average_method,
                )
            )

        return wrapper

    return decorator


def _rocking_scan_wrapper(  # ruff:ignore[too-many-arguments]
    plan: Generator[Msg, None, Any],
    dae: SimpleDae[PeriodPerPointController, Waiter, MultiRegionOfInterestReducer],
    *,
    x: str,
    roi_a: str,
    roi_b: str,
    fit_method: FitMethod,
    average_method: Callable[[ModelResult, ModelResult], ModelResult],
) -> Generator[Msg, None, RockingScanResult]:
    logger.info("Starting rocking scan")
    check_dae_strategies(
        dae,
        expected_controller=PeriodPerPointController,
        expected_reducer=MultiRegionOfInterestReducer,
    )
    reducer = dae.reducer

    yield from ensure_connected(dae)

    yield from call_qt_aware(plt.close, "all")
    _, (ax_a, ax_b) = yield from call_qt_aware(plt.subplots, nrows=2)

    callbacks_a = _region_callbacks(reducer, roi_a, x, ax_a, fit_method)
    callbacks_b = _region_callbacks(reducer, roi_b, x, ax_b, fit_method)

    yield from subs_wrapper(plan, callbacks_a.subs + callbacks_b.subs)

    fit_a = callbacks_a.live_fit.result
    fit_b = callbacks_b.live_fit.result
    fit_avg = None if not (fit_a and fit_b) else average_method(fit_a, fit_b)

    logger.info(
        "Finished rocking scan, fit A = %s, fit B = %s, avg = %s",
        fit_a,
        fit_b,
        fit_avg,
    )

    return {
        "fit_a": fit_a,
        "fit_b": fit_b,
        "fit_avg": fit_avg,
    }

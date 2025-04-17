"""Reflectometry detector-mapping alignment plans."""

import logging
from collections.abc import Generator
from typing import TypedDict

import bluesky.plan_stubs as bps
import bluesky.plans as bp
import matplotlib.pyplot as plt
import numpy as np
import numpy.typing as npt
from bluesky.preprocessors import subs_decorator
from bluesky.protocols import NamedMovable
from bluesky.utils import Msg
from lmfit.model import ModelResult
from matplotlib.axes import Axes
from ophyd_async.plan_stubs import ensure_connected

from ibex_bluesky_core.callbacks import ISISCallbacks, LiveFit
from ibex_bluesky_core.callbacks.reflectometry import (
    DetMapAngleScanLiveDispatcher,
    DetMapHeightScanLiveDispatcher,
    LivePColorMesh,
)
from ibex_bluesky_core.devices.simpledae import (
    PeriodPerPointController,
    PeriodSpecIntegralsReducer,
    SimpleDae,
    Waiter,
    check_dae_strategies,
)
from ibex_bluesky_core.fitting import Gaussian
from ibex_bluesky_core.plan_stubs import call_qt_aware

__all__ = ["DetMapAlignResult", "angle_scan_plan", "height_and_angle_scan_plan"]


logger = logging.getLogger(__name__)


def _height_scan_callback_and_fit(
    reducer: PeriodSpecIntegralsReducer, height: NamedMovable[float], ax: Axes
) -> tuple[DetMapHeightScanLiveDispatcher, LiveFit]:
    intensity = "intensity"
    height_scan_ld = DetMapHeightScanLiveDispatcher(
        mon_name=reducer.mon_integrals.name,
        det_name=reducer.det_integrals.name,
        out_name=intensity,
    )

    height_scan_callbacks = ISISCallbacks(
        x=height.name,
        y=intensity,
        yerr=f"{intensity}_err",
        fit=Gaussian().fit(),
        add_peak_stats=False,
        ax=ax,
        live_fit_logger_postfix="_height",
        human_readable_file_postfix="_height",
    )
    for cb in height_scan_callbacks.subs:
        height_scan_ld.subscribe(cb)

    return height_scan_ld, height_scan_callbacks.live_fit


def _angle_scan_callback_and_fit(
    reducer: PeriodSpecIntegralsReducer, angle_map: npt.NDArray[np.float64], ax: Axes
) -> tuple[DetMapAngleScanLiveDispatcher, LiveFit]:
    angle_name = "angle"
    counts_name = "counts"

    angle_scan_ld = DetMapAngleScanLiveDispatcher(
        x_data=angle_map,
        x_name=angle_name,
        y_in_name=reducer.det_integrals.name,
        y_out_name=counts_name,
    )

    angle_scan_callbacks = ISISCallbacks(
        x=angle_name,
        y=counts_name,
        yerr=f"{counts_name}_err",
        fit=Gaussian().fit(),
        add_peak_stats=False,
        add_table_cb=False,
        ax=ax,
        live_fit_logger_postfix="_angle",
        human_readable_file_postfix="_angle",
    )
    for cb in angle_scan_callbacks.subs:
        angle_scan_ld.subscribe(cb)

    return angle_scan_ld, angle_scan_callbacks.live_fit


def _check_angle_map_shape(
    reducer: PeriodSpecIntegralsReducer,
    angle_map: npt.NDArray[np.float64],
) -> None:
    if reducer.detectors.shape != angle_map.shape:
        raise ValueError(
            f"detectors ({reducer.detectors.shape}) and "
            f"angle_map ({angle_map.shape}) must have same shape"
        )


def angle_scan_plan(
    dae: SimpleDae[PeriodPerPointController, Waiter, PeriodSpecIntegralsReducer],
    *,
    angle_map: npt.NDArray[np.float64],
) -> Generator[Msg, None, ModelResult | None]:
    """Reflectometry detector-mapping angle alignment plan.

    This plan does not move any axes, but takes a single DAE measurement at the current
    position. It processes this single DAE measurement to produce an angle scan, mapping
    the detector intensity against angular pixel position.

    Args:
        dae: The DAE to acquire from
        angle_map: a numpy array, with the same shape as detectors,
            describing the detector angle of each detector pixel

    """
    logger.info("Starting angle scan")
    check_dae_strategies(
        dae,
        expected_controller=PeriodPerPointController,
        expected_reducer=PeriodSpecIntegralsReducer,
    )
    reducer = dae.reducer
    _check_angle_map_shape(reducer, angle_map)

    yield from ensure_connected(dae)

    yield from call_qt_aware(plt.close, "all")
    _, ax = yield from call_qt_aware(plt.subplots)

    angle_cb, angle_fit = _angle_scan_callback_and_fit(reducer, angle_map, ax)

    @subs_decorator(
        [
            angle_cb,
        ]
    )
    def _inner() -> Generator[Msg, None, None]:
        yield from bp.count([dae])

    yield from _inner()

    logger.info("Finished angle scan, result = %s", angle_fit.result)

    return angle_fit.result


class DetMapAlignResult(TypedDict):
    """Result from mapping alignment plan.

    Keys:
        height_fit:
            An lmfit ModelResult object describing the height fit,
            if the fit succeeded, or None otherwise.
        angle_fit:
            An lmfit ModelResult object describing the angle fit,
            if the fit succeeded, or None otherwise.
    """

    height_fit: ModelResult | None
    angle_fit: ModelResult | None


def height_and_angle_scan_plan(  # noqa PLR0913
    dae: SimpleDae[PeriodPerPointController, Waiter, PeriodSpecIntegralsReducer],
    height: NamedMovable[float],
    start: float,
    stop: float,
    *,
    num: int,
    angle_map: npt.NDArray[np.float64],
    rel: bool = False,
) -> Generator[Msg, None, DetMapAlignResult]:
    """Reflectometry detector-mapping simultaneous height & angle alignment plan.

    This plan does a step scan over the specified height axis, taking *num* measurements
    from the DAE, evenly spaced between *start* and *stop*.

    Args:
        dae: The DAE to acquire from
        height: A bluesky Movable corresponding to a height stage
        start: start point for scan
        stop: stop point for scan
        num: how many points to measure
        angle_map: a numpy array, with the same shape as detectors,
            describing the detector angle of each detector pixel
        rel: whether this scan should be absolute (default) or relative

    Returns:
        A dictionary containing the fit results from gaussian height and angle fits.

    """
    logger.info("Starting combined height and angle scan")
    check_dae_strategies(
        dae,
        expected_controller=PeriodPerPointController,
        expected_reducer=PeriodSpecIntegralsReducer,
    )

    reducer = dae.reducer
    _check_angle_map_shape(reducer, angle_map)

    yield from ensure_connected(height, dae)  # type: ignore

    yield from call_qt_aware(plt.close, "all")
    _, (grid_ax, height_ax, angle_ax) = yield from call_qt_aware(plt.subplots, nrows=3)

    live_grid = LivePColorMesh(
        x=reducer.det_integrals.name,
        y=height.name,
        x_name="angle",
        x_coord=angle_map,
        ax=grid_ax,
        cmap="hot",
        shading="auto",
    )
    height_cb, height_fit = _height_scan_callback_and_fit(reducer, height, height_ax)
    angle_cb, angle_fit = _angle_scan_callback_and_fit(reducer, angle_map, angle_ax)

    @subs_decorator(
        [
            live_grid,
            height_cb,
            angle_cb,
        ]
    )
    def _inner() -> Generator[Msg, None, None]:
        nonlocal start, stop, num
        yield from bps.mv(dae.number_of_periods, num)
        plan = bp.rel_scan if rel else bp.scan
        yield from plan([dae], height, start, stop, num=num)

    yield from _inner()

    logger.info(
        "Finished height and angle scan, height result = %s, angle result = %s",
        height_fit.result,
        angle_fit.result,
    )

    return {
        "height_fit": height_fit.result,
        "angle_fit": angle_fit.result,
    }

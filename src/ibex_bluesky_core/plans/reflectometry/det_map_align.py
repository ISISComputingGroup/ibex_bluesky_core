"""Implements detector-mapping alignment."""

from collections.abc import Generator

import bluesky.plans as bp
import matplotlib.pyplot as plt
import numpy as np
import numpy.typing as npt
from bluesky.preprocessors import subs_decorator
from bluesky.protocols import NamedMovable
from bluesky.utils import Msg
from matplotlib.axes import Axes
from ophyd_async.plan_stubs import ensure_connected

from ibex_bluesky_core.callbacks import ISISCallbacks, LiveFit
from ibex_bluesky_core.callbacks.fitting.fitting_utils import Gaussian
from ibex_bluesky_core.callbacks.reflectometry.det_map import (
    DetMapAngleScanLiveDispatcher,
    DetMapHeightScanLiveDispatcher,
    LivePColorMesh,
)
from ibex_bluesky_core.devices import get_pv_prefix
from ibex_bluesky_core.devices.simpledae import SimpleDae
from ibex_bluesky_core.devices.simpledae.controllers import (
    PeriodPerPointController,
)
from ibex_bluesky_core.devices.simpledae.reducers import (
    PeriodSpecIntegralsReducer,
)
from ibex_bluesky_core.devices.simpledae.waiters import PeriodGoodFramesWaiter
from ibex_bluesky_core.plan_stubs import call_qt_aware
from ibex_bluesky_core.plans import set_num_periods


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
    )
    for cb in angle_scan_callbacks.subs:
        angle_scan_ld.subscribe(cb)

    return angle_scan_ld, angle_scan_callbacks.live_fit


def _dae_and_reducer(
    frames: int, monitor: int, detectors: npt.NDArray[np.int64]
) -> tuple[SimpleDae, PeriodSpecIntegralsReducer]:
    controller = PeriodPerPointController(save_run=True)
    waiter = PeriodGoodFramesWaiter(frames)
    reducer = PeriodSpecIntegralsReducer(
        monitors=np.array([monitor], dtype=np.int64),
        detectors=detectors,
    )

    prefix = get_pv_prefix()
    dae = SimpleDae(
        prefix=prefix,
        controller=controller,
        waiter=waiter,
        reducer=reducer,
    )

    return dae, reducer


def mapping_alignment_plan(  # noqa: PLR0913, this is intentionally quite generic
    height: NamedMovable[float],
    start: float,
    stop: float,
    *,
    num: int,
    detectors: npt.NDArray[np.int64],
    monitor: int,
    angle_map: npt.NDArray[np.float64],
    frames: int,
    rel: bool = False,
) -> Generator[Msg, None, None]:
    """Reflectometry detector-mapping alignment plan.

    Args:
        height: A bluesky Movable corresponding to the height stage
        start: start point for scan
        stop: stop point for scan
        num: how many points to measure
        detectors: numpy array of detector spectra to integrate
        monitor: a single monitor spectrum to use for normalization
        angle_map: a numpy array, with the same shape as detectors,
            describing the detector angle of each detector pixel
        frames: how many frames to measure at each scan point
        rel: whether this scan should be absolute (default) or relative

    """
    if detectors.shape != angle_map.shape:
        raise ValueError(
            f"detectors ({detectors.shape}) and angle_map ({angle_map.shape}) must have same shape"
        )

    dae, reducer = _dae_and_reducer(frames, monitor, detectors)
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
        yield from set_num_periods(dae, num)
        if rel:
            plan = bp.rel_scan
        else:
            plan = bp.scan
        yield from plan([dae], height, start, stop, num=num)

    yield from _inner()

    print("HEIGHT FIT:")
    print(height_fit.result.fit_report(show_correl=False))
    print("\n\n")
    print("ANGLE FIT:")
    print(angle_fit.result.fit_report(show_correl=False))
    print("\n\n")

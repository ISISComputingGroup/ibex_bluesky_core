"""e.g.
RE(scan("S4VG", -1, 1, 25, frames=20, model=fitting_utils.SlitScan())).
"""

from pathlib import Path

import bluesky.plans as bp
import bluesky.preprocessors as bpp
import matplotlib
import matplotlib.pyplot as plt
from bluesky.callbacks import LiveFitPlot, LiveTable
from ophyd_async.plan_stubs import ensure_connected

from ibex_bluesky_core.callbacks.file_logger import HumanReadableFileCallback
from ibex_bluesky_core.callbacks.fitting import FitMethod, LiveFit
from ibex_bluesky_core.callbacks.fitting.fitting_utils import Fit, Linear
from ibex_bluesky_core.callbacks.fitting.livefit_logger import LiveFitLogger
from ibex_bluesky_core.callbacks.plotting import LivePlot
from ibex_bluesky_core.devices import get_pv_prefix
from ibex_bluesky_core.devices.simpledae import SimpleDae
from ibex_bluesky_core.devices.simpledae.controllers import (
    PeriodPerPointController,
    RunPerPointController,
)
from ibex_bluesky_core.devices.simpledae.reducers import MonitorNormalizer
from ibex_bluesky_core.devices.simpledae.waiters import GoodFramesWaiter, PeriodGoodFramesWaiter
from ibex_bluesky_core.plan_stubs import call_qt_aware
from ibex_bluesky_core.plans import set_num_periods
from ibex_bluesky_core.plans.reflectometry import centred_pixel, refl_parameter
from ibex_bluesky_core.run_engine import get_run_engine

matplotlib.rcParams["figure.autolayout"] = True
matplotlib.rcParams["font.size"] = 8

RE = get_run_engine()

DEFAULT_DET = 3
DEFAULT_MON = 1

READABLE_FILE_OUTPUT_DIR = Path("C:\\") / "instrument" / "var" / "logs" / "bluesky" / "output_files"


def crisp_dae(
    *,
    det_pixels: list[int],
    frames: int,
    periods: bool = True,
    monitor: int = 1,
    save_run: bool = False,
) -> SimpleDae:
    prefix = get_pv_prefix()

    if periods:
        controller = PeriodPerPointController(save_run=save_run)
        waiter = PeriodGoodFramesWaiter(frames)
    else:
        controller = RunPerPointController(save_run=save_run)
        waiter = GoodFramesWaiter(frames)

    reducer = MonitorNormalizer(
        prefix=prefix,
        detector_spectra=det_pixels,
        monitor_spectra=[monitor],
    )

    dae = SimpleDae(
        prefix=prefix,
        controller=controller,
        waiter=waiter,
        reducer=reducer,
    )

    dae.reducer.intensity.set_name("intensity")  # type: ignore
    dae.reducer.intensity_stddev.set_name("intensity_stddev")  # type: ignore
    return dae


def scan(
    param: str,
    start: float,
    stop: float,
    count: int,
    *,
    frames: int,
    det: int = DEFAULT_DET,
    mon: int = DEFAULT_MON,
    pixel_range: int = 0,
    model: FitMethod = Linear().fit(),
    periods: bool = True,
    save_run: bool = False,
    rel: bool = False,
):
    block = refl_parameter(param)
    det_pixels = centred_pixel(det, pixel_range)
    dae = crisp_dae(
        det_pixels=det_pixels, frames=frames, periods=periods, save_run=save_run, monitor=mon
    )

    yield from ensure_connected(dae, block)

    yield from set_num_periods(dae, count if periods else 1)

    yield from call_qt_aware(plt.close, "all")
    _, ax = yield from call_qt_aware(plt.subplots)

    livefit = LiveFit(
        model,
        y=dae.reducer.intensity.name,
        yerr=dae.reducer.intensity_stddev.name,
        x=block.name,  # type: ignore
    )

    fields = [block.name]
    if periods:
        fields.append(dae.period_num.name)  # type: ignore
    elif save_run:
        fields.append(dae.controller.run_number.name)  # type: ignore

    fields.extend(
        [
            dae.reducer.intensity.name,  # type: ignore
            dae.reducer.intensity_stddev.name,  # type: ignore
        ]
    )

    @bpp.subs_decorator(
        [
            HumanReadableFileCallback(output_dir=READABLE_FILE_OUTPUT_DIR, fields=fields),
            LivePlot(
                y=dae.reducer.intensity.name,  # type: ignore
                yerr=dae.reducer.intensity_stddev.name,  # type: ignore
                x=block.name,
                marker="x",
                linestyle="none",
                ax=ax,
            ),
            LiveFitLogger(
                livefit,
                y=dae.reducer.intensity.name,  # type: ignore
                x=block.name,  # type: ignore
                output_dir=READABLE_FILE_OUTPUT_DIR,
                postfix="fit_2",
                yerr=dae.reducer.intensity_stddev.name,  # type: ignore
            ),
            LiveTable(fields),
            LiveFitPlot(livefit, ax=ax),
        ]
    )
    def _inner():
        if rel:
            plan = bp.rel_scan
        else:
            plan = bp.scan
        yield from plan([dae], block, start, stop, num=count)

    yield from _inner()

    print(f"Files written to {READABLE_FILE_OUTPUT_DIR}\n")

    if livefit.result is not None:
        print(livefit.result.fit_report())
        return livefit.result.params
    else:
        print("No LiveFit result, likely fit failed")
        return None


def adaptive_scan(
    param: str,
    start: float,
    stop: float,
    min_step: float,
    max_step: float,
    target_delta: float,
    *,
    frames: int,
    det: int = DEFAULT_DET,
    mon: int = DEFAULT_MON,
    pixel_range: int = 0,
    model: Fit = Linear(),
    periods: bool = True,
    save_run: bool = False,
    rel: bool = False,
):
    block = refl_parameter(param)
    det_pixels = centred_pixel(det, pixel_range)
    dae = crisp_dae(
        det_pixels=det_pixels, frames=frames, periods=periods, save_run=save_run, monitor=mon
    )

    yield from ensure_connected(dae, block)

    yield from set_num_periods(dae, 100)

    yield from call_qt_aware(plt.close, "all")
    _, ax = yield from call_qt_aware(plt.subplots)

    livefit = LiveFit(
        model.fit(),
        y=dae.reducer.intensity.name,
        yerr=dae.reducer.intensity_stddev.name,
        x=block.name,  # type: ignore
    )

    fields = [block.name]
    if periods:
        fields.append(dae.period_num.name)  # type: ignore
    elif save_run:
        fields.append(dae.controller.run_number.name)  # type: ignore

    fields.extend(
        [
            dae.reducer.intensity.name,  # type: ignore
            dae.reducer.intensity_stddev.name,  # type: ignore
        ]
    )

    @bpp.subs_decorator(
        [
            HumanReadableFileCallback(READABLE_FILE_OUTPUT_DIR, fields),
            LivePlot(
                y=dae.reducer.intensity.name,  # type: ignore
                yerr=dae.reducer.intensity_stddev.name,  # type: ignore
                x=block.name,
                marker="x",
                linestyle="none",
                ax=ax,
            ),
            LiveFitLogger(
                livefit,
                y=dae.reducer.intensity.name,  # type: ignore
                x=block.name,  # type: ignore
                output_dir=READABLE_FILE_OUTPUT_DIR,
                postfix="fit_1",
                yerr=dae.reducer.intensity_stddev.name,  # type: ignore
            ),
            LiveTable(fields),
            LiveFitPlot(livefit, ax=ax),
        ]
    )
    def _inner():
        if rel:
            plan = bp.rel_adaptive_scan
        else:
            plan = bp.adaptive_scan
        yield from plan(
            [dae],
            dae.reducer.intensity.name,
            block,
            start,
            stop,
            min_step,
            max_step,
            target_delta,
            backstep=True,
        )  # type: ignore

    yield from _inner()

    print(f"Files written to {READABLE_FILE_OUTPUT_DIR}\n")

    if livefit.result is not None:
        print(livefit.result.fit_report())
        return livefit.result.params
    else:
        print("No LiveFit result, likely fit failed")
        return None

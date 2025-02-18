"""CRISP specific plans."""

from collections.abc import Generator

import bluesky.plans as bp
import matplotlib
from bluesky.utils import Msg
from ophyd_async.plan_stubs import ensure_connected

from ibex_bluesky_core.callbacks import ISISCallbacks
from ibex_bluesky_core.callbacks.fitting import FitMethod
from ibex_bluesky_core.callbacks.fitting.fitting_utils import Linear
from ibex_bluesky_core.devices.simpledae import SimpleDae
from ibex_bluesky_core.plans import common_dae, set_num_periods
from ibex_bluesky_core.plans.reflectometry import centred_pixel, refl_parameter
from ibex_bluesky_core.run_engine import get_run_engine

matplotlib.rcParams["figure.autolayout"] = True
matplotlib.rcParams["font.size"] = 8

RE = get_run_engine()

DEFAULT_DET = 3
DEFAULT_MON = 1

LINEAR_FIT = Linear().fit()


def crisp_dae(
    *,
    det_pixels: list[int],
    frames: int,
    periods: bool = True,
    monitor: int = 1,
    save_run: bool = False,
) -> SimpleDae:
    return common_dae(
        det_pixels=det_pixels, frames=frames, periods=periods, monitor=monitor, save_run=save_run
    )


def scan(  # noqa: PLR0913
    param: str,
    start: float,
    stop: float,
    count: int,
    *,
    frames: int,
    det: int = DEFAULT_DET,
    mon: int = DEFAULT_MON,
    pixel_range: int = 0,
    model: FitMethod = LINEAR_FIT,
    periods: bool = True,
    save_run: bool = False,
    rel: bool = False,
) -> Generator[Msg, None, None]:
    block = refl_parameter(param)
    det_pixels = centred_pixel(det, pixel_range)
    dae = crisp_dae(
        det_pixels=det_pixels, frames=frames, periods=periods, save_run=save_run, monitor=mon
    )

    yield from ensure_connected(dae, block)

    yield from set_num_periods(dae, count if periods else 1)

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

    icc = ISISCallbacks(
        y=dae.reducer.intensity.name,  # type: ignore
        yerr=dae.reducer.intensity_stddev.name,  # type: ignore
        x=block.name,
        live_fit_logger_postfix="fit_2",
        measured_fields=fields,
        fit=model,
    )

    @icc
    def _inner() -> Generator[Msg, None, None]:
        if rel:
            plan = bp.rel_scan
        else:
            plan = bp.scan
        yield from plan([dae], block, start, stop, num=count)

    yield from _inner()

    if icc.live_fit.result is not None:
        print(icc.live_fit.result.fit_report())
        return icc.live_fit.result.params
    else:
        print("No LiveFit result, likely fit failed")
        return None


def adaptive_scan(  # noqa: PLR0913
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
    model: FitMethod = LINEAR_FIT,
    periods: bool = True,
    save_run: bool = False,
    rel: bool = False,
) -> Generator[Msg, None, None]:
    block = refl_parameter(param)
    det_pixels = centred_pixel(det, pixel_range)
    dae = crisp_dae(
        det_pixels=det_pixels, frames=frames, periods=periods, save_run=save_run, monitor=mon
    )

    yield from ensure_connected(dae, block)

    yield from set_num_periods(dae, 100)

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

    icc = ISISCallbacks(
        y=dae.reducer.intensity.name,  # type: ignore
        yerr=dae.reducer.intensity_stddev.name,  # type: ignore
        x=block.name,
        live_fit_logger_postfix="fit_1",
        measured_fields=fields,
        fit=model,
    )

    @icc
    def _inner() -> Generator[Msg, None, None]:
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
    if icc.live_fit.result is not None:
        print(icc.live_fit.result.fit_report())
        return icc.live_fit.result.params
    else:
        print("No LiveFit result, likely fit failed")
        return None

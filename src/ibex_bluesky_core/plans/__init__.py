"""Generic plan helpers."""

from collections.abc import Generator

import bluesky.plans as bp
from bluesky.protocols import Movable, NamedMovable
from bluesky.utils import Msg
from ophyd_async.core import Device
from ophyd_async.plan_stubs import ensure_connected

from ibex_bluesky_core.callbacks import FitMethod, ISISCallbacks
from ibex_bluesky_core.callbacks.fitting.fitting_utils import Linear
from ibex_bluesky_core.devices import get_pv_prefix
from ibex_bluesky_core.devices.block import BlockMot
from ibex_bluesky_core.devices.block import block_mot as block_mot
from ibex_bluesky_core.devices.dae import common_dae
from ibex_bluesky_core.devices.simpledae import SimpleDae
from ibex_bluesky_core.plan_stubs import set_num_periods
from ibex_bluesky_core.utils import centred_pixel

DEFAULT_DET = 3
DEFAULT_FIT_METHOD = Linear().fit()


def scan(  # noqa: PLR0913
    dae: SimpleDae,
    block: NamedMovable,
    start: float,
    stop: float,
    count: int,
    *,
    model: FitMethod = DEFAULT_FIT_METHOD,
    periods: bool = True,
    save_run: bool = False,
    rel: bool = False,
) -> Generator[Msg, None, ISISCallbacks]:
    """Scan the DAE against a Movable.

    Args: TODO sort docstring out
        block_name: the name of the block to move.
        start: the starting position of the block.
        stop: the final position of the block.
        count: the number of points to make.
        frames: the number of frames to wait for.
        det: the detector spectra to use.
        mon: the monitor spectra to use for normalisation.
        model: the fit method to use.
        periods: whether or not to use hardware periods.
        save_run: whether or not to save run.
        rel: whether or not to scan around the current position or use absolute positions.

    """
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

    return icc


def adaptive_scan(  # noqa: PLR0913
    dae: SimpleDae,
    block: NamedMovable,
    start: float,
    stop: float,
    min_step: float,
    max_step: float,
    target_delta: float,
    *,
    model: FitMethod = DEFAULT_FIT_METHOD,
    periods: bool = True,
    save_run: bool = False,
    rel: bool = False,
) -> Generator[Msg, None, ISISCallbacks]:
    """Scan the DAE against a block using an adaptive scan.

    This will scan coarsely until target_delta occurs, then it will go back and perform finer scans.

    Args: TODO sort docstring out
        block_name: the name of the block to move.
        start: the starting position of the block.
        stop: the final position of the block.
        min_step: smallest step for fine regions.
        max_step: largest step for coarse regions.
        target_delta: desired fractional change in detector signal between steps
        frames: the number of frames to wait for.
        det: the detector spectra to use.
        mon: the monitor spectra to use for normalisation.
        model: the fit method to use.
        periods: whether or not to use hardware periods.
        save_run: whether or not to save run.
        rel: whether or not to scan around the current position or use absolute positions.

    """
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
            detectors=[dae],
            target_field=dae.reducer.intensity.name,
            motor=block,
            start=start,
            stop=stop,
            min_step=min_step,
            max_step=max_step,
            target_delta=target_delta,
            backstep=True,
        )  # type: ignore

    yield from _inner()

    return icc


DEFAULT_DET = 3
DEFAULT_MON = 1
LINEAR_FIT = Linear().fit()


def motor_scan(
    block_name: str,
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
):
    """TODO add docstring"""
    block = BlockMot(prefix=get_pv_prefix(), block_name=block_name)
    det_pixels = centred_pixel(det, pixel_range)
    dae = common_dae(
        det_pixels=det_pixels, frames=frames, periods=periods, save_run=save_run, monitor=mon
    )

    icc = yield from scan(
        dae, block, start, stop, count, model=model, save_run=save_run, periods=periods, rel=rel
    )

    if icc.live_fit.result is not None:
        print(icc.live_fit.result.fit_report())
        return icc.live_fit.result.params
    else:
        print("No LiveFit result, likely fit failed")
        return None


def motor_adaptive_scan(
    block_name: str,
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
):
    """TODO add docstring"""
    block = BlockMot(prefix=get_pv_prefix(), block_name=block_name)
    det_pixels = centred_pixel(det, pixel_range)
    dae = common_dae(
        det_pixels=det_pixels, frames=frames, periods=periods, save_run=save_run, monitor=mon
    )

    icc = yield from adaptive_scan(
        dae=dae,
        block=block,
        start=start,
        stop=stop,
        min_step=min_step,
        max_step=max_step,
        target_delta=target_delta,
        model=model,
        save_run=save_run,
        rel=rel,
    )
    if icc.live_fit.result is not None:
        print(icc.live_fit.result.fit_report())
        return icc.live_fit.result.params
    else:
        print("No LiveFit result, likely fit failed")
        return None

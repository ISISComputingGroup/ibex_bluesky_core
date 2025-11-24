"""Generic plans."""

from collections.abc import Generator
from typing import TYPE_CHECKING, Any

import bluesky.plans as bp
import matplotlib.pyplot as plt
from bluesky import plan_stubs as bps
from bluesky.protocols import NamedMovable
from bluesky.utils import Msg
from matplotlib.axes import Axes
from ophyd_async.plan_stubs import ensure_connected

from ibex_bluesky_core.callbacks import ISISCallbacks
from ibex_bluesky_core.devices.block import BlockWriteConfig, block_rw
from ibex_bluesky_core.devices.simpledae import monitor_normalising_dae
from ibex_bluesky_core.fitting import FitMethod
from ibex_bluesky_core.plan_stubs import call_qt_aware, polling_plan
from ibex_bluesky_core.utils import NamedReadableAndMovable, centred_pixel

if TYPE_CHECKING:
    from ibex_bluesky_core.devices.simpledae import SimpleDae

__all__ = [
    "NamedReadableAndMovable",
    "adaptive_scan",
    "motor_adaptive_scan",
    "motor_scan",
    "polling_plan",
    "scan",
]


def _get_additional_md(
    dae: "SimpleDae", *, periods: bool, save_run: bool
) -> Generator[Msg, None, dict[str, Any]]:
    if periods and save_run:
        run_number = yield from bps.rd(dae.current_or_next_run_number_str)
        return {"run_number": run_number}
    else:
        yield from bps.null()
        return {}


def scan(  # noqa: PLR0913
    dae: "SimpleDae",
    block: NamedMovable[float],
    start: float,
    stop: float,
    num: int,
    *,
    model: FitMethod | None = None,
    periods: bool = True,
    save_run: bool = False,
    rel: bool = False,
    md: dict[Any, Any] | None = None,
) -> Generator[Msg, None, ISISCallbacks]:
    """Scan the DAE against a Movable.

    Args:
        dae: the simple DAE object to use.
        block: a movable to move during the scan.
        start: the starting position.
        stop: the final position.
        num: the number of points to make.
        model: the fit method to use.
        periods: whether or not to use software periods.
        save_run: whether or not to save run.
        rel: whether or not to scan around the current position or use absolute positions.
        md: Arbitrary metadata to include in this scan.

    """
    yield from ensure_connected(dae, block)  # type: ignore

    yield from call_qt_aware(plt.close, "all")
    _, ax = yield from call_qt_aware(plt.subplots)

    yield from bps.mv(dae.number_of_periods, num if periods else 1)

    icc = _set_up_fields_and_icc(block, dae, model, periods, save_run, ax)

    additional_md = yield from _get_additional_md(dae, periods=periods, save_run=save_run)

    @icc
    def _inner() -> Generator[Msg, None, None]:
        if rel:
            plan = bp.rel_scan
        else:
            plan = bp.scan
        yield from plan([dae], block, start, stop, num=num, md=additional_md | (md or {}))

    yield from _inner()

    return icc


def _set_up_fields_and_icc(
    block: NamedMovable[Any],
    dae: "SimpleDae",
    model: FitMethod | None,
    periods: bool,
    save_run: bool,
    ax: Axes,
) -> ISISCallbacks:
    fields = [block.name]
    if periods:
        fields.append(dae.period_num.name)  # type: ignore
    elif save_run:
        fields.append(dae.controller.run_number.name)  # type: ignore
    icc = ISISCallbacks(
        y=dae.reducer.intensity.name,  # type: ignore
        yerr=dae.reducer.intensity_stddev.name,  # type: ignore
        x=block.name,
        measured_fields=fields,
        fit=model,
        ax=ax,
    )
    return icc


def adaptive_scan(  # noqa: PLR0913, PLR0917
    dae: "SimpleDae",
    block: NamedMovable[float],
    start: float,
    stop: float,
    min_step: float,
    max_step: float,
    target_delta: float,
    *,
    model: FitMethod | None = None,
    periods: bool = True,
    save_run: bool = False,
    rel: bool = False,
    md: dict[Any, Any] | None = None,
) -> Generator[Msg, None, ISISCallbacks]:
    """Scan the DAE against a block using an adaptive scan.

    This will scan coarsely until target_delta occurs, then it will go back and perform finer scans.

    Args:
        dae: the simple DAE object to use.
        block: a movable to move during the scan.
        start: the starting position of the block.
        stop: the final position of the block.
        min_step: smallest step for fine regions.
        max_step: largest step for coarse regions.
        target_delta: desired fractional change in detector signal between steps
        model: the fit method to use.
        periods: whether or not to use software periods.
        save_run: whether or not to save run.
        rel: whether or not to scan around the current position or use absolute positions.
        md: Arbitrary metadata to include in this scan.

    Returns:
        an :obj:`ibex_bluesky_core.callbacks.ISISCallbacks` instance.

    """
    yield from ensure_connected(dae, block)  # type: ignore
    if periods:
        max_periods = yield from bps.rd(dae.max_periods)
        yield from bps.mv(dae.number_of_periods, max_periods)

    yield from call_qt_aware(plt.close, "all")
    _, ax = yield from call_qt_aware(plt.subplots)

    icc = _set_up_fields_and_icc(block, dae, model, periods, save_run, ax)

    additional_md = yield from _get_additional_md(dae, periods=periods, save_run=save_run)

    @icc
    def _inner() -> Generator[Msg, None, None]:
        if rel:
            plan = bp.rel_adaptive_scan
        else:
            plan = bp.adaptive_scan
        yield from plan(
            detectors=[dae],
            target_field=dae.reducer.intensity.name,  # type: ignore
            motor=block,
            start=start,
            stop=stop,
            min_step=min_step,
            max_step=max_step,
            target_delta=target_delta,
            backstep=True,
            md=additional_md | (md or {}),
        )  # type: ignore

    yield from _inner()

    return icc


def motor_scan(  # noqa: PLR0913
    block_name: str,
    start: float,
    stop: float,
    num: int,
    *,
    frames: int,
    det: int,
    mon: int,
    model: FitMethod | None = None,
    pixel_range: int = 0,
    periods: bool = True,
    save_run: bool = False,
    rel: bool = False,
    md: dict[Any, Any] | None = None,
) -> Generator[Msg, None, ISISCallbacks]:
    """Wrap our ``scan()`` plan and create a ``block_rw`` and a DAE object.

    This essentially uses the same mechanism as a waitfor_move by using the global "moving" flag
    to determine if motors are still moving after starting a move.
    This is really just a wrapper around :func:`ibex_bluesky_core.plans.scan`

    Args:
        block_name: the name of the block to scan.
        start: the starting position of the block.
        stop: the final position of the block.
        num: the number of points to make.
        frames: the number of frames to wait for when scanning.
        det: the detector number.
        mon: the monitor number.
        pixel_range: the range of pixels to scan over, using `det` as a centred pixel.
        model: the fit method to use.
        periods: whether or not to use software periods.
        save_run: whether or not to save run.
        rel: whether or not to scan around the current position or use absolute positions.
        md: Arbitrary metadata to include in this scan.

    Returns:
        an :obj:`ibex_bluesky_core.callbacks.ISISCallbacks` instance.

    """
    block = block_rw(
        float,
        block_name=block_name,
        write_config=BlockWriteConfig(use_global_moving_flag=True),
    )
    det_pixels = centred_pixel(det, pixel_range)
    dae = monitor_normalising_dae(
        det_pixels=det_pixels, frames=frames, periods=periods, save_run=save_run, monitor=mon
    )

    return (
        yield from scan(
            dae=dae,
            block=block,
            start=start,
            stop=stop,
            num=num,
            model=model,
            save_run=save_run,
            periods=periods,
            rel=rel,
            md=md,
        )
    )


def motor_adaptive_scan(  # noqa: PLR0913
    block_name: str,
    start: float,
    stop: float,
    min_step: float,
    max_step: float,
    target_delta: float,
    *,
    frames: int,
    det: int,
    mon: int,
    model: FitMethod | None = None,
    pixel_range: int = 0,
    periods: bool = True,
    save_run: bool = False,
    rel: bool = False,
    md: dict[Any, Any] | None = None,
) -> Generator[Msg, None, ISISCallbacks]:
    """Wrap ``adaptive_scan()`` plan and create a ``block_rw`` and a DAE object.

    This essentially uses the same mechanism as a waitfor_move by using the global "moving" flag
    to determine if motors are still moving after starting a move.
    This is really just a wrapper around :func:`ibex_bluesky_core.plans.adaptive_scan`

    Args:
        block_name: the name of the block to scan.
        start: the starting position of the block.
        stop: the final position of the block.
        min_step: smallest step for fine regions.
        max_step: largest step for coarse regions.
        target_delta: desired fractional change in detector signal between steps.
        frames: the number of frames to wait for when scanning.
        det: the detector number.
        mon: the monitor number.
        pixel_range: the range of pixels to scan over, using `det` as a centred pixel.
        model: the fit method to use.
        periods: whether or not to use software periods.
        save_run: whether or not to save run.
        rel: whether or not to scan around the current position or use absolute positions.
        md: Arbitrary metadata to include in this scan.

    Returns:
        an :obj:`ibex_bluesky_core.callbacks.ISISCallbacks` instance.

    """
    block = block_rw(
        float,
        block_name=block_name,
        write_config=BlockWriteConfig(use_global_moving_flag=True),
    )
    det_pixels = centred_pixel(det, pixel_range)
    dae = monitor_normalising_dae(
        det_pixels=det_pixels, frames=frames, periods=periods, save_run=save_run, monitor=mon
    )

    return (
        yield from adaptive_scan(
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
            md=md,
        )
    )

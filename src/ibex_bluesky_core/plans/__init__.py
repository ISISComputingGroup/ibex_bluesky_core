"""Generic plan helpers."""

from collections.abc import Generator

import bluesky.plans as bp
from bluesky import plan_stubs as bps
from bluesky.utils import Msg
from ophyd_async.plan_stubs import ensure_connected

from ibex_bluesky_core.callbacks import FitMethod, ISISCallbacks
from ibex_bluesky_core.callbacks.fitting.fitting_utils import Linear
from ibex_bluesky_core.devices import get_pv_prefix
from ibex_bluesky_core.devices.block import BlockWriteConfig, block_rw
from ibex_bluesky_core.devices.simpledae import SimpleDae
from ibex_bluesky_core.devices.simpledae.controllers import (
    PeriodPerPointController,
    RunPerPointController,
)
from ibex_bluesky_core.devices.simpledae.reducers import MonitorNormalizer
from ibex_bluesky_core.devices.simpledae.waiters import GoodFramesWaiter, PeriodGoodFramesWaiter


def set_num_periods(dae: SimpleDae, nperiods: int) -> Generator[Msg, None, None]:
    """Set the number of hardware periods for a DAE.

    Args:
        dae (SimpleDae): DAE object.
        nperiods (int): number of hardware periods to set.

    """
    yield from bps.mv(dae.number_of_periods, nperiods)  # type: ignore
    actual = yield from bps.rd(dae.number_of_periods)
    if actual != nperiods:
        raise ValueError(
            f"Could not set {nperiods} periods on DAE (probably requesting too many points, "
            f"or already running)"
        )


DEFAULT_MON = 1


def common_dae(
    *,
    det_pixels: list[int],
    frames: int,
    periods: bool = True,
    monitor: int = DEFAULT_MON,
    save_run: bool = False,
) -> SimpleDae:
    """Create a simple DAE which normalises using a monitor.

    This is really a shortcut to reduce code in plans used on the majority of instruments that
       normalise using a monitor, wait for a number of frames and optionally use hardware periods.

    Args:
        det_pixels: list of detector pixel to use for scanning.
        frames: number of frames to wait for.
        periods: whether or not to use hardware periods.
        monitor: the monitor spectra number.
        save_run: whether or not to save the run of the DAE.

    """
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


DEFAULT_DET = 3
DEFAULT_FIT_METHOD = Linear().fit()


def scan(  # noqa: PLR0913
    block_name: str,
    start: float,
    stop: float,
    count: int,
    *,
    frames: int,
    det: int = DEFAULT_DET,
    mon: int = DEFAULT_MON,
    model: FitMethod = DEFAULT_FIT_METHOD,
    periods: bool = True,
    save_run: bool = False,
    rel: bool = False,
) -> Generator[Msg, None, None]:
    """Scan the DAE against a block.

    Args:
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
    block = block_rw(float, block_name, write_config=BlockWriteConfig(use_global_moving_flag=True))
    dae = common_dae(
        det_pixels=[det], frames=frames, periods=periods, save_run=save_run, monitor=mon
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

    print(f"Centre-of-mass from PeakStats: {icc.peak_stats['com']}\n")

    if icc.live_fit.result is not None:
        print(icc.live_fit.result.fit_report())
        return icc.live_fit.result.params
    else:
        print("No LiveFit result, likely fit failed")
        return None


def adaptive_scan(  # noqa: PLR0913
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
    model: FitMethod = DEFAULT_FIT_METHOD,
    periods: bool = True,
    save_run: bool = False,
    rel: bool = False,
) -> Generator[Msg, None, None]:
    """Scan the DAE against a block using an adaptive scan.

    This will scan coarsely until target_delta occurs, then it will go back and perform finer scans.

    Args:
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
    block = block_rw(float, block_name, write_config=BlockWriteConfig(use_global_moving_flag=True))
    dae = common_dae(
        det_pixels=[det], frames=frames, periods=periods, save_run=save_run, monitor=mon
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

    print(f"Centre-of-mass from PeakStats: {icc.peak_stats['com']}\n")

    if icc.live_fit.result is not None:
        print(icc.live_fit.result.fit_report())
        return icc.live_fit.result.params
    else:
        print("No LiveFit result, likely fit failed")
        return None

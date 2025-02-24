"""Generic plan helpers."""

from collections.abc import Generator

from bluesky import plan_stubs as bps
from bluesky.utils import Msg

from ibex_bluesky_core.devices import get_pv_prefix
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

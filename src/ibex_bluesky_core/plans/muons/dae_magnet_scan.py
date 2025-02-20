"""Demonstration plan showing basic bluesky functionality."""

import os
from collections.abc import Generator

import bluesky.plans as bp
import matplotlib
import matplotlib.pyplot as plt
from bluesky.utils import Msg
from ophyd_async.plan_stubs import ensure_connected

from ibex_bluesky_core.callbacks import ISISCallbacks
from ibex_bluesky_core.devices import get_pv_prefix
from ibex_bluesky_core.devices.block import BlockWriteConfig, block_rw_rbv
from ibex_bluesky_core.devices.simpledae import SimpleDae
from ibex_bluesky_core.devices.simpledae.controllers import (
    RunPerPointController,
    PeriodPerPointController,
)
from ibex_bluesky_core.devices.simpledae.reducers import PeriodGoodFramesNormalizer
from ibex_bluesky_core.devices.simpledae.waiters import GoodFramesWaiter, PeriodGoodFramesWaiter
from ibex_bluesky_core.plans import set_num_periods
from ibex_bluesky_core.run_engine import get_run_engine

from ibex_bluesky_core.callbacks.fitting.fitting_utils import Gaussian


def dae_magnet_plan(
    block,
    start,
    stop,
    num,
    periods=True,
    frames=500,
    save_run=True,
    magnet_tolerance=0.01,
    magnet_settle_time=1,
) -> Generator[Msg, None, None]:
    """Scan a DAE against a magnet."""

    def check_within_tolerance(setpoint: float, actual: float) -> bool:
        return setpoint - magnet_tolerance <= actual <= setpoint + magnet_tolerance

    magnet = block_rw_rbv(
        float,
        block,
        write_config=BlockWriteConfig(
            settle_time_s=magnet_settle_time, set_success_func=check_within_tolerance
        ),
    )

    prefix = get_pv_prefix()

    if periods:
        controller = PeriodPerPointController(save_run=save_run)
        waiter = PeriodGoodFramesWaiter(frames)
    else:
        controller = RunPerPointController(save_run=save_run)
        waiter = GoodFramesWaiter(frames)

    reducer = PeriodGoodFramesNormalizer(prefix, detector_spectra=[i for i in range(1, 32 + 1)])

    dae = SimpleDae(
        prefix=prefix,
        controller=controller,
        waiter=waiter,
        reducer=reducer,
    )

    yield from ensure_connected(magnet, dae, force_reconnect=True)

    if periods:
        yield from set_num_periods(dae, num)
    else:
        yield from set_num_periods(dae, 1)

    icc = ISISCallbacks(
        y=reducer.intensity.name,
        x=magnet.name,
        yerr=reducer.intensity_stddev.name,
        fit=Gaussian().fit(),
    )

    @icc
    def _inner() -> Generator[Msg, None, None]:
        yield from bp.scan([dae], magnet, start, stop, num=num)

    yield from _inner()
    print(icc.live_fit.result.fit_report())

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
)
from ibex_bluesky_core.devices.simpledae.reducers import (
    GoodFramesNormalizer,
)
from ibex_bluesky_core.devices.simpledae.waiters import GoodFramesWaiter
from ibex_bluesky_core.plans import set_num_periods
from ibex_bluesky_core.run_engine import get_run_engine

NUM_POINTS: int = 3

MAGNET_SETTLE_TIME = 3
MAGNET_BLOCK_NAME = "p3"
MAGNET_TOLERANCE = 0.1


def dae_magnet_plan() -> Generator[Msg, None, None]:
    """Scan a DAE against a magnet."""

    def check_within_tolerance(setpoint: float, actual: float) -> bool:
        return setpoint - MAGNET_TOLERANCE <= actual <= setpoint + MAGNET_TOLERANCE

    magnet = block_rw_rbv(
        float,
        MAGNET_BLOCK_NAME,
        write_config=BlockWriteConfig(
            settle_time_s=MAGNET_SETTLE_TIME, set_success_func=check_within_tolerance
        ),
    )

    prefix = get_pv_prefix()
    controller_chronus = RunPerPointController(save_run=True)
    waiter_chronus = GoodFramesWaiter(500)
    reducer_chronus = GoodFramesNormalizer(
        prefix=prefix,
        detector_spectra=[i for i in range(1, 32 + 1)],
    )

    dae_chronus = SimpleDae(
        prefix=prefix,
        controller=controller_chronus,
        waiter=waiter_chronus,
        reducer=reducer_chronus,
    )

    # yield from set_num_periods(dae_chronus, 100)

    yield from ensure_connected(magnet, dae_chronus, force_reconnect=True)

    icc = ISISCallbacks(
        y=reducer_chronus.intensity.name,
        x=magnet.name,
        yerr=reducer_chronus.intensity_stddev.name,
    )

    @icc
    def _inner() -> Generator[Msg, None, None]:
        yield from bp.scan([dae_chronus], magnet, 0, 10, num=NUM_POINTS)

    yield from _inner()
    print(icc.live_fit.result.fit_report())


if __name__ == "__main__" and not os.environ.get("FROM_IBEX") == "True":
    matplotlib.use("qtagg")
    plt.ion()
    RE = get_run_engine()
    RE(dae_magnet_plan())
    input("Plan complete, press return to close plot and exit")

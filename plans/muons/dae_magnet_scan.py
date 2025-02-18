"""Demonstration plan showing basic bluesky functionality."""

import os
from collections.abc import Generator
from pathlib import Path

import bluesky.plans as bp
import matplotlib.pyplot as plt
from bluesky.utils import Msg
from ophyd_async.plan_stubs import ensure_connected

from ibex_bluesky_core.callbacks import ISISCallbacks
from ibex_bluesky_core.callbacks.fitting import LiveFit
from ibex_bluesky_core.callbacks.fitting.fitting_utils import Linear
from ibex_bluesky_core.devices.block import BlockWriteConfig, block_rw_rbv
from ibex_bluesky_core.devices.simpledae import SimpleDae
from ibex_bluesky_core.devices.simpledae.controllers import (
    RunPerPointController,
)
from ibex_bluesky_core.devices.simpledae.reducers import (
    GoodFramesNormalizer,
)
from ibex_bluesky_core.devices.simpledae.waiters import GoodFramesWaiter
from ibex_bluesky_core.plan_stubs import call_qt_aware
from ibex_bluesky_core.run_engine import get_run_engine

NUM_POINTS: int = 3

MAGNET_SETTLE_TIME = 3
MAGNET_BLOCK_NAME = "p3"


def dae_scan_plan() -> Generator[Msg, None, None]:
    magnet = block_rw_rbv(
        float, MAGNET_BLOCK_NAME, write_config=BlockWriteConfig(settle_time_s=MAGNET_SETTLE_TIME)
    )

    # prefix = "IN:CHRONUS:"
    prefix = "TE:NDW2932:"
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
        name="emu_dae",
    )

    _, ax = yield from call_qt_aware(plt.subplots)

    lf = LiveFit(
        Linear.fit(),
        y=reducer_chronus.intensity.name,
        x=magnet.name,
        yerr=reducer_chronus.intensity_stddev.name,
    )

    yield from ensure_connected(magnet, dae_chronus, force_reconnect=True)

    icc = ISISCallbacks(
        y=reducer_chronus.intensity.name,
        x=magnet.name,
        yerr=reducer_chronus.intensity_stddev.name,
        human_readable_file_output_dir=Path("C:\\")
        / "instrument"
        / "var"
        / "logs"
        / "bluesky"
        / "output_files",
        live_fit_logger_output_dir=Path("C:\\")
        / "instrument"
        / "var"
        / "logs"
        / "bluesky"
        / "fitting",
    )

    @icc
    def _inner() -> Generator[Msg, None, None]:
        yield from bp.scan([dae_chronus], magnet, 0, 10, num=NUM_POINTS)
        print(lf.result.fit_report())

    yield from _inner()


if __name__ == "__main__" and not os.environ.get("FROM_IBEX") == "True":
    # matplotlib.use("qtagg")
    # plt.ion()
    RE = get_run_engine()
    RE(dae_scan_plan())
    input("Plan complete, press return to close plot and exit")

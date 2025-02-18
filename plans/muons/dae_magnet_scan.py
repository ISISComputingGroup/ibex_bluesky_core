"""Demonstration plan showing basic bluesky functionality."""

import os
from collections.abc import Generator
from pathlib import Path

import bluesky.plan_stubs as bps
import bluesky.plans as bp
# import matplotlib
# import matplotlib.pyplot as plt
from bluesky.callbacks import LiveFitPlot, LiveTable
from bluesky.preprocessors import subs_decorator
from bluesky.utils import Msg
from ophyd_async.plan_stubs import ensure_connected

from ibex_bluesky_core.callbacks.file_logger import HumanReadableFileCallback
from ibex_bluesky_core.callbacks.fitting import LiveFit
from ibex_bluesky_core.callbacks.fitting.fitting_utils import Linear
from ibex_bluesky_core.callbacks.fitting.livefit_logger import LiveFitLogger
from ibex_bluesky_core.callbacks.plotting import LivePlot
from ibex_bluesky_core.devices import get_pv_prefix
from ibex_bluesky_core.devices.block import block_rw_rbv, BlockWriteConfig
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

    magnet = block_rw_rbv(float, MAGNET_BLOCK_NAME, write_config=BlockWriteConfig(settle_time_s=MAGNET_SETTLE_TIME))

    emu_prefix = "IN:EMU:"
    controller_emu = RunPerPointController(save_run=True)
    waiter_emu = GoodFramesWaiter(500)
    reducer_emu = GoodFramesNormalizer(
        prefix=emu_prefix,
        detector_spectra=[i for i in range(1, 100)],
    )

    dae_emu = SimpleDae(
        prefix=emu_prefix,
        controller=controller_emu,
        waiter=waiter_emu,
        reducer=reducer_emu, name="emu_dae"
    )

    _, ax = yield from call_qt_aware(plt.subplots)

    lf = LiveFit(
        Linear.fit(), y=reducer_emu.intensity.name, x=magnet.name, yerr=reducer_emu.intensity_stddev.name
    )

    yield from ensure_connected(magnet, dae_emu, force_reconnect=True)

    @subs_decorator(
        [
            LiveFitPlot(livefit=lf, ax=ax),
            LivePlot(
                y=reducer_emu.intensity.name,
                x=magnet.name,
                marker="x",
                linestyle="none",
                ax=ax,
                yerr=reducer_emu.intensity_stddev.name,
            ),
            LiveTable(
                [
                    magnet.name,
                    controller_emu.run_number.name,
                    reducer_emu.intensity.name,
                    reducer_emu.intensity_stddev.name,
                    reducer_emu.det_counts.name,
                    reducer_emu.det_counts_stddev.name,
                    dae_emu.good_frames.name,
                ]
            ),
        ]
    )
    def _inner() -> Generator[Msg, None, None]:
        yield from bp.scan([dae_emu], magnet, 0, 10, num=NUM_POINTS)
        print(lf.result.fit_report())

    yield from _inner()


if __name__ == "__main__" and not os.environ.get("FROM_IBEX") == "True":
    # matplotlib.use("qtagg")
    # plt.ion()
    RE = get_run_engine()
    RE(dae_scan_plan())
    input("Plan complete, press return to close plot and exit")

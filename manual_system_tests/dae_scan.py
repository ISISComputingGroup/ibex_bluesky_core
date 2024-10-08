"""Demonstration plan showing basic bluesky functionality."""

import os
from pathlib import Path
from typing import Generator

import bluesky.plan_stubs as bps
import bluesky.plans as bp
import matplotlib
import matplotlib.pyplot as plt
from bluesky.callbacks import LiveTable
from bluesky.preprocessors import subs_decorator
from bluesky.utils import Msg
from ophyd_async.plan_stubs import ensure_connected

from ibex_bluesky_core.callbacks.file_logger import HumanReadableOutputFileLoggingCallback
from ibex_bluesky_core.callbacks.plotting import LivePlot
from ibex_bluesky_core.devices import get_pv_prefix
from ibex_bluesky_core.devices.block import block_rw_rbv
from ibex_bluesky_core.devices.simpledae import SimpleDae
from ibex_bluesky_core.devices.simpledae.controllers import (
    RunPerPointController,
)
from ibex_bluesky_core.devices.simpledae.reducers import (
    GoodFramesNormalizer,
)
from ibex_bluesky_core.devices.simpledae.waiters import GoodFramesWaiter
from ibex_bluesky_core.run_engine import get_run_engine


def dae_scan_plan() -> Generator[Msg, None, None]:
    """Manual system test which moves a block and reads the DAE.

    Prerequisites:
    - A block named "mot" pointing at MOT:MTR0101.RBV
    - A galil IOC in RECSIM mode with MTRCTRL=1 so that the above PV is available
    - A DAE in a setup which can begin and end simulated runs.

    Expected result:
    - A sensible-looking LiveTable has been displayed
      * Shows mot stepping from 0 to 10 in 3 evenly-spaced steps
    - A plot has been displayed (in IBEX if running in the IBEX gui, in a QT window otherwise)
      * Should plot "noise" on the Y axis from the simulated DAE
      * Y axis should be named "normalized counts"
      * X axis should be named "mot"
    - The DAE was started and ended once per point
    - The DAE waited for at least 500 good frames at each point
    """
    prefix = get_pv_prefix()
    block = block_rw_rbv(float, "mot")

    controller = RunPerPointController(save_run=True)
    waiter = GoodFramesWaiter(500)
    reducer = GoodFramesNormalizer(
        prefix=prefix,
        detector_spectra=[i for i in range(1, 100)],
    )

    dae = SimpleDae(
        prefix=prefix,
        controller=controller,
        waiter=waiter,
        reducer=reducer,
    )

    # Demo giving some signals more user-friendly names
    controller.run_number.set_name("run number")
    reducer.intensity.set_name("normalized counts")

    yield from ensure_connected(block, dae, force_reconnect=True)

    @subs_decorator(
        [
            HumanReadableOutputFileLoggingCallback(
                Path("C:\\") / "instrument" / "var" / "logs" / "bluesky" / "output_files",
                [
                    block.name,
                    controller.run_number.name,
                    reducer.intensity.name,
                    reducer.det_counts.name,
                    dae.good_frames.name,
                ],
            ),
            LivePlot(y=reducer.intensity.name, x=block.name, marker="x", linestyle="none"),
            LiveTable(
                [
                    block.name,
                    controller.run_number.name,
                    reducer.intensity.name,
                    reducer.det_counts.name,
                    dae.good_frames.name,
                ]
            ),
        ]
    )
    def _inner() -> Generator[Msg, None, None]:
        num_points = 3
        yield from bps.mv(dae.number_of_periods, num_points)
        yield from bp.scan([dae], block, 0, 10, num=num_points)

        yield from bps.abs_set(block, 3.0, wait=True)
        yield from bps.trigger(dae.controls.begin_run, wait=True)
        yield from bps.sleep(5)  # ... some complicated logic ...
        yield from bps.trigger(dae.controls.end_run, wait=True)
        yield from bps.create()  # Create a bundle of readings
        yield from bps.read(block)
        yield from bps.read(dae.good_uah)
        yield from bps.save()

    yield from _inner()


if __name__ == "__main__" and not os.environ.get("FROM_IBEX") == "True":
    matplotlib.use("qtagg")
    plt.ion()
    RE = get_run_engine()
    RE(dae_scan_plan())
    input("Plan complete, press return to close plot and exit")

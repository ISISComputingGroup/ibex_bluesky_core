"""Demonstration plan showing basic bluesky functionality."""

import os
import uuid
from pathlib import Path
from typing import Generator

import bluesky.plan_stubs as bps
import bluesky.plans as bp
import matplotlib
import matplotlib.pyplot as plt
from bluesky.callbacks import LiveFitPlot, LiveTable
from bluesky.plan_stubs import trigger_and_read
from bluesky.preprocessors import subs_decorator, run_decorator, monitor_during_decorator, contingency_wrapper
from bluesky.utils import Msg
from ophyd_async.plan_stubs import ensure_connected

from ibex_bluesky_core.callbacks.file_logger import HumanReadableFileCallback
from ibex_bluesky_core.callbacks.fitting import LiveFit
from ibex_bluesky_core.callbacks.fitting.fitting_utils import Linear, Gaussian
from ibex_bluesky_core.callbacks.plotting import LivePlot
from ibex_bluesky_core.devices import get_pv_prefix
from ibex_bluesky_core.devices.block import block_rw_rbv, block_r, block_mot
from ibex_bluesky_core.devices.simpledae import SimpleDae
from ibex_bluesky_core.devices.simpledae.controllers import (
    RunPerPointController,
)
from ibex_bluesky_core.devices.simpledae.reducers import (
    GoodFramesNormalizer,
)
from ibex_bluesky_core.devices.simpledae.waiters import GoodFramesWaiter
from ibex_bluesky_core.run_engine import get_run_engine

NUM_POINTS: int = 3


def continuous_scan_plan(dave: float) -> Generator[Msg, None, None]:
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
    bob = block_mot("bob")
    alice = block_r(float, "alice")
    mot = block_r(float, "mot")
    _, ax = plt.subplots()
    lf = LiveFit(
        Gaussian.fit(), y=alice.name, x=bob.name
    )

    yield from ensure_connected(bob, alice, mot)

    @subs_decorator(
        [
            HumanReadableFileCallback(
                Path("C:\\") / "instrument" / "var" / "logs" / "bluesky" / "output_files",
                [
                    alice.name,
                    bob.name
                ],
            ),
            LiveTable(
                [
                    alice.name,
                    bob.name
                ]
            ),
            LiveFitPlot(livefit=lf, ax=ax, update_every=100),
            LivePlot(
                y=alice.name,
                x=bob.name,
                marker="x",
                linestyle="none",
                ax=ax,
            ),
        ]
    )
    def _inner() -> Generator[Msg, None, None]:

        @run_decorator(md={})
        def polling_plan():
            yield from bps.create()
            reading = yield from bps.read(bob)
            yield from bps.read(alice)
            yield from bps.save()

            # start the ramp
            status = yield from bps.abs_set(bob, dave, wait=False)
            while not status.done:
                yield from bps.checkpoint()
                yield from bps.clear_checkpoint()

                yield from bps.create()
                new_reading = yield from bps.read(bob)
                yield from bps.read(alice)

                if new_reading[bob.name]["value"] == reading[bob.name]["value"]:
                    yield from bps.drop()
                else:
                    reading = new_reading
                    yield from bps.save()

            # take a 'post' data point
            yield from trigger_and_read([bob, alice])

        return (yield from polling_plan())

    def _stop_motor(e):
        yield from bps.stop(bob)

    yield from contingency_wrapper(_inner(), except_plan=_stop_motor)


if __name__ == "__main__" and not os.environ.get("FROM_IBEX") == "True":
    matplotlib.use("qtagg")
    plt.ion()
    RE = get_run_engine()
    RE(continuous_scan_plan())
    input("Plan complete, press return to close plot and exit")

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
from bluesky.preprocessors import subs_decorator, run_decorator, finalize_wrapper
from bluesky.utils import Msg
from ophyd_async.plan_stubs import ensure_connected

from ibex_bluesky_core.callbacks.file_logger import HumanReadableFileCallback
from ibex_bluesky_core.callbacks.fitting import LiveFit
from ibex_bluesky_core.callbacks.fitting.fitting_utils import Trapezoid
from ibex_bluesky_core.callbacks.plotting import LivePlot
from ibex_bluesky_core.devices.block import block_r, block_mot
from ibex_bluesky_core.run_engine import get_run_engine

NUM_POINTS: int = 3


def continuous_scan_plan(
    mot_block_name: str, centre: float, size: float, time: float, iterations: int
) -> Generator[Msg, None, None]:
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
    motor = block_mot(mot_block_name)

    laser_intensity = block_r(float, "alice")
    _, ax = plt.subplots()
    lf = LiveFit(Trapezoid.fit(), y=laser_intensity.name, x=motor.name)

    initial_position = centre - 0.5 * size
    final_position = centre + 0.5 * size

    yield from ensure_connected(
        laser_intensity,
        motor,
    )
    initial_velocity = yield from bps.rd(motor.velocity)
    yield from bps.mv(motor.velocity, size / time)

    @subs_decorator(
        [
            HumanReadableFileCallback(
                Path("C:\\") / "instrument" / "var" / "logs" / "bluesky" / "output_files",
                [motor.name, laser_intensity.name],
            ),
            LiveTable([motor.name, laser_intensity.name]),
            LiveFitPlot(livefit=lf, ax=ax),
            LivePlot(
                y=laser_intensity.name,
                x=motor.name,
                marker="x",
                linestyle="none",
                ax=ax,
            ),
        ]
    )
    @run_decorator(md={})
    def _inner() -> Generator[Msg, None, None]:
        def polling_plan(destination: float):
            yield from bps.checkpoint()
            yield from bps.create()
            reading = yield from bps.read(motor)
            yield from bps.read(laser_intensity)
            yield from bps.save()

            # start the ramp
            status = yield from bps.abs_set(motor, destination, wait=False)
            while not status.done:
                yield from bps.create()
                new_reading = yield from bps.read(motor)
                yield from bps.read(laser_intensity)

                if new_reading[motor.name]["value"] == reading[motor.name]["value"]:
                    yield from bps.drop()
                else:
                    reading = new_reading
                    yield from bps.save()

            # take a 'post' data point
            yield from trigger_and_read([motor, laser_intensity])

        yield from bps.mv(motor, initial_position)
        for i in range(iterations):
            yield from polling_plan(final_position)
            yield from polling_plan(initial_position)

    def _set_motor_back_to_original_velocity():
        yield from bps.mv(motor.velocity, initial_velocity)

    yield from finalize_wrapper(_inner(), _set_motor_back_to_original_velocity)
    print(lf.result.fit_report())


if __name__ == "__main__" and not os.environ.get("FROM_IBEX") == "True":
    matplotlib.use("qtagg")
    plt.ion()
    RE = get_run_engine()
    RE(continuous_scan_plan("bob", 100, 50, 10, 2))
    input("Plan complete, press return to close plot and exit")

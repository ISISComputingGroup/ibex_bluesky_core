"""Demonstration plan showing basic bluesky functionality."""

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

from ibex_bluesky_core.callbacks.plotting import LivePlot
from ibex_bluesky_core.callbacks.file_logger import HumanReadableOutputFileLoggingCallback
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

__all__ = ["demo_plan"]


def demo_plan() -> Generator[Msg, None, None]:
    """Demonstration plan which moves a block and reads the DAE."""
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
                [block.name, "DAE-good_uah"],
            ),
            HumanReadableOutputFileLoggingCallback(
                Path("C:\\")
                / "instrument"
                / "var"
                / "logs"
                / "bluesky"
                / "output_files"
                / "hintedfields"
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
        num_points = 20
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


if __name__ == "__main__":
    if "genie_python" not in matplotlib.get_backend():
        matplotlib.use("qtagg")
        plt.ion()
    RE = get_run_engine()
    RE(demo_plan(), testing123="yes")
    input("plan complete, press return to continue.")

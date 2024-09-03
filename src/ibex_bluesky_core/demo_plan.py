"""Demonstration plan showing basic bluesky functionality."""

from typing import Generator

import bluesky.plan_stubs as bps
import matplotlib
import matplotlib.pyplot as plt
from bluesky.callbacks import LiveTable
from bluesky.preprocessors import run_decorator, subs_decorator
from bluesky.utils import Msg
from ophyd_async.plan_stubs import ensure_connected

from ibex_bluesky_core.callbacks.plotting import LivePlot
from ibex_bluesky_core.devices import get_pv_prefix
from ibex_bluesky_core.devices.block import block_rw_rbv
from ibex_bluesky_core.devices.dae.dae import Dae
from ibex_bluesky_core.run_engine import get_run_engine

__all__ = ["demo_plan"]


def demo_plan() -> Generator[Msg, None, None]:
    """Demonstration plan which moves a block and reads the DAE."""
    prefix = get_pv_prefix()
    block = block_rw_rbv(float, "mot")
    dae = Dae(prefix)

    yield from ensure_connected(block, dae, force_reconnect=True)

    @subs_decorator(
        [
            LivePlot(y=dae.name, x=block.name, marker="x", linestyle="none"),
            LiveTable([block.name, dae.name]),
        ]
    )
    @run_decorator(md={})
    def _inner() -> Generator[Msg, None, None]:
        # Acquisition showing arbitrary DAE control to support complex use-cases.
        yield from bps.abs_set(block, 2.0, wait=True)
        yield from bps.trigger(dae.controls.begin_run, wait=True)
        yield from bps.sleep(5)  # ... some complicated logic ...
        yield from bps.trigger(dae.controls.end_run, wait=True)
        yield from bps.create()  # Create a bundle of readings
        yield from bps.read(block)
        yield from bps.read(dae)
        yield from bps.save()

    yield from _inner()


if __name__ == "__main__":
    if "genie_python" not in matplotlib.get_backend():
        matplotlib.use("qtagg")
        plt.ion()
    RE = get_run_engine()
    RE(demo_plan())
    input("plan complete, press return to continue.")

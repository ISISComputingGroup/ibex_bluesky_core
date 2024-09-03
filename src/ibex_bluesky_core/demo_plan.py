"""Demonstration plan showing basic bluesky functionality."""

from typing import Generator

import bluesky.plan_stubs as bps
from bluesky.callbacks import LiveTable
from bluesky.preprocessors import run_decorator
from bluesky.utils import Msg
from ophyd_async.plan_stubs import ensure_connected

from ibex_bluesky_core.devices import get_pv_prefix
from ibex_bluesky_core.devices.block import BlockRwRbv, block_rw_rbv
from ibex_bluesky_core.devices.dae.dae import Dae
from ibex_bluesky_core.run_engine import get_run_engine

__all__ = ["run_demo_plan", "demo_plan"]


def run_demo_plan() -> None:
    """Run the demo plan, including setup which would usually be done outside the plan.

    You will need a DAE in a state which can begin, and a settable & readable
    floating-point block named "mot".

    Run using:
    >>> from ibex_bluesky_core.demo_plan import run_demo_plan
    >>> run_demo_plan()
    """
    RE = get_run_engine()
    prefix = get_pv_prefix()
    block = block_rw_rbv(float, "mot")
    dae = Dae(prefix)
    RE(demo_plan(block, dae), LiveTable(["mot", "DAE"]))


def demo_plan(block: BlockRwRbv[float], dae: Dae) -> Generator[Msg, None, None]:
    """Demonstration plan which moves a block and reads the DAE."""
    yield from ensure_connected(block, dae, force_reconnect=True)

    @run_decorator(md={})
    def _inner() -> Generator[Msg, None, None]:
        # A "simple" acquisition using trigger_and_read.
        yield from bps.abs_set(block, 1.0, wait=True)
        yield from bps.trigger_and_read([block, dae])

        # More complicated acquisition showing arbitrary DAE control to support complex use-cases.
        yield from bps.abs_set(block, 2.0, wait=True)
        yield from bps.trigger(dae.begin_run, wait=True)
        yield from bps.sleep(5)  # ... some complicated logic ...
        yield from bps.trigger(dae.end_run, wait=True)
        yield from bps.create()  # Create a bundle of readings
        yield from bps.read(block)
        yield from bps.read(dae)
        yield from bps.save()

    yield from _inner()

"""Demonstration plan showing basic bluesky functionality."""

from typing import Generator

import bluesky.plan_stubs as bps
from bluesky.preprocessors import run_decorator
from bluesky.utils import Msg
from ophyd_async.plan_stubs import ensure_connected

from ibex_bluesky_core.devices.block import Block
from ibex_bluesky_core.devices.dae import Dae


def demo_plan() -> Generator[Msg, None, None]:
    """Demonstration plan which moves a block and reads the DAE.

    Run using:
    >>> from ibex_bluesky_core.demo_plan import demo_plan
    >>> from bluesky.run_engine import RunEngine
    >>> from bluesky.callbacks import LiveTable
    >>> RE = RunEngine()
    >>> RE(demo_plan(), LiveTable("mot-value", "DAE"))

    You will need a DAE in a state which can begin, and a settable & readable
    floating-point block named "mot".
    """
    block = Block("mot", float)
    dae = Dae()
    yield from ensure_connected(block, dae)

    @run_decorator(md={})
    def _inner() -> Generator[Msg, None, None]:
        yield from bps.abs_set(block, 1.0, wait=True)
        yield from bps.trigger_and_read([block, dae])
        yield from bps.abs_set(block, 2.0, wait=True)
        yield from bps.trigger_and_read([block, dae])

    yield from _inner()

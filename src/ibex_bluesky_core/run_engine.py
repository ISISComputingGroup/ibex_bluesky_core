"""Utilities for the bluesky run engine, configured for IBEX."""

import asyncio
from functools import cache
from threading import Event

from bluesky.run_engine import RunEngine
from bluesky.utils import DuringTask

__all__ = ["get_run_engine"]


class _DuringTask(DuringTask):
    def block(self, blocking_event: Event) -> None:
        """On windows, event.wait() on the main thread is not interruptible by a CTRL-C.

        Therefore, split the event.wait into many smaller event.waits, each with a 0.1 second
        timeout. This allows:
        - CTRL-C to be handled reasonably responsively for users
        - returning as soon as possible after the event is set
        - not busy-waiting
        """
        while not blocking_event.wait(0.1):
            pass


@cache  # functools.cache ensures we only ever create a single instance of the RunEngine
def get_run_engine() -> RunEngine:
    """Acquire a RunEngine in a suitable configuration for ISIS experiments.

    This function should always be used in preference to creating a bluesky run engine manually.

    This function is cached, meaning that the *same* run engine (using the same underlying event
    loop) will be used if this function is called multiple times. Creating multiple RunEngines is
    unlikely to be desired behaviour, though we cannot prevent users from creating a RunEngine from
    bluesky directly.

    Basic usage:
    - Get the IBEX run engine:
    >>> RE = get_run_engine()

    - Run a plan:
    >>> from bluesky.plans import count  # Or any other plan
    >>> det = ...  # A "detector" object, for example a Block or Dae device.
    >>> RE(count([det]))

    - Control the state of the run engine:
    >>> RE.abort(reason="...")  # Stop a plan, do cleanup, and mark as failed (e.g. bad data).
    >>> RE.stop()  # Stop a plan, do cleanup, mark as success"(e.g. scan has moved past peak).
    >>> RE.halt()  # Stop a plan, don't do any cleanup, just abort with no further action.
    >>> RE.resume()  # Resume running a previously-paused plan.

    - Subscribe to data emitted by this run engine:
    >>> RE.subscribe(lambda name, document: ...)

    For full documentation about the run engine, see:
    - https://nsls-ii.github.io/bluesky/tutorial.html#the-runengine
    - https://nsls-ii.github.io/bluesky/run_engine_api.html
    """
    loop = asyncio.new_event_loop()
    RE = RunEngine(
        loop=loop,
        during_task=_DuringTask(),
        call_returns_result=True,  # Will be default in a future bluesky version.
    )
    RE.record_interruptions = True

    return RE

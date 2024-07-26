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


@cache
def get_run_engine() -> RunEngine:
    """Acquire a RunEngine in a suitable configuration for ISIS experiments.

    This function should always be used in preference to creating a bluesky run engine manually.

    This function is cached, meaning that the *same* run engine (using the same underlying event
    loop) will be used if this function is called multiple times. Creating multiple RunEngines is
    unlikely to be desired behaviour, though we cannot prevent users from creating a RunEngine from
    bluesky directly.

    Generally should be used as:
    >>> RE = get_run_engine()
    >>> plan: Generator[Msg, None, None] = ...
    >>> RE(plan)  # Run a plan
    >>> RE.subscribe(...)  # Subscribe to future documents emitted by the run engine
    >>> RE.abort(reason="...")  # Control the state of the run engine
    """
    loop = asyncio.new_event_loop()
    RE = RunEngine(
        loop=loop,
        during_task=_DuringTask(),
        call_returns_result=True,  # Will be default in a future bluesky version.
    )
    RE.record_interruptions = True

    return RE

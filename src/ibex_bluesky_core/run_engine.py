"""Utilities for the bluesky run engine, configured for IBEX."""

import asyncio
from functools import cache

from bluesky.run_engine import RunEngine

__all__ = ["get_run_engine"]


@cache
def get_run_engine() -> RunEngine:
    """Acquire a RunEngine in a suitable configuration for ISIS experiments.

    This function should always be used in preference to creating a bluesky
    run engine manually.

    This function is cached, meaning that the *same* run engine (using the same
    underlying event loop) will be used if this function is called multiple
    times. Creating multiple RunEngines is unlikely to be desired behaviour,
    though we cannot prevent users from creating a RunEngine from bluesky directly.

    Generally should be used as:
    >>> RE = get_run_engine()
    """
    loop = asyncio.new_event_loop()
    RE = RunEngine(
        loop=loop,
        call_returns_result=True,  # Will be default in a future bluesky version.
    )
    RE.record_interruptions = True

    return RE

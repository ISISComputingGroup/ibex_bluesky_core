"""Utilities for the bluesky run engine, configured for IBEX."""

import asyncio
import functools
from functools import cache
from threading import Event
from typing import Generator

import bluesky.plan_stubs as bps
import bluesky.preprocessors as bpp
import matplotlib
from bluesky.run_engine import RunEngine
from bluesky.utils import DuringTask, Msg
from ophyd_async.epics.signal import epics_signal_r
from ophyd_async.plan_stubs import ensure_connected

from ibex_bluesky_core.callbacks.document_logger import DocLoggingCallback

__all__ = ["get_run_engine"]

from ibex_bluesky_core.devices import get_pv_prefix


def add_rb_number_processor(msg: Msg) -> tuple[Generator[Msg, None, None] | None, None]:
    if msg.command == "open_run" and "rb_number" not in msg.kwargs:

        def _before() -> Generator[Msg, None, None]:
            rb_number = epics_signal_r(str, f"{get_pv_prefix()}ED:RBNUMBER", name="rb_number")

            def _read_rb() -> Generator[Msg, None, str]:
                yield from ensure_connected(rb_number)
                return (yield from bps.rd(rb_number))

            def _cant_read_rb(e: Exception) -> Generator[Msg, None, str]:
                yield from bps.null()
                return "(unknown)"

            rb = yield from bpp.contingency_wrapper(
                _read_rb(), except_plan=_cant_read_rb, auto_raise=False
            )
            return (yield from bpp.inject_md_wrapper(bpp.single_gen(msg), md={"rb_number": rb}))

        return _before(), None
    return None, None


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

    - Get the IBEX run engine::

        RE = get_run_engine()

    - Run a plan::

        from bluesky.plans import count  # Or any other plan
        det = ...  # A "detector" object, for example a Block or Dae device.
        RE(count([det]))

    - Control the state of the run engine::

        RE.abort(reason="...")  # Stop a plan, do cleanup, and mark as failed (e.g. bad data).
        RE.stop()  # Stop a plan, do cleanup, mark as success"(e.g. scan has moved past peak).
        RE.halt()  # Stop a plan, don't do any cleanup, just abort with no further action.
        RE.resume()  # Resume running a previously-paused plan.

    - Subscribe to data emitted by this run engine::

        RE.subscribe(lambda name, document: ...)

    For full documentation about the run engine, see:
    - https://nsls-ii.github.io/bluesky/tutorial.html#the-runengine
    - https://nsls-ii.github.io/bluesky/run_engine_api.html
    """
    loop = asyncio.new_event_loop()

    # Only log *very* slow callbacks (in asyncio debug mode)
    # Fitting/plotting can take more than the 100ms default.
    loop.slow_callback_duration = 500

    # See https://github.com/bluesky/bluesky/pull/1770 for details
    # We don't need to use our custom _DuringTask if matplotlib is
    # configured to use Qt.
    dt = None if "qt" in matplotlib.get_backend() else _DuringTask()

    RE = RunEngine(
        loop=loop,
        during_task=dt,
        call_returns_result=True,  # Will be default in a future bluesky version.
    )

    log_callback = DocLoggingCallback()
    RE.subscribe(log_callback)

    RE.preprocessors.append(functools.partial(bpp.plan_mutator, msg_proc=add_rb_number_processor))

    return RE

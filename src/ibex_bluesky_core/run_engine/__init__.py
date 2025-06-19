"""Utilities for the bluesky run engine, configured for IBEX."""

import asyncio
import functools
import logging
from collections.abc import Generator
from functools import cache
from threading import Event, Lock
from typing import Any, cast

import bluesky.preprocessors as bpp
from bluesky.run_engine import RunEngine, RunEngineResult
from bluesky.utils import DuringTask, Msg, RunEngineControlException, RunEngineInterrupted

from ibex_bluesky_core.callbacks import DocLoggingCallback
from ibex_bluesky_core.preprocessors import add_rb_number_processor

__all__ = ["get_run_engine", "run_plan"]


from ibex_bluesky_core.plan_stubs import CALL_QT_AWARE_MSG_KEY, CALL_SYNC_MSG_KEY
from ibex_bluesky_core.run_engine._msg_handlers import call_qt_aware_handler, call_sync_handler
from ibex_bluesky_core.utils import is_matplotlib_backend_qt
from ibex_bluesky_core.version import version

logger = logging.getLogger(__name__)


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
    logger.info("Creating new bluesky RunEngine")
    loop = asyncio.new_event_loop()

    # Only log *very* slow callbacks (in asyncio debug mode)
    # Fitting/plotting can take more than the 100ms default.
    loop.slow_callback_duration = 500

    # See https://github.com/bluesky/bluesky/pull/1770 for details
    # We don't need to use our custom _DuringTask if matplotlib is
    # configured to use Qt.
    dt = None if is_matplotlib_backend_qt() else _DuringTask()

    RE = RunEngine(
        loop=loop,
        during_task=dt,
        call_returns_result=True,  # Will be default in a future bluesky version.
    )

    RE.md["versions"]["ibex_bluesky_core"] = version

    log_callback = DocLoggingCallback()
    RE.subscribe(log_callback)

    RE.register_command(CALL_SYNC_MSG_KEY, call_sync_handler)
    RE.register_command(CALL_QT_AWARE_MSG_KEY, call_qt_aware_handler)

    RE.preprocessors.append(functools.partial(bpp.plan_mutator, msg_proc=add_rb_number_processor))

    return RE


_RUN_PLAN_LOCK = Lock()  # Explicitly *not* an RLock - RunEngine is not reentrant.


def run_plan(
    plan: Generator[Msg, Any, Any],
    **metadata_kw: Any,  # noqa ANN401 - this really does accept anything serializable
) -> RunEngineResult:
    """Run a plan.

    .. Warning::

        The usual way to run a plan in bluesky is by calling ``RE(plan(...))`` interactively.
        An ``RE`` object is already available in recent versions of the IBEX user interface,
        or can be acquired by calling ``get_run_engine()``.

        Use of this function is **not recommended**, but it is nevertheless provided as an escape
        hatch for workflows which would otherwise be difficult to express or where parts of scanning
        scripts have not, or cannot, be migrated to bluesky.

    Args:
        plan (positional-only): The plan to run. This is typically a generator instance.
        metadata_kw (optional, keyword-only): Keyword arguments (metadata) to pass to the bluesky
            run engine.

    Returns:
        A ``RunEngineResult`` instance. The return value of the plan can then be accessed using
        the ``plan_result`` attribute.

    Raises:
        RuntimeError: if the run engine was not idle at the start of this call.
        RuntimeError: if a reentrant call to the run engine is detected.
        :py:obj:`bluesky.utils.RunEngineInterrupted`: if the user, or the plan itself, explicitly
            requests an interruption.

    Calling a plan using this function means that keyboard-interrupt handling will be
    degraded: all keyboard interrupts will now force an immediate abort of the plan, using
    ``RE.abort()``, rather than giving the possibility of gracefully resuming. Cleanup handlers
    will execute during the ``RE.abort()``.

    The bluesky run engine is not reentrant. It is a programming error to attempt to run a plan
    using this function, from within a plan. To call a sub plan from within an outer plan, use::

        def outer_plan():
            ...
            yield from subplan(...)

    """
    RE = get_run_engine()

    if not _RUN_PLAN_LOCK.acquire(blocking=False):
        raise RuntimeError(
            "reentrant run_plan call attempted; this cannot be supported.\n"
            "It is a programming error to attempt to run a plan using run_plan "
            "from within a plan.\n"
            "To call a sub plan from within an outer plan, "
            "use 'yield from subplan(...)' instead.\n"
        )
    try:
        if RE.state != "idle":
            raise RuntimeError(
                "Cannot run plan; RunEngine is not idle at start of run_plan call. "
                "You may need to call RE.abort() to abort after a previous plan."
            )
        try:
            return cast(RunEngineResult, RE(plan, **metadata_kw))
        except (RunEngineInterrupted, RunEngineControlException):
            raise RunEngineInterrupted(
                "bluesky RunEngine interrupted; not resumable as running via run_plan"
            ) from None
        finally:
            if RE.state != "idle":
                # Safest reasonable default? Don't want to halt()
                # as that wouldn't do cleanup e.g. dae settings
                RE.abort()
    finally:
        _RUN_PLAN_LOCK.release()

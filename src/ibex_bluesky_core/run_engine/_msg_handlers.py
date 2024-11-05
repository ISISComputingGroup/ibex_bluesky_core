"""Private helper module for run engine message handlers.

Not intended for user use.
"""

import ctypes
import threading
from asyncio import CancelledError, Event, get_running_loop
from typing import Any

from bluesky.utils import Msg


class _ExternalFunctionInterrupted(BaseException):
    """An external sync function running in a worker thread is being interrupted."""


async def call_sync_handler(msg: Msg) -> Any:  # noqa: ANN401
    """Handle ibex_bluesky_core.plan_stubs.call_sync."""
    func = msg.obj
    ret = None
    exc: BaseException | None = None
    done_event = Event()
    loop = get_running_loop()

    def _wrapper() -> Any:  # noqa: ANN401
        try:
            nonlocal ret
            ret = func(*msg.args, **msg.kwargs)
        except _ExternalFunctionInterrupted:
            pass  # Suppress stack traces from our special interruption exception.
        except BaseException as e:
            nonlocal exc
            exc = e
            raise
        finally:
            loop.call_soon_threadsafe(done_event.set)

    worker_thread = threading.Thread(target=_wrapper, name="external_function_worker", daemon=True)
    worker_thread.start()

    try:
        # Wait until done event is set.
        # Ensure we're not blocking the whole event loop while waiting.
        await done_event.wait()
    except (KeyboardInterrupt, CancelledError):
        # We got interrupted while the external function thread was running.
        #
        # A few options:
        # - We could hang until the external function returns (not ideal, in principle it could
        #   be a rather long-running external function, so would prevent the interrupt from working)
        # - Interrupt but don't actually kill the thread, this leads to a misleading result where
        #   a user gets the shell back but the task is still running in the background
        # - Hack around with ctypes to inject an injection into the thread running the external
        #   function. This is generally frowned upon as a bad idea, but may be the "least bad"
        #   solution to running potentially-blocking user code within a plan.
        # - Force users to pass in coroutines (which await regularly) or functions which check some
        #   global interrupt flag regularly. Unlikely to be able to persuade users to do this in
        #   general.
        #
        # A few notes on PyThreadState_SetAsyncExc:
        # - It is used by bluesky here, for a similar case:
        #   https://github.com/bluesky/bluesky/blob/v1.13.0a4/src/bluesky/run_engine.py#L1074
        # - The documentation for this function includes the line
        #   "To prevent naive misuse, you must write your own C extension to call this."
        #   (Like bluesky, I have cheated by using ctypes instead of C)
        # - It may not be fully reliable, in general. It is possible for the async exception to be
        #   cleared in native code (and thus "ignored"). We can't wait for the thread to die, as it
        #   may be in a long-running system call that won't notice this exception until it returns
        #   to python code. This is still felt to be better-than-nothing.
        #
        thread_id = worker_thread.ident
        assert thread_id is not None, "Can't find worker thread to kill it"
        n_threads = ctypes.pythonapi.PyThreadState_SetAsyncExc(
            ctypes.c_ulong(thread_id), ctypes.py_object(_ExternalFunctionInterrupted)
        )
        assert n_threads <= 1, f"Raised async exception in multiple ({n_threads}) threads!"
        raise
    if exc is not None:
        raise exc
    return ret

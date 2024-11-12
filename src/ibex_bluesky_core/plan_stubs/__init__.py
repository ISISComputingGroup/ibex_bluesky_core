"""Core plan stubs."""

from typing import Callable, Generator, ParamSpec, TypeVar, cast

import bluesky.plan_stubs as bps
from bluesky.utils import Msg

P = ParamSpec("P")
T = TypeVar("T")


CALL_SYNC_MSG_KEY = "ibex_bluesky_core_call_sync"


def call_sync(func: Callable[P, T], *args: P.args, **kwargs: P.kwargs) -> Generator[Msg, None, T]:
    """Call a synchronous user function in a plan, and returns the result of that call.

    Attempts to guard against the most common pitfalls of naive implementations, for example:

    - Blocking the whole event loop
    - Breaking keyboard interrupt handling
    - Not clearing the active checkpoint

    It does not necessarily guard against all possible cases, and as such it is *recommended* to
    use native bluesky functionality wherever possible in preference to this plan stub. This should
    be seen as an escape-hatch.

    The wrapped function will be run in a new thread.

    This plan stub will clear any active checkpoints before running the external code, because
    in general the external code is not safe to re-run later once it has started (e.g. it may have
    done relative sets, or may have started some external process). This means that if a plan is
    interrupted at any point between a call_sync and the next checkpoint, the plan cannot be
    resumed - in this case bluesky.utils.FailedPause will appear in the ctrl-c stack trace.

    Args:
        func: A callable to run.
        args: Arbitrary arguments to be passed to the wrapped function
        kwargs: Arbitrary keyword arguments to be passed to the wrapped function

    """
    yield from bps.clear_checkpoint()
    return cast(T, (yield Msg(CALL_SYNC_MSG_KEY, func, *args, **kwargs)))

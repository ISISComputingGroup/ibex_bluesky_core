"""Core plan stubs."""

from collections.abc import Generator
from typing import Any, Callable, ParamSpec, TypeVar, cast

import bluesky.plan_stubs as bps
import matplotlib.pyplot as plt
from bluesky.utils import Msg
from matplotlib.figure import Figure

P = ParamSpec("P")
T = TypeVar("T")


CALL_SYNC_MSG_KEY = "ibex_bluesky_core_call_sync"
CALL_QT_SAFE_MSG_KEY = "ibex_bluesky_core_call_qt_safe"


__all__ = ["call_sync", "matplotlib_subplots"]


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


def matplotlib_subplots(
    *args: Any,  # noqa: ANN401 - pyright doesn't understand we're wrapping mpl API.
    **kwargs: Any,  # noqa: ANN401 - pyright doesn't understand we're wrapping mpl API.
) -> Generator[Msg, None, tuple[Figure, Any]]:
    """Create a new matplotlib figure and axes, using matplotlib.pyplot.subplots, from a plan.

    This is done in a Qt-safe way, such that if matplotlib is using a Qt backend then
    UI operations are run on the Qt thread via Qt signals.

    Args:
        args: Arbitrary arguments, passed through to matplotlib.pyplot.subplots
        kwargs: Arbitrary keyword arguments, passed through to matplotlib.pyplot.subplots

    Returns:
        tuple of (figure, axes) - as per matplotlib.pyplot.subplots()

    """
    yield from bps.clear_checkpoint()
    return cast(
        tuple[Figure, Any], (yield Msg(CALL_QT_SAFE_MSG_KEY, plt.subplots, *args, **kwargs))
    )

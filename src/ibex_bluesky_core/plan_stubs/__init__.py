"""Core plan stubs."""

import threading
from collections.abc import Generator
from typing import Callable, ParamSpec, TypeVar, cast

import bluesky.plan_stubs as bps
import matplotlib.pyplot as plt
from bluesky.callbacks.mpl_plotting import QtAwareCallback
from bluesky.utils import Msg
from event_model import RunStart
from matplotlib.axes import Axes
from matplotlib.figure import Figure

P = ParamSpec("P")
T = TypeVar("T")


PYPLOT_SUBPLOTS_TIMEOUT = 5


CALL_SYNC_MSG_KEY = "ibex_bluesky_core_call_sync"


__all__ = ["call_sync", "new_matplotlib_figure_and_axes"]


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


def new_matplotlib_figure_and_axes(
    *args: list, **kwargs: dict
) -> Generator[Msg, None, tuple[Figure, Axes]]:
    """Create a new matplotlib figure and axes, using plt.subplots, from within a plan.

    This is done in a Qt-safe way, such that if matplotlib is using the Qt backend then
    UI operations need to be run on the Qt thread via Qt signals.

    Args:
        args: Arbitrary arguments, passed through to matplotlib.pyplot.subplots
        kwargs: Arbitrary keyword arguments, passed through to matplotlib.pyplot.subplots

    Returns:
        tuple of (figure, axes) - as per matplotlib.pyplot.subplots()

    """
    yield from bps.null()

    ev = threading.Event()
    fig: Figure | None = None
    ax: Axes | None = None
    ex: BaseException | None = None

    # Slightly hacky, this isn't really a callback per-se but we want to benefit from
    # bluesky's Qt-matplotlib infrastructure.
    # This never gets attached to the RunEngine.
    class _Cb(QtAwareCallback):
        def start(self, _: RunStart) -> None:
            nonlocal fig, ax, ex
            # Note: this is "fast" - so don't need to worry too much about
            # interruption case.
            try:
                fig, ax = plt.subplots(*args, **kwargs)
            except BaseException as e:
                ex = e
            finally:
                ev.set()

    cb = _Cb()
    # Send fake event to our callback to trigger it (actual contents unimportant)
    cb("start", {"time": 0, "uid": ""})
    if not ev.wait(PYPLOT_SUBPLOTS_TIMEOUT):
        raise OSError("Could not create matplotlib figure and axes (timeout)")
    if fig is None or ax is None:
        raise OSError(
            "Could not create matplotlib figure and axes (got fig=%s, ax=%s, ex=%s)", fig, ax, ex
        )
    return fig, ax

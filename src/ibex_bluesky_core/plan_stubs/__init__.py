"""Core plan stubs."""

from collections.abc import Generator
from typing import Callable, ParamSpec, TypeVar, cast

import bluesky.plan_stubs as bps
from bluesky.utils import Msg

from ibex_bluesky_core.devices.simpledae import SimpleDae

P = ParamSpec("P")
T = TypeVar("T")


CALL_SYNC_MSG_KEY = "ibex_bluesky_core_call_sync"
CALL_QT_AWARE_MSG_KEY = "ibex_bluesky_core_call_qt_aware"


__all__ = ["call_qt_aware", "call_sync"]


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
        *args: Arbitrary arguments to be passed to the wrapped function
        **kwargs: Arbitrary keyword arguments to be passed to the wrapped function

    Returns:
        The return value of the wrapped function

    """
    yield from bps.clear_checkpoint()
    return cast(T, (yield Msg(CALL_SYNC_MSG_KEY, func, *args, **kwargs)))


def call_qt_aware(
    func: Callable[P, T], *args: P.args, **kwargs: P.kwargs
) -> Generator[Msg, None, T]:
    """Call a matplotlib function in a Qt-aware context, from within a plan.

    If matplotlib is using a Qt backend then UI operations are run on the Qt thread via Qt signals.

    Only matplotlib functions may be run using this plan stub.

    Args:
        func: A matplotlib function reference.
        *args: Arbitrary arguments, passed through to matplotlib.pyplot.subplots
        **kwargs: Arbitrary keyword arguments, passed through to matplotlib.pyplot.subplots

    Raises:
        ValueError: if the passed function is not a matplotlib function.

    Returns:
        The return value of the wrapped function

    """
    # Limit potential for misuse - constrain to just running matplotlib functions.
    if not getattr(func, "__module__", "").startswith("matplotlib"):
        raise ValueError("Only matplotlib functions should be passed to call_qt_aware")

    yield from bps.clear_checkpoint()
    return cast(T, (yield Msg(CALL_QT_AWARE_MSG_KEY, func, *args, **kwargs)))


def set_num_periods(dae: SimpleDae, nperiods: int) -> Generator[Msg, None, None]:
    """Set the number of periods for a DAE.

    Args:
        dae (SimpleDae): DAE object.
        nperiods (int): number of periods to set.

    """
    yield from bps.mv(dae.number_of_periods, nperiods)  # type: ignore
    actual = yield from bps.rd(dae.number_of_periods)
    if actual != nperiods:
        raise ValueError(
            f"Could not set {nperiods} periods on DAE (probably requesting too many points, "
            f"or already running)"
        )

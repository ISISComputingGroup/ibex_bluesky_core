"""Core plan stubs."""

import logging
from collections.abc import Callable, Generator
from typing import Any, ParamSpec, TypeVar, cast

from bluesky import plan_stubs as bps
from bluesky.plan_stubs import trigger_and_read
from bluesky.preprocessors import finalize_wrapper
from bluesky.protocols import Readable
from bluesky.utils import Msg
from ophyd_async.epics.motor import Motor, UseSetMode

from ibex_bluesky_core.devices.reflectometry import ReflParameter
from ibex_bluesky_core.plan_stubs._dae_table_wrapper import with_dae_tables
from ibex_bluesky_core.plan_stubs._num_periods_wrapper import with_num_periods
from ibex_bluesky_core.plan_stubs._time_channels_wrapper import with_time_channels
from ibex_bluesky_core.utils import NamedReadableAndMovable

logger = logging.getLogger(__name__)

P = ParamSpec("P")
T = TypeVar("T")


CALL_SYNC_MSG_KEY = "ibex_bluesky_core_call_sync"
CALL_QT_AWARE_MSG_KEY = "ibex_bluesky_core_call_qt_aware"


__all__ = [
    "call_qt_aware",
    "call_sync",
    "polling_plan",
    "prompt_user_for_choice",
    "redefine_motor",
    "redefine_refl_parameter",
    "with_dae_tables",
    "with_num_periods",
    "with_time_channels",
]


def call_sync(func: Callable[P, T], *args: P.args, **kwargs: P.kwargs) -> Generator[Msg, None, T]:
    """Call a synchronous user function in a plan, and returns the result of that call.

    Attempts to guard against the most common pitfalls of naive implementations, for example:

    - Blocking the whole event loop
    - Breaking keyboard interrupt handling

    It does not necessarily guard against all possible cases, and as such it is *recommended* to
    use native bluesky functionality wherever possible in preference to this plan stub. This should
    be seen as an escape-hatch.

    The wrapped function will be run in a new thread.

    Args:
        func: A callable to run.
        *args: Arbitrary arguments to be passed to the wrapped function
        **kwargs: Arbitrary keyword arguments to be passed to the wrapped function

    Returns:
        The return value of the wrapped function

    """
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

    return cast(T, (yield Msg(CALL_QT_AWARE_MSG_KEY, func, *args, **kwargs)))


def redefine_motor(
    motor: Motor, position: float, *, sleep: float = 1
) -> Generator[Msg, None, None]:
    """Redefines the current positions of a motor.

    Note:
        This does not move the motor, it just redefines its position to be the given value.

    Args:
        motor: The motor to set a position on.
        position: The position to set.
        sleep: An amount of time to sleep, in seconds, after redefining. Defaults to 1 second.
            This avoids race conditions where a motor is redefined and then immediately moved.

    """
    logger.info("Redefining motor %s to %s", motor.name, position)

    def make_motor_usable() -> Generator[Msg, None, None]:
        yield from bps.abs_set(motor.set_use_switch, UseSetMode.USE)
        yield from bps.sleep(sleep)

    def inner() -> Generator[Msg, None, None]:
        yield from bps.abs_set(motor.set_use_switch, UseSetMode.SET)
        yield from bps.abs_set(motor.user_setpoint, position)

    return (yield from finalize_wrapper(inner(), make_motor_usable()))


def redefine_refl_parameter(
    parameter: ReflParameter, position: float
) -> Generator[Msg, None, None]:
    """Redefines the current positions of a reflectometry parameter.

    Note:
        This does not move the parameter, it just redefines its position to be the given value.

    Args:
        parameter: The reflectometry parameter to set a position on.
        position: The position to set.

    """
    if parameter.redefine is None:
        raise ValueError(f"Parameter {parameter.name} cannot be redefined.")
    logger.info("Redefining refl parameter %s to %s", parameter.name, position)
    yield from bps.mv(parameter.redefine, position)


def prompt_user_for_choice(*, prompt: str, choices: list[str]) -> Generator[Msg, None, str]:
    """Prompt the user to choose between a limited set of options.

    Args:
        prompt: The user prompt string.
        choices: A list of allowable choices.

    Returns:
        One of the entries in the choices list.

    """
    choice = yield from call_sync(input, prompt)
    while choice not in choices:
        choice = yield from call_sync(input, prompt)

    return choice


def polling_plan(
    motor: NamedReadableAndMovable, readable: Readable[Any], destination: float
) -> Generator[Msg, None, None]:
    """Move to a destination but drop updates from readable if motor position has not changed.

    .. note::

        This does not start a run, this should be done with a
        :py:obj:`~bluesky.preprocessors.run_decorator` or similar in an
        outer plan which calls this plan.

    Args:
        motor: the motor to move.
        readable: the readable to read updates from, but drop if motor has not moved.
        destination: the destination position.

    Returns:
        None

    """
    yield from bps.checkpoint()
    yield from bps.create()
    reading = yield from bps.read(motor)
    yield from bps.read(readable)
    yield from bps.save()

    # start the ramp
    status = yield from bps.abs_set(motor, destination, wait=False)
    while not status.done:
        yield from bps.create()
        new_reading = yield from bps.read(motor)
        yield from bps.read(readable)

        if new_reading[motor.name]["value"] == reading[motor.name]["value"]:
            yield from bps.drop()
        else:
            reading = new_reading
            yield from bps.save()

    # take a 'post' data point
    yield from trigger_and_read([motor, readable])

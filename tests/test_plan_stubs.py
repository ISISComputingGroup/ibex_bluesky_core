# pyright: reportMissingParameterType=false
import time
from asyncio import CancelledError
from unittest.mock import MagicMock, call, patch

import matplotlib.pyplot as plt
import pytest
from bluesky.utils import Msg
from ophyd_async.epics.motor import UseSetMode
from ophyd_async.plan_stubs import ensure_connected
from ophyd_async.testing import callback_on_mock_put, get_mock_put, set_mock_value

from ibex_bluesky_core.devices.block import BlockMot
from ibex_bluesky_core.devices.reflectometry import ReflParameter
from ibex_bluesky_core.plan_stubs import (
    CALL_QT_AWARE_MSG_KEY,
    call_qt_aware,
    call_sync,
    prompt_user_for_choice,
    redefine_motor,
    redefine_refl_parameter,
)
from ibex_bluesky_core.run_engine._msg_handlers import call_sync_handler


def test_call_sync_returns_result(RE):
    def f(arg, keyword_arg):
        assert arg == "foo"
        assert keyword_arg == "bar"
        return 123

    result = RE(call_sync(f, "foo", keyword_arg="bar"))

    assert result.plan_result == 123


@pytest.mark.filterwarnings("ignore::pytest.PytestUnhandledThreadExceptionWarning")
def test_call_sync_throws_exception(RE):
    def f():
        raise ValueError("broke it")

    with pytest.raises(ValueError, match="broke it"):
        RE(call_sync(f))


@pytest.mark.parametrize("err", [(KeyboardInterrupt,), (CancelledError,)])
async def test_call_sync_handler_blocking_python(err: type[BaseException]):
    def f():
        while True:
            pass

    with patch("ibex_bluesky_core.run_engine._msg_handlers.Event") as evt:
        evt.return_value.wait.side_effect = err
        msg = Msg("", f)
        with pytest.raises(err):
            await call_sync_handler(msg)


@pytest.mark.parametrize("err", [(KeyboardInterrupt,), (CancelledError,)])
async def test_call_sync_handler_blocking_native(err: type[BaseException]):
    def f():
        while True:
            time.sleep(1)

    with patch("ibex_bluesky_core.run_engine._msg_handlers.Event") as evt:
        evt.return_value.wait.side_effect = err
        msg = Msg("", f)
        with pytest.raises(err):
            await call_sync_handler(msg)


def test_call_sync_waits_for_completion(RE):
    def f():
        time.sleep(1)

    start = time.monotonic()
    RE(call_sync(f))
    end = time.monotonic()

    assert end - start == pytest.approx(1, abs=0.2)


def test_call_qt_aware_returns_result(RE):
    def f(arg, keyword_arg):
        assert arg == "foo"
        assert keyword_arg == "bar"
        return 123

    def plan():
        return (yield Msg(CALL_QT_AWARE_MSG_KEY, f, "foo", keyword_arg="bar"))

    result = RE(plan())

    assert result.plan_result == 123


def test_call_qt_aware_throws_exception(RE):
    def f():
        raise ValueError("broke it")

    def plan():
        return (yield Msg(CALL_QT_AWARE_MSG_KEY, f))

    with pytest.raises(ValueError, match="broke it"):
        RE(plan())


def test_call_qt_aware_matplotlib_function(RE):
    mock = MagicMock(spec=plt.close)
    mock.__module__ = "matplotlib.pyplot"
    mock.return_value = 123

    def plan():
        return (yield from call_qt_aware(mock, "all"))

    result = RE(plan())
    assert result.plan_result == 123
    mock.assert_called_once_with("all")


def test_call_qt_aware_non_matplotlib_function(RE):
    mock = MagicMock()
    mock.__module__ = "some_random_module"

    def plan():
        return (yield from call_qt_aware(mock, "arg", keyword_arg="kwarg"))

    with pytest.raises(
        ValueError, match="Only matplotlib functions should be passed to call_qt_aware"
    ):
        RE(plan())

    mock.assert_not_called()


def test_redefine_motor(RE):
    motor = BlockMot(prefix="", block_name="some_motor")

    def plan():
        yield from ensure_connected(motor, mock=True)
        yield from redefine_motor(motor, 42.0)

    RE(plan())

    get_mock_put(motor.set_use_switch).assert_has_calls(
        [call(UseSetMode.SET, wait=True), call(UseSetMode.USE, wait=True)]
    )

    get_mock_put(motor.user_setpoint).assert_called_once_with(42.0, wait=True)


async def test_redefine_refl_parameter(RE):
    param = ReflParameter(prefix="", name="some_refl_parameter", changing_timeout_s=60)
    await param.connect(mock=True)

    callback_on_mock_put(
        param.redefine.define_pos_sp, lambda *a, **k: set_mock_value(param.redefine.changed, True)
    )

    RE(redefine_refl_parameter(param, 42.0))

    get_mock_put(param.redefine.define_pos_sp).assert_called_once_with(42.0, wait=True)


def test_get_user_input(RE):
    with patch("ibex_bluesky_core.plan_stubs.input") as mock_input:
        mock_input.__name__ = "mock"
        mock_input.side_effect = ["foo", "bar", "baz"]

        result = RE(prompt_user_for_choice(prompt="choice?", choices=["bar", "baz"]))
        assert result.plan_result == "bar"

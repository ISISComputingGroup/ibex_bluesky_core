# pyright: reportMissingParameterType=false
import re
import time
from asyncio import CancelledError
from unittest.mock import patch

import matplotlib
import pytest
from bluesky.utils import Msg

from ibex_bluesky_core.plan_stubs import CALL_QT_SAFE_MSG_KEY, call_sync, matplotlib_subplots
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


def test_call_qt_safe_returns_result(RE):
    def f(arg, keyword_arg):
        assert arg == "foo"
        assert keyword_arg == "bar"
        return 123

    def plan():
        return (yield Msg(CALL_QT_SAFE_MSG_KEY, f, "foo", keyword_arg="bar"))

    result = RE(plan())

    assert result.plan_result == 123


def test_call_qt_safe_throws_exception(RE):
    def f():
        raise ValueError("broke it")

    def plan():
        return (yield Msg(CALL_QT_SAFE_MSG_KEY, f))

    with pytest.raises(ValueError, match="broke it"):
        RE(plan())


@pytest.mark.skipif("qt" not in matplotlib.get_backend().lower(), reason="Qt not available")
def test_call_qt_safe_blocking_causes_descriptive_timeout_error(RE):
    def f():
        time.sleep(0.2)

    def plan():
        return (yield Msg(CALL_QT_SAFE_MSG_KEY, f))

    with patch("ibex_bluesky_core.run_engine._msg_handlers.CALL_QT_SAFE_TIMEOUT", new=0.1):
        with pytest.raises(
            TimeoutError,
            match=re.escape(
                "Long-running function 'f' passed to call_qt_safe_handler. "
                "Functions passed to call_qt_safe_handler must be faster than 0.1s."
            ),
        ):
            RE(plan())


def test_matplotlib_subplots_calls_pyplot_subplots(RE):
    def plan():
        return (yield from matplotlib_subplots("foo", keyword="bar"))

    with patch("ibex_bluesky_core.plan_stubs.plt.subplots") as mock_pyplot_subplots:
        RE(plan())
        mock_pyplot_subplots.assert_called_once_with("foo", keyword="bar")

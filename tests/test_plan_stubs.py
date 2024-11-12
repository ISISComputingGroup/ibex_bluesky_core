# pyright: reportMissingParameterType=false

import time
from asyncio import CancelledError
from unittest.mock import patch

import pytest
from bluesky.utils import Msg

from ibex_bluesky_core.plan_stubs import call_sync
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

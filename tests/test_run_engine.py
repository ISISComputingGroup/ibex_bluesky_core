# pyright: reportMissingParameterType=false

import threading
from typing import Any, Generator
from unittest.mock import MagicMock

import bluesky.plan_stubs as bps
import pytest
from bluesky.run_engine import RunEngineResult
from bluesky.utils import Msg, RequestAbort, RunEngineInterrupted

from ibex_bluesky_core.run_engine import _DuringTask, get_run_engine


def test_run_engine_is_singleton():
    re1 = get_run_engine()
    re2 = get_run_engine()

    assert re1 is re2


def test_run_engine_can_be_used_for_simple_plan(RE):
    def plan() -> Generator[Msg, None, Any]:
        yield from bps.null()
        return "plan_result"

    assert RE(plan()) == RunEngineResult((), "plan_result", "success", False, "", None)


def test_run_engine_reports_aborted_plan(RE):
    def pausing_plan() -> Generator[Msg, None, None]:
        yield from bps.pause()

    with pytest.raises(RunEngineInterrupted):
        RE(pausing_plan())

    result: RunEngineResult = RE.abort("abort reason")

    assert result.run_start_uids == ()
    assert result.plan_result == RE.NO_PLAN_RETURN
    assert result.exit_status == "abort"
    assert result.interrupted
    assert isinstance(result.exception, RequestAbort)
    assert result.reason == "abort reason"


def test_run_engine_reports_plan_which_pauses_resumes_and_then_returns(RE):
    def pausing_plan() -> Generator[Msg, None, str]:
        yield from bps.pause()
        return "plan result"

    with pytest.raises(RunEngineInterrupted):
        RE(pausing_plan())

    result: RunEngineResult = RE.resume()

    assert result == RunEngineResult((), "plan result", "success", False, "", None)


def test_run_engine_can_emit_documents_to_custom_subscriber(RE):
    def basic_plan() -> Generator[Msg, None, None]:
        yield from bps.open_run()
        yield from bps.close_run()

    documents = []
    RE.subscribe(lambda typ, _doc: documents.append(typ))

    RE(basic_plan())

    # Expected basic series of document types for a start run/stop run sequence.
    assert documents == ["start", "stop"]


def test_during_task_does_wait_with_small_timeout():
    task = _DuringTask()

    event = MagicMock(spec=threading.Event)
    event.wait.side_effect = [False, True]

    task.block(event)

    event.wait.assert_called_with(0.1)
    assert event.wait.call_count == 2

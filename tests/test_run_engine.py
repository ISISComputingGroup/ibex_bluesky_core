# pyright: reportMissingParameterType=false

import threading
from collections.abc import Generator
from typing import Any
from unittest import mock
from unittest.mock import MagicMock

import bluesky.plan_stubs as bps
import bluesky.preprocessors as bpp
import pytest
from bluesky.run_engine import RunEngineResult
from bluesky.utils import Msg, RequestAbort, RunEngineInterrupted

from ibex_bluesky_core.run_engine import _DuringTask, get_kafka_topic_name, get_run_engine, run_plan
from ibex_bluesky_core.version import version


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


def test_runengine_has_version_number_as_metadata(RE):
    assert RE.md["versions"]["ibex_bluesky_core"] == version


def test_run_plan_rejects_reentrant_call(RE):
    def _null():
        yield from bps.null()

    def plan():
        yield from _null()
        run_plan(_null())

    with pytest.raises(
        RuntimeError, match="reentrant run_plan call attempted; this cannot be supported"
    ):
        run_plan(plan())


def test_run_plan_rejects_call_if_re_already_busy(RE):
    def _null():
        yield from bps.null()

    with pytest.raises(RunEngineInterrupted):
        RE(bps.pause())
    assert RE.state == "paused"
    with pytest.raises(RuntimeError):
        run_plan(_null())

    RE.halt()


def test_run_plan_runs_cleanup_on_interruption(RE):
    cleaned_up = False

    def plan():
        def cleanup():
            yield from bps.null()
            nonlocal cleaned_up
            cleaned_up = True

        yield from bpp.finalize_wrapper(bps.pause(), cleanup())

    with pytest.raises(
        RunEngineInterrupted,
        match="bluesky RunEngine interrupted; not resumable as running via run_plan",
    ):
        run_plan(plan())

    assert RE.state == "idle"
    assert cleaned_up


def test_run_plan_happy_path(RE):
    def plan():
        yield from bps.null()
        return "happy_path_result"

    result = run_plan(plan())
    assert result.plan_result == "happy_path_result"
    assert result.exit_status == "success"


def test_get_kafka_topic_name():
    with mock.patch("ibex_bluesky_core.run_engine.os.environ.get", return_value="FOO"):
        assert get_kafka_topic_name() == "FOO_bluesky"

    with mock.patch("ibex_bluesky_core.run_engine.os.environ.get", return_value="NDXBAR"):
        assert get_kafka_topic_name() == "BAR_bluesky"

    with mock.patch("ibex_bluesky_core.run_engine.os.environ.get", return_value="NDHBAZ"):
        assert get_kafka_topic_name() == "BAZ_bluesky"

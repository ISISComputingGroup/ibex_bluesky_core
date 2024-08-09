import json
from pathlib import Path
import threading
from typing import Any, Generator
from unittest.mock import MagicMock, mock_open, patch

import bluesky.plan_stubs as bps
import pytest
from bluesky.run_engine import RunEngine, RunEngineResult
from bluesky.utils import Msg, RequestAbort, RequestStop, RunEngineInterrupted
from ibex_bluesky_core.run_engine import _DuringTask, get_run_engine
import os


@pytest.fixture
def RE() -> RunEngine:
    get_run_engine.cache_clear()
    return get_run_engine()


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
    assert documents == ["start", "descriptor", "stop"]


def test_run_engine_emits_documents_for_interruptions(RE):
    def pausing_plan() -> Generator[Msg, None, None]:
        yield from bps.open_run(md={"reason": "run one start"})
        yield from bps.pause()
        yield from bps.close_run(reason="run one end")
        yield from bps.open_run(md={"reason": "run two start"})
        yield from bps.pause()
        yield from bps.close_run(reason="run two end")

    doc_types = []
    docs = []

    def sub(typ, doc):
        doc_types.append(typ)
        docs.append({typ: doc})

    RE.subscribe(sub)

    with pytest.raises(RunEngineInterrupted):
        RE(pausing_plan())

    with pytest.raises(RunEngineInterrupted):
        RE.resume()

    result: RunEngineResult = RE.stop()

    assert doc_types == [
        "start",  # Open run 1
        "descriptor",  # Open run descriptor
        "event",  # First pause
        "event",  # Resume
        "stop",  # Close run 1
        "start",  # Open run 2
        "descriptor",  # Open run descriptor
        "event",  # Second pause
        "stop",  # Close run 2
    ]

    assert docs[0]["start"]["reason"] == "run one start"
    assert docs[2]["event"]["data"] == {"interruption": "pause"}
    assert docs[3]["event"]["data"] == {"interruption": "resume"}
    assert docs[4]["stop"]["reason"] == "run one end"

    assert docs[5]["start"]["reason"] == "run two start"
    assert docs[7]["event"]["data"] == {"interruption": "pause"}
    assert docs[8]["stop"]["reason"] == ""  # Stopped by run engine, *not* our close_run

    assert len(result.run_start_uids) == 2  # Both runs started
    assert result.plan_result == RE.NO_PLAN_RETURN
    assert result.exit_status == "success"
    assert result.interrupted
    assert result.exception == RequestStop
    assert result.reason == ""


def test_during_task_does_wait_with_small_timeout():
    task = _DuringTask()

    event = MagicMock(spec=threading.Event)
    event.wait.side_effect = [False, True]

    task.block(event)

    event.wait.assert_called_with(0.1)
    assert event.wait.call_count == 2

def test_run_engine_logs_all_documents(RE):

    m = mock_open()
    filepath: str
    DEFAULT_LOG_LOCATION = Path(os.path.join("C:\\","instrument","var","logs","bluesky","raw_documents"))

    def basic_plan() -> Generator[Msg, None, None]:
        yield from bps.open_run()
        yield from bps.close_run()

    with patch('ibex_bluesky_core.callbacks.document_logger.open', m):
        result: RunEngineResult = RE(basic_plan())
        filepath = os.path.join(DEFAULT_LOG_LOCATION, f"{result.run_start_uids[0]}.log")
    
    for i in range (0,3):
        assert m.call_args_list[i].args == (filepath, 'a') # Checks that the file is opened 3 times, for open, descriptor then stop

    handle = m()
    document = json.loads(handle.write.mock_calls[-1].args[0])
    
    assert document['document']['exit_status'] == "success" # In the stop document to be written, check that the run is successful with no interruptions
    assert document['document']['num_events']['interruptions'] == 0

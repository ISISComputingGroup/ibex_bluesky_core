# pyright: reportMissingParameterType=false

import json
from pathlib import Path
from typing import Generator
from unittest.mock import mock_open, patch

import bluesky.plan_stubs as bps
from bluesky.run_engine import RunEngineResult
from bluesky.utils import Msg


def test_run_engine_logs_all_documents(RE):
    m = mock_open()
    log_location = Path("C:\\") / "instrument" / "var" / "logs" / "bluesky" / "raw_documents"

    def basic_plan() -> Generator[Msg, None, None]:
        yield from bps.open_run()
        yield from bps.close_run()

    with patch("ibex_bluesky_core.callbacks.document_logger.open", m):
        result: RunEngineResult = RE(basic_plan())
        filepath = log_location / f"{result.run_start_uids[0]}.log"

    for i in range(0, 2):
        assert m.call_args_list[i].args == (filepath, "a")
        # Checks that the file is opened 2 times, for open and then stop

    handle = m()
    document = json.loads(handle.write.mock_calls[-1].args[0])

    # In the stop document to be written, check that the run is successful
    assert document["document"]["exit_status"] == "success"

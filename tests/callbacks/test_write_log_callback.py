# pyright: reportMissingParameterType=false

import pytest
import json
from unittest.mock import mock_open, MagicMock, patch
from pathlib import Path
from typing import Generator

import bluesky.plan_stubs as bps
from bluesky.run_engine import RunEngineResult
from bluesky.utils import Msg

from ibex_bluesky_core.callbacks.write_log import OutputLoggingCallback



m = mock_open()
save_path = Path("C:\\") / "instrument" / "var" / "logs" / "bluesky" / "output_files"
doc = {"uid": "23097941-783c-4353-8809-d8038a52517f", 
        "time": 1726242068.520683, 
        "versions": {"bluesky": "1.13.0a4"}, 
        "scan_id": 1, "plan_type": "generator", 
        "plan_name": "example",
        "name": "primary",
        "test": "test",
        "descriptor": "23097941-783c-4353-8809-d8038a52517f",
        "data" :{
            'mot-setpoint_readback': 1.0,
            'mot': 1.0,
            'DAE-good_uah': 0.8474488258361816,
            'DAE': 0.8474488258361816
        } }

testing_function = OutputLoggingCallback(['block', 'dae'], save_path)

def test_start_data(RE):    
    with patch("ibex_bluesky_core.callbacks.write_log.open", m) as mock_file:
        testing_function.start(doc)
        result = save_path / f"{doc['uid']}.txt"

    mock_file.assert_called_with(result, 'a')

    expected_content = f"{list(doc.keys())[-1]}: {list(doc.values())[-1]}\n"
    mock_file().write.assert_called_with(expected_content)

def test_descriptor_data(RE):
    testing_function.descriptor(doc)

    assert doc['uid'] in testing_function.descriptors
    assert testing_function.descriptors[doc['uid']] == doc

def test_event_data(RE):
    testing_function.event(doc)

    assert doc['DAE'] in testing_function.event

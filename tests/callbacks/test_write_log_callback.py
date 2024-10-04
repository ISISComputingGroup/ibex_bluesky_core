# pyright: reportMissingParameterType=false

import pytest
from unittest.mock import mock_open, MagicMock, patch
from pathlib import Path

from ibex_bluesky_core.callbacks.file_logger import HumanReadableOutputFileLoggingCallback


m = mock_open()
save_path = Path("C:\\") / "instrument" / "var" / "logs" / "bluesky" / "output_files"
doc = {
    "uid": "23097941-783c-4353-8809-d8038a52517f",
    "time": 1726242068.520683,
    "versions": {"bluesky": "1.13.0a4"},
    "scan_id": 1,
    "plan_type": "generator",
    "plan_name": "example",
    "name": "primary",
    "test": "test",
    "descriptor": "23097941-783c-4353-8809-d8038a52517f",
    "data": {
        "mot-setpoint_readback": 1.0,
        "mot": 1.0,
        "DAE-good_uah": 0.8474488258361816,
        "DAE": 0.8474488258361816,
    },
}


@pytest.fixture
def cb() -> HumanReadableOutputFileLoggingCallback:
    return HumanReadableOutputFileLoggingCallback(save_path, ["block", "dae"])


def test_start_data(cb):
    with patch("ibex_bluesky_core.callbacks.file_logger.open", m) as mock_file:
        cb.start(doc)
        result = save_path / f"{doc['uid']}.txt"

    mock_file.assert_called_with(result, "a")

    expected_content = f"{list(doc.keys())[-1]}: {list(doc.values())[-1]}\n"
    mock_file.write.assert_called_with(expected_content)


def test_descriptor_data(cb):
    cb.descriptor(doc)

    assert doc["uid"] in cb.descriptors
    assert cb.descriptors[doc["uid"]] == doc


def test_event_data(cb):
    cb.event(doc)

    assert doc["DAE"] in cb.event

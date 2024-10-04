# pyright: reportMissingParameterType=false

import pytest
from unittest.mock import mock_open, MagicMock, patch
from pathlib import Path

from event_model import EventDescriptor, RunStart, Event

from ibex_bluesky_core.callbacks.file_logger import HumanReadableOutputFileLoggingCallback


m = mock_open()
save_path = Path("C:\\") / "instrument" / "var" / "logs" / "bluesky" / "output_files"


@pytest.fixture
def cb() -> HumanReadableOutputFileLoggingCallback:
    return HumanReadableOutputFileLoggingCallback(save_path, ["block", "dae"])


@patch("ibex_bluesky_core.callbacks.file_logger.Path", autospec=True)
def test_header_data_all_available_on_start(_, cb):
    time = 1728049423.5860472
    uid = "test123"
    scan_id = 1234
    run_start = RunStart(time=time, uid=uid, scan_id=scan_id)
    with patch("ibex_bluesky_core.callbacks.file_logger.open", m) as mock_file:
        cb.start(run_start)
        result = save_path / f"{run_start['uid']}.txt"

    mock_file.assert_called_with(result, "a")
    # assert not mock_file().write.assert_any_call(f"scan_id: {scan_id}")
    # time should have been renamed to start_time and converted to human readable
    mock_file().write.assert_any_call("start_time: 2024-10-04 14:43:43\n")

    mock_file().write.assert_any_call(f"uid: {uid}\n")

    # scan id is in the exclude list should not have been written, therefore call count should only be 2
    assert mock_file().write.call_count == 2


def test_descriptor_data_does_nothing_if_doc_not_called_primary(cb):
    desc = EventDescriptor(
        data_keys={}, uid="someuid", time=123.4, run_start="n/a", name="notprimary"
    )
    cb.descriptor(desc)

    assert desc["uid"] not in cb.descriptors


def test_descriptor_adds_descriptor_if_name_primary(cb):
    desc = EventDescriptor(data_keys={}, uid="someuid", time=123.4, run_start="n/a", name="primary")

    cb.descriptor(desc)
    assert desc["uid"] in cb.descriptors
    assert cb.descriptors[desc["uid"]] == desc


def test_event_respects_precision_of_value():
    desc = EventDescriptor()
    event = Event()
    pass


def test_event_gives_raw_value_without_precision():
    desc = EventDescriptor()
    event = Event()
    pass


def test_event_ignores_precision_if_value_not_float():
    desc = EventDescriptor()
    event = Event()
    pass


def test_event_writes_units_line_followed_by_data_with_units_specified():
    desc = EventDescriptor()
    event = Event()
    pass


def test_event_writes_units_line_followed_by_data_with_units_not_specified():
    desc = EventDescriptor()
    event = Event()
    pass


def test_stop_clears_descriptors(cb):
    cb.descriptors["test"] = EventDescriptor(uid="test", run_start="", time=0.1, data_keys={})

    cb.stop(EventDescriptor(uid="test1", run_start="", time=0.2, data_keys={}))

    assert not cb.descriptors

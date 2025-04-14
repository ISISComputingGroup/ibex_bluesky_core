# pyright: reportMissingParameterType=false
# pyright: reportCallIssue=false

from pathlib import Path
from platform import node
from unittest.mock import call, mock_open, patch

import pytest
from event_model import DataKey, Event, EventDescriptor, RunStart, RunStop

from ibex_bluesky_core.callbacks import HumanReadableFileCallback

save_path = Path("C:\\") / "instrument" / "var" / "logs" / "bluesky" / "output_files"


@pytest.fixture
def cb() -> HumanReadableFileCallback:
    return HumanReadableFileCallback(["block", "dae"], output_dir=save_path)


def test_header_data_all_available_on_start(cb):
    time = 1728049423.5860472
    uid = "test123"
    scan_id = 1234
    run_start = RunStart(
        time=time, uid=uid, scan_id=scan_id, rb_number="0", detectors=["dae"], motors=("block",)
    )
    with (
        patch("ibex_bluesky_core.callbacks._file_logger.open", mock_open()) as mock_file,
        patch("ibex_bluesky_core.callbacks._file_logger.os.makedirs"),
    ):
        cb.start(run_start)
        result = (
            save_path
            / f"{run_start.get('rb_number', None)}"
            / f"{node()}_block_2024-10-04_13-43-43Z.txt"
        )

    mock_file.assert_called_with(result, "a", newline="\n", encoding="utf-8")
    writelines_call_args = mock_file().writelines.call_args[0][0]
    # time should have been renamed to start_time and converted to human readable
    assert "start_time: 2024-10-04 13:43:43\n" in writelines_call_args
    assert f"uid: {uid}\n" in writelines_call_args


def test_no_rb_number_folder(cb):
    time = 1728049423.5860472
    uid = "test123"
    scan_id = 1234
    run_start = RunStart(time=time, uid=uid, scan_id=scan_id, detectors=["dae"], motors=("block",))

    with (
        patch("ibex_bluesky_core.callbacks._file_logger.open", mock_open()) as mock_file,
        patch("ibex_bluesky_core.callbacks._file_logger.os.makedirs") as mock_mkdir,
    ):
        cb.start(run_start)
        result = save_path / "Unknown RB" / f"{node()}_block_2024-10-04_13-43-43Z.txt"
        assert mock_mkdir.called

    mock_file.assert_called_with(result, "a", newline="\n", encoding="utf-8")
    # time should have been renamed to start_time and converted to human readable
    writelines_call_args = mock_file().writelines.call_args[0][0]
    assert "start_time: 2024-10-04 13:43:43\n" in writelines_call_args
    assert f"uid: {uid}\n" in writelines_call_args


def test_no_motors_doesnt_append_to_filename(cb):
    time = 1728049423.5860472
    uid = "test123"
    scan_id = 1234
    run_start = RunStart(time=time, uid=uid, scan_id=scan_id, detectors=["dae"])

    with (
        patch("ibex_bluesky_core.callbacks._file_logger.open", mock_open()) as mock_file,
        patch("ibex_bluesky_core.callbacks._file_logger.os.makedirs") as mock_mkdir,
    ):
        cb.start(run_start)
        result = save_path / "Unknown RB" / f"{node()}_2024-10-04_13-43-43Z.txt"
        assert mock_mkdir.called

    mock_file.assert_called_with(result, "a", newline="\n", encoding="utf-8")
    # time should have been renamed to start_time and converted to human readable
    writelines_call_args = mock_file().writelines.call_args[0][0]
    assert "start_time: 2024-10-04 13:43:43\n" in writelines_call_args
    assert f"uid: {uid}\n" in writelines_call_args


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


def test_event_prints_header_with_units_and_respects_precision_of_value_on_first_message():
    field_name = "test"
    cb = HumanReadableFileCallback([field_name], output_dir=save_path)
    # This actually contains the precision
    expected_value = 1.234567
    units = "mm"
    prec = 4
    descriptor = "somedescriptor"
    uid = "123456"
    desc = EventDescriptor(uid=uid, data_keys={field_name: DataKey(precision=prec, units=units)})
    cb.descriptors[descriptor] = desc
    cb.filename = Path("test")

    # This just contains the value
    event = Event(uid=uid, data={field_name: expected_value}, descriptor=descriptor, seq_num=1)
    with patch("ibex_bluesky_core.callbacks._file_logger.open", mock_open()) as mock_file:
        cb.event(event)

    mock_file.assert_called_with(cb.filename, "a", newline="", encoding="utf-8")
    first_call = call(f"\n{field_name}({units})\n")
    second_call = call(f"{expected_value:.{prec}f}\n")
    mock_file().write.assert_has_calls([first_call, second_call])
    assert mock_file().write.call_count == 2


def test_event_prints_header_without_units_and_does_not_truncate_precision_if_no_precision():
    field_name = "test"
    cb = HumanReadableFileCallback([field_name], output_dir=save_path)
    # This actually contains the precision
    expected_value = 1.2345
    units = None
    prec = None
    descriptor = "somedescriptor"
    uid = "123456"
    desc = EventDescriptor(uid=uid, data_keys={field_name: DataKey(precision=prec, units=units)})
    cb.descriptors[descriptor] = desc
    cb.filename = Path("test")

    # This just contains the value
    event = Event(uid=uid, data={field_name: expected_value}, descriptor=descriptor, seq_num=1)
    with patch("ibex_bluesky_core.callbacks._file_logger.open", mock_open()) as mock_file:
        cb.event(event)

    mock_file.assert_called_with(cb.filename, "a", newline="", encoding="utf-8")
    mock_file().write.assert_has_calls([call("\ntest\n"), call("1.2345\n")])
    assert mock_file().write.call_count == 2


def test_event_prints_header_only_on_first_event_and_does_not_truncate_if_not_float_value():
    field_name = "test"
    cb = HumanReadableFileCallback([field_name], output_dir=save_path)
    # This actually contains the precision
    expected_value = 12345
    units = "mm"
    prec = 3
    descriptor = "somedescriptor"
    uid = "123456"
    desc = EventDescriptor(uid=uid, data_keys={field_name: DataKey(precision=prec, units=units)})
    cb.descriptors[descriptor] = desc
    cb.filename = Path("test")

    # This just contains the value
    second_event = Event(
        uid=uid, data={field_name: expected_value}, descriptor=descriptor, seq_num=2
    )

    with patch("ibex_bluesky_core.callbacks._file_logger.open", mock_open()) as mock_file:
        cb.event(second_event)

    mock_file.assert_called_with(cb.filename, "a", newline="", encoding="utf-8")

    mock_file().write.assert_called_once_with(f"{expected_value}\n")
    assert mock_file().write.call_count == 1


def test_event_called_before_filename_specified_does_nothing():
    field_name = "test"
    cb = HumanReadableFileCallback([field_name], output_dir=save_path)
    # This actually contains the precision
    expected_value = 12345
    units = "mm"
    prec = 3
    descriptor = "somedescriptor"
    uid = "123456"
    desc = EventDescriptor(uid=uid, data_keys={field_name: DataKey(precision=prec, units=units)})
    cb.descriptors[descriptor] = desc

    # This just contains the value
    second_event = Event(
        uid=uid, data={field_name: expected_value}, descriptor=descriptor, seq_num=2
    )

    with patch("ibex_bluesky_core.callbacks._file_logger.open", mock_open()) as mock_file:
        cb.event(second_event)

    mock_file.assert_not_called()


def test_stop_clears_descriptors(cb):
    cb.descriptors["test"] = EventDescriptor(uid="test", run_start="", time=0.1, data_keys={})

    cb.stop(RunStop(uid="test", run_start="", time=0.1, exit_status="success"))

    assert not cb.descriptors

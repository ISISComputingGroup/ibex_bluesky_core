# pyright: reportMissingParameterType=false
# pyright: reportArgumentType=false
import numpy as np
import pytest
from event_model import EventDescriptor, RunStart, RunStop
from matplotlib import pyplot as plt

from ibex_bluesky_core.callbacks.reflectometry import (
    DetMapAngleScanLiveDispatcher,
    DetMapHeightScanLiveDispatcher,
    LivePColorMesh,
)

FAKE_START_DOC: RunStart = {"uid": "1"}  # type: ignore
FAKE_DESCRIPTOR: EventDescriptor = {"uid": "2", "data_keys": {}}  # type: ignore
FAKE_STOP_DOC: RunStop = {"exit_status": "success"}  # type: ignore


def test_angle_scan_livedispatcher():
    dispatcher = DetMapAngleScanLiveDispatcher(
        x_name="angle",
        x_data=np.linspace(-1, 2, num=4),
        y_in_name="det",
        y_out_name="summed_counts",
    )

    captured_events = []

    def sub(doc_typ, doc):
        if doc_typ == "event":
            captured_events.append(doc)

    dispatcher.subscribe(sub)

    dispatcher.start(FAKE_START_DOC)
    dispatcher.stop(FAKE_STOP_DOC)

    # No events should be emitted if no descriptor emitted
    assert captured_events == []

    dispatcher.start(FAKE_START_DOC)
    dispatcher.descriptor(FAKE_DESCRIPTOR)
    dispatcher.event(
        {
            "data": {
                "det": np.array([1, 2, 3, 4]),
            },
            "descriptor": "2",
        }
    )
    dispatcher.event(
        {
            "data": {
                "det": np.array([0, 0, 100, 100]),
            },
            "descriptor": "2",
        }
    )

    with pytest.raises(ValueError, match=r"Shape of data .* does not match .*"):
        dispatcher.event(
            {
                "data": {
                    "det": np.array([0, 0, 100]),
                },
                "descriptor": "2",
            }
        )

    dispatcher.stop(FAKE_STOP_DOC)

    assert len(captured_events) == 4

    assert captured_events[0]["data"]["angle"] == pytest.approx(-1)
    assert captured_events[0]["data"]["summed_counts"] == pytest.approx(1)

    assert captured_events[1]["data"]["angle"] == pytest.approx(0)
    assert captured_events[1]["data"]["summed_counts"] == pytest.approx(2)

    assert captured_events[2]["data"]["angle"] == pytest.approx(1)
    assert captured_events[2]["data"]["summed_counts"] == pytest.approx(103)

    assert captured_events[3]["data"]["angle"] == pytest.approx(2)
    assert captured_events[3]["data"]["summed_counts"] == pytest.approx(104)


def test_height_scan_livedispatcher():
    dispatcher = DetMapHeightScanLiveDispatcher(
        mon_name="mon",
        det_name="det",
        out_name="normalized_counts",
    )

    captured_events = []

    def sub(doc_typ, doc):
        if doc_typ == "event":
            captured_events.append(doc)

    dispatcher.subscribe(sub)

    dispatcher.start(FAKE_START_DOC)
    dispatcher.descriptor(FAKE_DESCRIPTOR)
    dispatcher.event(
        {
            "data": {
                "mon": np.array([1, 1, 1, 1]),
                "det": np.array([1, 2, 3, 4]),
            },
            "descriptor": "2",
        }
    )
    dispatcher.event(
        {
            "data": {
                "mon": np.array([9, 8, 7, 6]),
                "det": np.array([101, 201, 301, 401]),
            },
            "descriptor": "2",
        }
    )
    dispatcher.stop(FAKE_STOP_DOC)

    assert len(captured_events) == 2
    assert captured_events[0]["data"]["normalized_counts"] == pytest.approx(10 / 4)
    assert captured_events[1]["data"]["normalized_counts"] == pytest.approx(
        (101 + 201 + 301 + 401) / (9 + 8 + 7 + 6)
    )


def test_height_scan_livedispatcher_zero_monitor():
    dispatcher = DetMapHeightScanLiveDispatcher(
        mon_name="mon",
        det_name="det",
        out_name="normalized_counts",
    )

    dispatcher.start(FAKE_START_DOC)
    dispatcher.descriptor(FAKE_DESCRIPTOR)
    with pytest.raises(ValueError, match=r"No monitor counts.*"):
        dispatcher.event(
            {
                "data": {
                    "mon": np.array([0, 0, 0, 0]),
                    "det": np.array([1, 2, 3, 4]),
                },
                "descriptor": "2",
            }
        )


def test_live_pcolormap():
    _, ax = plt.subplots()
    cb = LivePColorMesh(y="y", x="x", x_name="angle", x_coord=np.array([1, 2, 3]), ax=ax)

    cb.start(FAKE_START_DOC)
    cb.descriptor(FAKE_DESCRIPTOR)
    cb.event(
        {
            "data": {
                "y": 1001,
                "x": np.array([11, 12, 13]),
            },
            "descriptor": "2",
        }
    )
    cb.event(
        {
            "data": {
                "y": 1002,
                "x": np.array([33, 44, 55]),
            },
            "descriptor": "2",
        }
    )

    np.testing.assert_equal(cb._data, np.array([[11, 12, 13], [33, 44, 55]]))

    cb.stop(FAKE_STOP_DOC)

# pyright: reportMissingParameterType=false
# pyright: reportArgumentType=false
import numpy as np
import pytest

from ibex_bluesky_core.callbacks.reflectometry.det_map import (
    DetMapAngleScanLiveDispatcher,
    DetMapHeightScanLiveDispatcher,
)


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

    dispatcher.start({"uid": "1"})
    dispatcher.descriptor({"uid": "2", "data_keys": {}})
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
    dispatcher.stop({"exit_status": "success"})

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

    dispatcher.start({"uid": "1"})
    dispatcher.descriptor({"uid": "2", "data_keys": {}})
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
    dispatcher.stop({"exit_status": "success"})

    assert len(captured_events) == 2
    assert captured_events[0]["data"]["normalized_counts"] == pytest.approx(10 / 4)
    assert captured_events[1]["data"]["normalized_counts"] == pytest.approx(
        (101 + 201 + 301 + 401) / (9 + 8 + 7 + 6)
    )

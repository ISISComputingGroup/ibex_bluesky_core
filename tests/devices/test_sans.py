# pyright: reportMissingParameterType=false
from unittest import mock

import bluesky.plan_stubs as bps
import matplotlib.pyplot as plt
import numpy as np
import pytest
from bluesky.preprocessors import subs_wrapper
from lmfit.model import ModelResult
from ophyd_async.core import soft_signal_rw

from ibex_bluesky_core.devices.simpledae import (
    MultiRegionOfInterestReducer,
    PeriodPerPointController,
    SimpleDae,
    Waiter,
)
from ibex_bluesky_core.fitting import Gaussian
from ibex_bluesky_core.plans.sans import rocking_scan
from ibex_bluesky_core.plans.sans._rocking import _region_callbacks
from ibex_bluesky_core.utils import average_model_results

DETECTOR_SPECTRA_ROIS = {"a": [1, 2, 3], "b": [4, 5, 6], "c": [7, 8, 9]}


@pytest.fixture
async def dae():
    noop_controller = mock.MagicMock(spec=PeriodPerPointController)
    noop_waiter = Waiter()
    reducer = MultiRegionOfInterestReducer(detector_spectra_rois=DETECTOR_SPECTRA_ROIS)

    dae = SimpleDae(
        prefix="unittest:",
        name="dae",
        controller=noop_controller,
        waiter=noop_waiter,
        reducer=reducer,
    )
    await dae.connect(mock=True)
    return dae


@pytest.fixture
def rotation():
    return soft_signal_rw(float, name="rotation")


def test_rocking_scan_decorator(RE, dae, rotation):
    fit_method = Gaussian.fit()

    @rocking_scan(dae, x=rotation.name, fit_method=fit_method)
    def _fake_plan():
        yield from bps.null()

    with mock.patch("ibex_bluesky_core.plans.sans._rocking._rocking_scan_wrapper") as mock_wrapper:
        RE(_fake_plan())

    mock_wrapper.assert_called_once_with(
        mock.ANY,
        dae,
        x="rotation",
        fit_method=fit_method,
        average_method=average_model_results,
    )


def _fake_call_qt_aware(func, *args, **kwargs):
    yield from bps.null()

    if func is not plt.subplots:
        return None

    axes = np.empty((kwargs["nrows"], 1), dtype=object)
    for i in range(kwargs["nrows"]):
        axes[i, 0] = mock.MagicMock()
    return mock.MagicMock(), axes


def _run_rocking_scan(RE, dae, rotation, fit_results, average_method, *, expect_error=False):
    fit_method = Gaussian.fit()
    plan_mock = mock.MagicMock()
    callbacks = []

    def _fake_region_callbacks(reducer, roi_name, x, ax, fit_method):
        cb = mock.MagicMock()
        cb.live_fit.result = fit_results[roi_name]
        cb.subs = [cb.live_fit]
        callbacks.append(cb)
        return cb

    @rocking_scan(dae, x=rotation.name, fit_method=fit_method, average_method=average_method)
    def _fake_plan(start, stop, *, num):
        plan_mock(start, stop, num=num)
        yield from bps.null()

    with (
        mock.patch(
            "ibex_bluesky_core.plans.sans._rocking.ensure_connected", return_value=bps.null()
        ) as mock_ensure_connected,
        mock.patch(
            "ibex_bluesky_core.plans.sans._rocking.call_qt_aware", side_effect=_fake_call_qt_aware
        ) as mock_call_qt_aware,
        mock.patch(
            "ibex_bluesky_core.plans.sans._rocking._region_callbacks",
            side_effect=_fake_region_callbacks,
        ) as mock_region_callbacks,
        mock.patch(
            "ibex_bluesky_core.plans.sans._rocking.subs_wrapper", wraps=subs_wrapper
        ) as mock_subs_wrapper,
    ):
        if expect_error:
            with pytest.raises(ValueError, match="At least one ROI fit failed"):
                RE(_fake_plan(-1.0, 1.0, num=21))
            plan_result = None
        else:
            plan_result = RE(_fake_plan(-1.0, 1.0, num=21)).plan_result

    mock_ensure_connected.assert_called_once_with(dae)
    assert mock_call_qt_aware.call_args_list == [
        mock.call(plt.close, "all"),
        mock.call(plt.subplots, nrows=len(DETECTOR_SPECTRA_ROIS), squeeze=False),
    ]

    assert mock_region_callbacks.call_count == len(DETECTOR_SPECTRA_ROIS)
    assert [c.args[1] for c in mock_region_callbacks.call_args_list] == list(DETECTOR_SPECTRA_ROIS)
    for c in mock_region_callbacks.call_args_list:
        assert c.args[0] is dae.reducer
        assert c.args[2] == "rotation"
        assert c.args[4] is fit_method

    mock_subs_wrapper.assert_called_once()
    subscribed = mock_subs_wrapper.call_args.args[1]
    assert subscribed == [cb.live_fit for cb in callbacks]

    plan_mock.assert_called_once_with(-1.0, 1.0, num=21)

    return plan_result


def test_rocking_scan_averages_fits_when_all_fits_succeed(RE, dae, rotation):
    fit_results = {name: mock.MagicMock(spec=ModelResult) for name in DETECTOR_SPECTRA_ROIS}
    avg = mock.MagicMock(spec=ModelResult)
    average_method = mock.MagicMock(return_value=avg)

    plan_result = _run_rocking_scan(RE, dae, rotation, fit_results, average_method)

    average_method.assert_called_once_with(list(fit_results.values()))
    assert plan_result == {"fits": fit_results, "fit_avg": avg}


def test_rocking_scan_raises_when_any_fit_fails(RE, dae, rotation, caplog):
    fit_results: dict[str, mock.MagicMock | None] = {
        name: mock.MagicMock(spec=ModelResult) for name in DETECTOR_SPECTRA_ROIS
    }
    fit_results["b"] = None
    average_method = mock.MagicMock()

    _run_rocking_scan(RE, dae, rotation, fit_results, average_method, expect_error=True)

    average_method.assert_not_called()
    assert "Fit for ROI 'b' is None" in caplog.text
    assert "Fit for ROI 'a' is None" not in caplog.text
    assert "Fit for ROI 'c' is None" not in caplog.text


def test_region_callbacks(dae):

    with mock.patch(
        "ibex_bluesky_core.callbacks.ISISCallbacks.__init__", return_value=None
    ) as mock_callbacks:
        ax = mock.MagicMock()
        fit = Gaussian.fit()
        _region_callbacks(dae.reducer, "a", "rotation", ax, fit)

        mock_callbacks.assert_called_once_with(
            x="rotation",
            y="dae-reducer-a",
            yerr="dae-reducer-a_err",
            fit=fit,
            add_peak_stats=False,
            ax=ax,
            live_fit_logger_postfix="_a",
            human_readable_file_postfix="_a",
            save_plot_to_png=False,
            set_title_to_fit_result=True,
        )

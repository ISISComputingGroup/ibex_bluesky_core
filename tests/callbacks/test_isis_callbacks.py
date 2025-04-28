# pyright: reportMissingParameterType=false
from unittest.mock import patch

import bluesky.plan_stubs as bps
import pytest
from bluesky.callbacks import LiveFitPlot, LiveTable
from bluesky.callbacks.fitting import LiveFit, PeakStats

from ibex_bluesky_core.callbacks import (
    HumanReadableFileCallback,
    ISISCallbacks,
    LiveFitLogger,
    LivePlot,
    PlotPNGSaver,
)
from ibex_bluesky_core.fitting import Linear


def test_peak_stats_without_peak_stats_callback_raises():
    with pytest.raises(
        ValueError,
        match=r"peak stats was not added as a callback.",
    ):
        _ = ISISCallbacks(
            x="X_signal",
            y="Y_signal",
            yerr="Y_error",
            add_peak_stats=False,
            show_fit_on_plot=False,
        ).peak_stats


def test_live_fit_without_live_fit_callback_raises():
    with pytest.raises(
        ValueError,
        match=r"live_fit was not added as a callback.",
    ):
        _ = ISISCallbacks(
            x="X_signal", y="Y_signal", yerr="Y_error", show_fit_on_plot=False
        ).live_fit


def test_add_human_readable_file_with_global_fields_and_specific_both_get_added():
    x = "X_signal"
    y = "Y_signal"

    specific_fields = ["spec_1", "spec_2"]
    global_fields = ["global_1", "global_2"]

    icc = ISISCallbacks(
        x=x,
        y=y,
        add_human_readable_file_cb=True,
        measured_fields=global_fields,
        fields_for_hr_file=specific_fields,
        add_plot_cb=False,
        show_fit_on_plot=False,
        add_peak_stats=False,
    )

    assert isinstance(icc.subs[0], HumanReadableFileCallback)
    assert icc.subs[0].fields == global_fields + specific_fields


def test_add_livetable_with_global_fields_and_specific_both_get_added():
    x = "X_signal"
    y = "Y_signal"

    specific_fields = ["spec_1", "spec_2"]
    global_fields = ["global_1", "global_2"]

    icc = ISISCallbacks(
        x=x,
        y=y,
        add_table_cb=True,
        measured_fields=global_fields,
        fields_for_live_table=specific_fields,
        add_plot_cb=False,
        show_fit_on_plot=False,
        add_peak_stats=False,
        add_human_readable_file_cb=False,
    )

    assert isinstance(icc.subs[0], LiveTable)
    assert icc.subs[0]._fields == global_fields + specific_fields


def test_add_livefit_then_get_livefit_property_returns_livefit():
    x = "X_signal"
    y = "Y_signal"

    fit_method = Linear().fit()

    icc = ISISCallbacks(
        x=x,
        y=y,
        fit=fit_method,
        add_table_cb=False,
        add_plot_cb=True,
        show_fit_on_plot=False,
        add_peak_stats=False,
        add_human_readable_file_cb=False,
    )

    assert icc.live_fit.method == fit_method  # pyright: ignore reportOptionalMemberAccess


def test_add_peakstats_then_get_peakstats_property_returns_peakstats():
    x = "X_signal"
    y = "Y_signal"

    icc = ISISCallbacks(
        x=x,
        y=y,
        add_table_cb=False,
        add_plot_cb=False,
        show_fit_on_plot=False,
        add_peak_stats=True,
        add_human_readable_file_cb=False,
    )

    assert isinstance(icc.peak_stats, PeakStats)


def test_add_livefitplot_without_plot_then_plot_is_set_up_regardless():
    x = "X_signal"
    y = "Y_signal"

    icc = ISISCallbacks(
        x=x,
        y=y,
        fit=Linear().fit(),
        add_table_cb=False,
        add_plot_cb=False,
        show_fit_on_plot=True,
        add_peak_stats=False,
        add_human_readable_file_cb=False,
    )
    assert any([isinstance(i, LivePlot) for i in icc.subs])


def test_do_not_add_live_fit_logger_then_not_added():
    x = "X_signal"
    y = "Y_signal"

    icc = ISISCallbacks(
        x=x,
        y=y,
        fit=Linear().fit(),
        add_table_cb=False,
        add_plot_cb=False,
        show_fit_on_plot=True,
        add_peak_stats=False,
        add_human_readable_file_cb=False,
        add_live_fit_logger=False,
    )
    assert not any([isinstance(i, LiveFitLogger) for i in icc.subs])


def test_do_not_add_png_saver_then_not_added():
    x = "X_signal"
    y = "Y_signal"

    icc = ISISCallbacks(
        x=x,
        y=y,
        fit=Linear().fit(),
        add_table_cb=False,
        add_plot_cb=False,
        show_fit_on_plot=True,
        add_peak_stats=False,
        add_human_readable_file_cb=False,
        add_live_fit_logger=False,
        save_plot_to_png=False,
    )
    assert not any([isinstance(i, PlotPNGSaver) for i in icc.subs])


@pytest.mark.parametrize("matplotlib_using_qt", [True, False])
def test_call_decorator(RE, matplotlib_using_qt):
    with patch(
        "ibex_bluesky_core.callbacks.is_matplotlib_backend_qt", return_value=matplotlib_using_qt
    ):
        x = "X_signal"
        y = "Y_signal"
        icc = ISISCallbacks(
            x=x,
            y=y,
            add_plot_cb=True,
            add_table_cb=False,
            add_peak_stats=False,
            add_human_readable_file_cb=False,
            show_fit_on_plot=True,
            fit=Linear().fit(),
        )

        def f():
            def _outer():
                @icc
                def _inner():
                    assert any(isinstance(sub, LivePlot) for sub in icc.subs)
                    assert any(isinstance(sub, LiveFitPlot) for sub in icc.subs)
                    assert any(isinstance(sub, LiveFit) for sub in icc.subs) == matplotlib_using_qt
                    yield from bps.null()

                yield from _inner()

            return (yield from _outer())

        RE(f())

# pyright: reportMissingParameterType=false
import bluesky.plan_stubs as bps
import pytest
from bluesky.callbacks import LiveFitPlot, LiveTable
from bluesky.callbacks.fitting import PeakStats

from ibex_bluesky_core.callbacks import (
    HumanReadableFileCallback,
    ISISCallbacks,
    LivePlot,
)
from ibex_bluesky_core.callbacks.fitting.fitting_utils import Linear


def test_no_measured_fields_for_human_readable_file_raises():
    with pytest.raises(ValueError, match=r"No fields specified for the human-readable file"):
        ISISCallbacks(
            x="X_signal",
            y="Y_signal",
            add_human_readable_file_cb=True,
            measured_fields=None,
            fields_for_hr_file=None,
            add_table_cb=False,
            add_peak_stats=False,
            add_fit_cb=False,
            add_plot_cb=False,
            show_fit_on_plot=False,
        )


def test_no_measured_fields_for_livetable_raises():
    with pytest.raises(ValueError, match=r"No fields specified for the live table"):
        ISISCallbacks(
            x="X_signal",
            y="Y_signal",
            add_human_readable_file_cb=False,
            measured_fields=None,
            fields_for_live_table=None,
            add_table_cb=True,
            add_peak_stats=False,
            add_fit_cb=False,
            add_plot_cb=False,
            show_fit_on_plot=False,
        )


def test_no_x_or_y_for_plot_or_fit_or_peak_stats_raises():
    with pytest.raises(
        ValueError, match=r"X and/or Y not specified when trying to add a plot, fit or peak stats."
    ):
        ISISCallbacks(
            x=None,
            y=None,
            add_plot_cb=True,
            add_fit_cb=True,
            add_peak_stats=True,
            show_fit_on_plot=False,
        )


def test_show_fit_on_plot_without_fit_callback_raises():
    with pytest.raises(
        ValueError,
        match=r"Fit has been requested to show on plot without a fitting method or callback.",
    ):
        ISISCallbacks(
            x="X_signal", y="Y_signal", yerr="Y_error", show_fit_on_plot=True, add_fit_cb=False
        )


def test_show_fit_on_plot_without_fit_method_raises():
    with pytest.raises(
        ValueError,
        match=r"Fit has been requested to show on plot without a fitting method or callback.",
    ):
        ISISCallbacks(
            x="X_signal",
            y="Y_signal",
            show_fit_on_plot=True,
            fit=None,
        )


def test_add_fit_cb_without_fit_method_raises():
    with pytest.raises(
        ValueError,
        match=r"Fit has been requested to show on plot without a fitting method or callback.",
    ):
        ISISCallbacks(
            x="X_signal",
            y="Y_signal",
            show_fit_on_plot=True,
            fit=None,
        )


# test singularly every cb

# test all of callbacks at once

# test callback decorator


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
        add_fit_cb=False,
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
        add_fit_cb=False,
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
        add_fit_cb=True,
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
        add_fit_cb=False,
        add_human_readable_file_cb=False,
    )

    assert isinstance(icc.peak_stats, PeakStats)


def test_raises_when_fit_requested_with_no_method():
    x = "X_signal"
    y = "Y_signal"
    with pytest.raises(ValueError, match=r"fit method must be specified if add_fit_cb is True"):
        _ = ISISCallbacks(
            x=x,
            y=y,
            add_table_cb=False,
            add_plot_cb=False,
            show_fit_on_plot=False,
            add_peak_stats=False,
            add_fit_cb=True,
            add_human_readable_file_cb=False,
        )


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
        add_fit_cb=True,
        add_human_readable_file_cb=False,
    )
    assert isinstance(icc.subs[0], LiveFitPlot)
    assert isinstance(icc.subs[1], LivePlot)


def test_call_decorator(RE):
    x = "X_signal"
    y = "Y_signal"
    icc = ISISCallbacks(
        x=x,
        y=y,
        add_plot_cb=True,
        add_fit_cb=False,
        add_table_cb=False,
        add_peak_stats=False,
        add_human_readable_file_cb=False,
        show_fit_on_plot=False,
    )

    def f():
        def _outer():
            @icc
            def _inner():
                assert isinstance(icc.subs[0], LivePlot)
                yield from bps.null()

            yield from _inner()

        return (yield from _outer())

    RE(f())

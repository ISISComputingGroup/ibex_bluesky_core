from unittest.mock import MagicMock

import pytest
from bluesky.callbacks import LiveTable

from ibex_bluesky_core.callbacks import (
    HumanReadableFileCallback,
    ISISCallbacks,
)


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

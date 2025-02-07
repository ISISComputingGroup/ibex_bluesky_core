"""Bluesky callbacks which may be attached to the RunEngine."""

import logging
import threading
from os import PathLike
from pathlib import Path
from typing import Callable

from bluesky.callbacks import LiveTable, LiveFitPlot
from bluesky.callbacks.fitting import PeakStats
from bluesky.callbacks.mpl_plotting import QtAwareCallback
from bluesky.utils import make_decorator
import bluesky.preprocessors as bpp
from event_model import RunStart

from ibex_bluesky_core.callbacks.file_logger import HumanReadableFileCallback, DEFAULT_PATH
from ibex_bluesky_core.callbacks.fitting import FitMethod, LiveFit
import matplotlib.pyplot as plt

from ibex_bluesky_core.callbacks.plotting import LivePlot

logger = logging.getLogger(__name__)


class ISISCallbacks:
    def __init__(
        self,
        x: str | None,
        y: str | None,
        yerr: str | None,
        fit: FitMethod | None = None,
        measured_fields: list[str] | None = None,
        fields_for_live_table: list[str] | None = None,
        fields_for_hr_file: list[str] | None = None,
        human_readable_file_output_dir: str | PathLike[str] | None = None,
        add_human_readable_file_cb: bool = True,
        add_plot_cb: bool = True,
        add_fit_cb: bool = True,
        add_table_cb: bool = True,
        add_peak_stats: bool = True,
        show_fit_on_plot: bool = True,
        ax: plt.Axes | None = None,
    ):
        """
        Collection of ISIS standard callbacks for use within plans. By default, this adds:
        HumanReadableFileCallback, LiveTable, PeakStats, LiveFit, LiveFitPlot and LivePlot.
        Results such as fitting outcomes can be accessed from the `live_fit` and `peak_stats` properties.

        Args:
            x: The signal _name_ to use for X within plots and fits.
            y: The signal _name_ to use for Y within plots and fits.
            yerr: The signal _name_ to use for the Y uncertainty within plots and fits.
            fit: The fit method to use when fitting.
            measured_fields: the fields to use for both the live table and human-readable file.
            fields_for_live_table: the fields to measure for the live table (in addition to `measured_fields`).
            fields_for_hr_file: the fields to measure for the human-readable file (in addition to `measured_fields`).
            human_readable_file_output_dir: the output directory for human-readable files. can be blank and will default.
            add_human_readable_file_cb: whether to add a human-readable file callback.
            add_plot_cb: whether to add a plot callback.
            add_fit_cb: whether to add a fitting callback (which will be displayed on a plot)
            add_table_cb: whether to add a table callback.
            add_peak_stats: whether to add a peak stats callback.
            ax: An optional axes object to use for plotting.
        """
        if measured_fields is None:
            measured_fields = []
        if fields_for_live_table is None:
            fields_for_live_table = []
        if fields_for_hr_file is None:
            fields_for_hr_file = []

        if show_fit_on_plot and (not add_fit_cb or fit is None):
            raise ValueError(
                "Fit has been requested to show on plot without a fitting method or callback."
            )
        if (add_peak_stats or add_fit_cb or add_plot_cb) and (not x or not y):
            raise ValueError(
                "X and/or Y not specified when trying to add a plot, fit or peak stats."
            )

        self.subs = []
        if add_human_readable_file_cb:
            _combined_hr_fields = measured_fields + fields_for_hr_file
            if not _combined_hr_fields: raise ValueError("No fields specified for the human-readable file")
            self.subs.append(
                HumanReadableFileCallback(
                    fields=_combined_hr_fields,
                    output_dir=Path(human_readable_file_output_dir)
                    if human_readable_file_output_dir
                    else DEFAULT_PATH,
                ),
            )

        if add_table_cb:
            _combined_lt_fields = measured_fields + fields_for_live_table
            if not _combined_lt_fields: raise ValueError("No fields specified for the live table")
            self.subs.append(
                LiveTable(_combined_lt_fields),
            )

        if add_peak_stats:
            self._peak_stats = PeakStats(x=x, y=y)
            self.subs.append(self._peak_stats)

        if (add_plot_cb or show_fit_on_plot) and not ax:
            logger.debug("No axis provided, creating a new one")
            fig, ax, exc, result = None, None, None, None
            done_event = threading.Event()
            class _Cb(QtAwareCallback):
                def start(self, doc: RunStart) -> None:
                    nonlocal result, exc, fig, ax
                    try:
                        plt.close("all")
                        fig, ax = plt.subplots()
                    finally:
                        done_event.set()

            cb = _Cb()
            cb("start", {"time": 0, "uid": ""})
            done_event.wait(10.0)

        if add_fit_cb:
            if fit is None:
                raise ValueError("fit method must be specified if add_fit_cb is True")
            self._live_fit = LiveFit(fit, y=y, x=x, yerr=yerr)
            if show_fit_on_plot:
                self.subs.append(LiveFitPlot(livefit=self._live_fit, ax=ax))

        if add_plot_cb or show_fit_on_plot:
            self.subs.append(
                LivePlot(
                    y=y,
                    x=x,
                    marker="x",
                    linestyle="none",
                    ax=ax,
                    yerr=yerr,
                )
            )

    def _icbc_wrapper(self, plan):
        @bpp.subs_decorator(self.subs)
        def _inner():
            return (yield from plan)

        return (yield from _inner())

    @property
    def live_fit(self) -> LiveFit | None:
        """The live fit object containing fitting results."""
        return self._live_fit

    @property
    def peak_stats(self) -> PeakStats | None:
        """The peak stats object containing statistics ie. centre of mass."""
        return self._peak_stats

    def __call__(self, f: Callable) -> Callable:
        return make_decorator(self._icbc_wrapper)()(f)

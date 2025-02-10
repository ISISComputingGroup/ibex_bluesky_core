"""Bluesky callbacks which may be attached to the RunEngine."""

import logging
import threading
from collections.abc import Generator
from os import PathLike
from pathlib import Path
from typing import Any, Callable

import bluesky.preprocessors as bpp
import matplotlib.pyplot as plt
from bluesky.callbacks import LiveFitPlot, LiveTable
from bluesky.callbacks.fitting import PeakStats
from bluesky.callbacks.mpl_plotting import QtAwareCallback
from bluesky.utils import Msg, make_decorator
from event_model import RunStart
from matplotlib.axes import Axes

from ibex_bluesky_core.callbacks.file_logger import DEFAULT_PATH, HumanReadableFileCallback
from ibex_bluesky_core.callbacks.fitting import FitMethod, LiveFit
from ibex_bluesky_core.callbacks.plotting import LivePlot

logger = logging.getLogger(__name__)

# ruff: noqa: PLR0913, PLR0912, PLR0917


class ISISCallbacks:
    """ISIS standard callbacks for use within plans."""

    def __init__(
        self,
        x: str | None = None,
        y: str | None = None,
        yerr: str | None = None,
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
        ax: Axes | None = None,
    ) -> None:
        """A collection of ISIS standard callbacks for use within plans.

        By default, this adds:

        - HumanReadableFileCallback

        - LiveTable

        - PeakStats

        - LiveFit

        - LiveFitPlot

        - LivePlot

        Results can be accessed from the `live_fit` and `peak_stats` properties.

        This is to be used as a member and then as a decorator if results are needed ie::

            def dae_scan_plan():
                ...
                icc = ISISCallbacks(
                    x=block.name,
                    y=reducer.intensity.name,
                    yerr=reducer.intensity_stddev.name,
                    fit=Linear.fit(),
                    ...
                )
                ...

                @icc
                def _inner():
                    yield from ...
                    ...
                    print(icc.live_fit.result.fit_report())
                    print(f"COM: {icc.peak_stats['com']}")

        Args:
            x: The signal name to use for X within plots and fits.
            y: The signal name to use for Y within plots and fits.
            yerr: The signal name to use for the Y uncertainty within plots and fits.
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
            show_fit_on_plot: whether to show fit on plot.
            ax: An optional axes object to use for plotting.

        """  # noqa
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
        if (add_peak_stats or add_fit_cb or add_plot_cb) and (x is None or y is None):
            raise ValueError(
                "X and/or Y not specified when trying to add a plot, fit or peak stats."
            )

        self.subs = []
        if add_human_readable_file_cb:
            combined_hr_fields = measured_fields + fields_for_hr_file
            if not combined_hr_fields:
                raise ValueError("No fields specified for the human-readable file")
            self.subs.append(
                HumanReadableFileCallback(
                    fields=combined_hr_fields,
                    output_dir=Path(human_readable_file_output_dir)
                    if human_readable_file_output_dir
                    else DEFAULT_PATH,
                ),
            )

        if add_table_cb:
            combined_lt_fields = measured_fields + fields_for_live_table
            if not combined_lt_fields:
                raise ValueError("No fields specified for the live table")
            self.subs.append(
                LiveTable(combined_lt_fields),
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
            self._live_fit = LiveFit(fit, y=y, x=x, yerr=yerr)  # pyright: ignore reportArgumentType
            if show_fit_on_plot:
                self.subs.append(LiveFitPlot(livefit=self._live_fit, ax=ax))

        if add_plot_cb or show_fit_on_plot:
            self.subs.append(
                LivePlot(
                    y=y,  # pyright: ignore reportArgumentType
                    x=x,
                    marker="x",
                    linestyle="none",
                    ax=ax,
                    yerr=yerr,
                )
            )

    @property
    def live_fit(self) -> LiveFit | None:
        """The live fit object containing fitting results."""
        return self._live_fit

    @property
    def peak_stats(self) -> PeakStats | None:
        """The peak stats object containing statistics ie. centre of mass."""
        return self._peak_stats

    def _icbc_wrapper(self, plan: Generator[Msg, None, None]) -> Generator[Msg, None, None]:
        @bpp.subs_decorator(self.subs)
        def _inner() -> Generator[Msg, None, None]:
            return (yield from plan)

        return (yield from _inner())

    def __call__(self, f: Callable[..., Any]) -> Callable[..., Any]:
        """Make a decorator to wrap the plan and subscribe to all callbacks."""
        return make_decorator(self._icbc_wrapper)()(f)

"""Bluesky callbacks which may be attached to the RunEngine."""

import logging
import threading
from collections.abc import Callable, Generator
from os import PathLike
from pathlib import Path
from typing import Any

import bluesky.preprocessors as bpp
import matplotlib.pyplot as plt
from bluesky.callbacks import CallbackBase, LiveFitPlot, LiveTable
from bluesky.callbacks.fitting import PeakStats
from bluesky.callbacks.mpl_plotting import QtAwareCallback
from bluesky.utils import Msg, make_decorator
from event_model import RunStart
from matplotlib.axes import Axes

from ibex_bluesky_core.callbacks._utils import get_default_output_path
from ibex_bluesky_core.callbacks.file_logger import (
    HumanReadableFileCallback,
)
from ibex_bluesky_core.callbacks.fitting import FitMethod, LiveFit
from ibex_bluesky_core.callbacks.fitting.livefit_logger import (
    LiveFitLogger,
)
from ibex_bluesky_core.callbacks.plotting import LivePlot

logger = logging.getLogger(__name__)

# ruff: noqa: PLR0913, PLR0912, PLR0917


class ISISCallbacks:
    """ISIS standard callbacks for use within plans."""

    def __init__(
        self,
        *,
        x: str,
        y: str,
        yerr: str | None = None,
        measured_fields: list[str] | None = None,
        add_table_cb: bool = True,
        fields_for_live_table: list[str] | None = None,
        add_human_readable_file_cb: bool = True,
        fields_for_hr_file: list[str] | None = None,
        human_readable_file_output_dir: str | PathLike[str] | None = None,
        add_plot_cb: bool = True,
        ax: Axes | None = None,
        fit: FitMethod | None = None,
        show_fit_on_plot: bool = True,
        add_peak_stats: bool = True,
        add_live_fit_logger: bool = True,
        live_fit_logger_output_dir: str | PathLike[str] | None = None,
        live_fit_logger_postfix: str = "",
        human_readable_file_postfix: str = "",
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
            measured_fields: the fields to use for both the live table and human-readable file.
            add_table_cb: whether to add a table callback.
            fields_for_live_table: the fields to measure for the live table (in addition to `measured_fields`).
            add_human_readable_file_cb: whether to add a human-readable file callback.
            fields_for_hr_file: the fields to measure for the human-readable file (in addition to `measured_fields`).
            human_readable_file_output_dir: the output directory for human-readable files. can be blank and will default.
            add_plot_cb: whether to add a plot callback.
            ax: An optional axes object to use for plotting.
            fit: The fit method to use when fitting.
            show_fit_on_plot: whether to show fit on plot.
            add_peak_stats: whether to add a peak stats callback.
            add_live_fit_logger: whether to add a live fit logger.
            live_fit_logger_output_dir: the output directory for live fit logger.
            live_fit_logger_postfix: the postfix to add to live fit logger.
            human_readable_file_postfix: optional postfix to add to human-readable file logger.
        """  # noqa
        self._subs = []
        self._peak_stats = None
        self._live_fit = None
        if measured_fields is None:
            measured_fields = []
        if fields_for_live_table is None:
            fields_for_live_table = []
        if fields_for_hr_file is None:
            fields_for_hr_file = []

        measured_fields.append(x)
        measured_fields.append(y)
        if yerr is not None:
            measured_fields.append(yerr)

        if add_human_readable_file_cb:
            combined_hr_fields = measured_fields + fields_for_hr_file
            self._subs.append(
                HumanReadableFileCallback(
                    fields=combined_hr_fields,
                    output_dir=Path(human_readable_file_output_dir)
                    if human_readable_file_output_dir
                    else get_default_output_path(),
                    postfix=human_readable_file_postfix,
                ),
            )

        if add_table_cb:
            combined_lt_fields = measured_fields + fields_for_live_table
            self._subs.append(
                LiveTable(combined_lt_fields),
            )

        if add_peak_stats:
            self._peak_stats = PeakStats(x=x, y=y)
            self._subs.append(self._peak_stats)

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

        if fit is not None:
            self._live_fit = LiveFit(fit, y=y, x=x, yerr=yerr)

            # Ideally this would append either livefitplot or livefit, not both, but there's a
            # race condition if using the Qt backend where a fit result can be returned before
            # the QtAwareCallback has had a chance to process it.
            self._subs.append(self._live_fit)
            if show_fit_on_plot:
                self._subs.append(LiveFitPlot(livefit=self._live_fit, ax=ax))

            if add_live_fit_logger:
                self._subs.append(
                    LiveFitLogger(
                        livefit=self._live_fit,
                        x=x,
                        y=y,
                        yerr=yerr,
                        output_dir=live_fit_logger_output_dir,
                        postfix=live_fit_logger_postfix,
                    )
                )

        if add_plot_cb or show_fit_on_plot:
            self._subs.append(
                LivePlot(
                    y=y,
                    x=x,
                    marker="x",
                    linestyle="none",
                    ax=ax,
                    yerr=yerr,
                )
            )

    @property
    def live_fit(self) -> LiveFit:
        """The live fit object containing fitting results."""
        if self._live_fit is None:
            raise ValueError("live_fit was not added as a callback.")
        return self._live_fit

    @property
    def peak_stats(self) -> PeakStats:
        """The peak stats object containing statistics ie. centre of mass."""
        if self._peak_stats is None:
            raise ValueError("peak stats was not added as a callback.")
        return self._peak_stats

    @property
    def subs(self) -> list[CallbackBase]:
        """The list of subscribed callbacks."""
        return self._subs

    def _icbc_wrapper(self, plan: Generator[Msg, None, None]) -> Generator[Msg, None, None]:
        @bpp.subs_decorator(self.subs)
        def _inner() -> Generator[Msg, None, None]:
            return (yield from plan)

        return (yield from _inner())

    def __call__(self, f: Callable[..., Any]) -> Callable[..., Any]:
        """Make a decorator to wrap the plan and subscribe to all callbacks."""
        return make_decorator(self._icbc_wrapper)()(f)

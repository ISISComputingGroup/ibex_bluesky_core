"""Bluesky callbacks which may be attached to the RunEngine."""
import threading
from os import PathLike
from pathlib import Path
from typing import Callable

from bluesky.callbacks import LiveTable, LiveFitPlot
from bluesky.callbacks.mpl_plotting import QtAwareCallback
from bluesky.utils import make_decorator
import bluesky.preprocessors as bpp
from event_model import RunStart

from ibex_bluesky_core.callbacks.file_logger import HumanReadableFileCallback, DEFAULT_PATH
from ibex_bluesky_core.callbacks.fitting import FitMethod, LiveFit
import matplotlib.pyplot as plt

from ibex_bluesky_core.callbacks.plotting import LivePlot


class ISISCallbacks:
    def __init__(
        self,
        x: str,
        y: str,
        yerr: str | None,
        fit: FitMethod,
        measured_fields: list[str] | None = None,
        human_readable_file_output_dir: str | PathLike[str] | None = None,
        add_human_readable_file_cb: bool = True,
        add_plot_cb: bool = True,
        add_fit_cb: bool = True,
        add_table_cb: bool = True,

    ):
        self.y = y
        self.x = x
        self.yerr = yerr
        self.measured_fields = measured_fields
        self.human_readable_file_output_dir = human_readable_file_output_dir
        self.add_human_readable_file_cb = add_human_readable_file_cb
        self.add_plot_cb = add_plot_cb
        self.add_fit_cb = add_fit_cb
        self.add_table_cb = add_table_cb
        self.fit = fit

        self.subs = []
        if self.add_human_readable_file_cb and self.measured_fields:
            self.subs.append(
                HumanReadableFileCallback(
                    fields=self.measured_fields,
                    output_dir=Path(self.human_readable_file_output_dir)
                    if self.human_readable_file_output_dir
                    else DEFAULT_PATH,
                ),
            )
        if self.add_table_cb and self.measured_fields:
            self.subs.append(
                LiveTable(self.measured_fields),
            )

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

        # TODO be a bit more cleverer here and auto-add a plot if fit toggled to true etc.
        self.lf = LiveFit(self.fit, y=self.y, x=self.x, yerr=self.yerr)
        if self.add_fit_cb:
            self.subs.append(LiveFitPlot(livefit=self.lf, ax=ax))
        if self.add_plot_cb:
            self.subs.append(
                LivePlot(
                    y=self.y,
                    x=self.x,
                    marker="x",
                    linestyle="none",
                    ax=ax,
                    yerr=self.yerr,
                )
            )


    def _icbc_wrapper(self, plan):
        @bpp.subs_decorator(self.subs)
        def _inner():
            return (yield from plan)
        return (yield from _inner())

    def __call__(self, f: Callable) -> Callable:
        return make_decorator(self._icbc_wrapper)()(f)


__all__ = [
    "ISISCallbacks",
    "LivePlot",
    "LiveFit",
    "LiveFitPlot",
    "HumanReadableFileCallback",
    "LiveTable",
]

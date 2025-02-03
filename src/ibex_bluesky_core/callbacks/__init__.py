"""Bluesky callbacks which may be attached to the RunEngine."""

from functools import wraps
from os import PathLike
from pathlib import Path

from bluesky.callbacks import LiveTable, LiveFitPlot
from bluesky.preprocessors import subs_wrapper

from ibex_bluesky_core.callbacks.file_logger import HumanReadableFileCallback
from ibex_bluesky_core.callbacks.fitting import FitMethod, LiveFit
import matplotlib.pyplot as plt

from ibex_bluesky_core.callbacks.plotting import LivePlot

def isis_standard_callbacks(
    x: str,
    y: str,
    yerr: str | None,
    fit: "FitMethod",
    add_human_readable_file_cb: bool = True,
    add_plot_cb: bool = True,
    add_fit_cb: bool = True,
    add_table_cb: bool = True,
    measured_fields: list[str] | None = None,
    human_readable_file_output_dir: str | PathLike[str] | None = None,
):
    def _outer(func):

        @wraps(func)
        def with_callbacks(*args, **kwargs):
            subs = []
            if add_human_readable_file_cb and measured_fields:
                subs.append(
                    HumanReadableFileCallback(
                        fields=measured_fields,
                        output_dir=Path(human_readable_file_output_dir)
                        if human_readable_file_output_dir
                        else Path("C:\\") / "instrument" / "var" / "logs" / "bluesky" / "output_files",
                    ),
                )
            if add_table_cb and measured_fields:
                subs.append(
                    LiveTable(measured_fields),
                )
            _, ax = plt.subplots()
            lf = LiveFit(fit, y=y, x=x, yerr=yerr)
            if add_fit_cb:
                subs.append(LiveFitPlot(livefit=lf, ax=ax))
            if add_plot_cb:
                subs.append(
                    LivePlot(
                        y=y,
                        x=x,
                        marker="x",
                        linestyle="none",
                        ax=ax,
                        yerr=yerr,
                    )
                )
            return subs_wrapper(func, subs)
        return with_callbacks
    return _outer


__all__ = [
    "isis_standard_callbacks",
    LivePlot,
    LiveFit,
    LiveFitPlot,
    HumanReadableFileCallback,
    LiveTable,
]

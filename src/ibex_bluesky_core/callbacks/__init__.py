"""Bluesky callbacks which may be attached to the RunEngine."""

from functools import wraps
from os import PathLike
from pathlib import Path

from bluesky.callbacks import LiveTable, LiveFitPlot
from bluesky.preprocessors import subs_wrapper
from bluesky.utils import make_decorator

from ibex_bluesky_core.callbacks.file_logger import HumanReadableFileCallback
from ibex_bluesky_core.callbacks.fitting import FitMethod, LiveFit
import matplotlib.pyplot as plt

from ibex_bluesky_core.callbacks.plotting import LivePlot


def _isis_standard_callbacks(plan,
    x: str,
    y: str,
    yerr: str | None,
    fit: FitMethod,
    add_human_readable_file_cb: bool = True,
    add_plot_cb: bool = True,
    add_fit_cb: bool = True,
    add_table_cb: bool = True,
    measured_fields: list[str] | None = None,
    human_readable_file_output_dir: str | PathLike[str] | None = None,
):
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
    return (yield from subs_wrapper(plan, subs))


isis_standard_callbacks = make_decorator(_isis_standard_callbacks)


__all__ = [
    isis_standard_callbacks,
    LivePlot,
    LiveFit,
    LiveFitPlot,
    HumanReadableFileCallback,
    LiveTable,
]

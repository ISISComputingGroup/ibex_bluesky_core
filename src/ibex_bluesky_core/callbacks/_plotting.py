"""IBEX plotting callbacks."""

import logging
import os
from pathlib import Path
from typing import Any

import matplotlib
import matplotlib.pyplot as plt
from bluesky.callbacks import LivePlot as _DefaultLivePlot
from bluesky.callbacks.core import get_obj_fields, make_class_safe
from bluesky.callbacks.mpl_plotting import QtAwareCallback
from event_model import RunStop
from event_model.documents import Event, RunStart
from matplotlib.axes import Axes

from ibex_bluesky_core.callbacks._utils import (
    _get_rb_num,
    format_time,
    get_default_output_path,
    get_instrument,
)

logger = logging.getLogger(__name__)

__all__ = ["LivePlot", "PlotPNGSaver", "show_plot"]


def show_plot() -> None:
    """Call plt.show().

    Play nicely with the "normal" backends too
    - only force show if we're actually using our custom backend.
    """
    if "genie_python" in matplotlib.get_backend():
        logger.debug("Explicitly show()ing plot for IBEX")
        plt.show()


@make_class_safe(logger=logger)  # pyright: ignore (pyright doesn't understand this decorator)
class LivePlot(_DefaultLivePlot):
    """Live plot, customized for IBEX."""

    def __init__(
        self,
        y: str,
        x: str | None = None,
        yerr: str | None = None,
        *args: Any,  # noqa: ANN401
        update_on_every_event: bool = True,
        **kwargs: Any,  # noqa: ANN401
    ) -> None:
        """Initialise LivePlot.

        Args:
            y (str): The name of the dependant variable.
            x (str or None, optional): The name of the independant variable.
            yerr (str or None, optional): Name of uncertainties signal.
                Providing None means do not plot uncertainties.
            *args: As per mpl_plotting.py
            update_on_every_event (bool, optional): Whether to update plot every event,
                or just at the end.
            **kwargs: As per mpl_plotting.py

        """
        self.update_on_every_event = update_on_every_event
        super().__init__(y=y, x=x, *args, **kwargs)  # noqa: B026
        if yerr is not None:
            self.yerr, *_others = get_obj_fields([yerr])
        else:
            self.yerr = None
        self.yerr_data = []

        self._mpl_errorbar_container = None

    def event(self, doc: Event) -> None:
        """Process an event document (delegate to superclass, then show the plot)."""
        new_yerr = None if self.yerr is None else doc["data"][self.yerr]
        self.update_yerr(new_yerr)
        super().event(doc)
        if self.update_on_every_event:
            show_plot()

    def update_plot(self, force: bool = False) -> None:
        """Create error bars if needed, then update plot."""
        if self.update_on_every_event or force:
            if self.yerr is not None:
                if self._mpl_errorbar_container is not None:
                    # Remove old error bars before drawing new ones
                    self._mpl_errorbar_container.remove()
                self._mpl_errorbar_container = self.ax.errorbar(  # type: ignore
                    x=self.x_data, y=self.y_data, yerr=self.yerr_data, fmt="none"
                )

            super().update_plot()

    def update_yerr(self, yerr: float | None) -> None:
        """Update uncertainties data."""
        self.yerr_data.append(yerr)

    def start(self, doc: RunStart) -> None:
        """Process an start document (delegate to superclass, then show the plot)."""
        super().start(doc)
        show_plot()

    def stop(self, doc: RunStop) -> None:
        """Process an start document (delegate to superclass, then show the plot)."""
        super().stop(doc)
        if not self.update_on_every_event:
            self.update_plot(force=True)
            show_plot()


class PlotPNGSaver(QtAwareCallback):
    """Save plots to PNG files on a run end."""

    def __init__(
        self,
        x: str,
        y: str,
        ax: Axes,
        postfix: str,
        output_dir: str | os.PathLike[str] | None,
    ) -> None:
        """Initialise the PlotPNGSaver callback.

        Args:
            x: The name of the signal for x.
            y: The name of the signal for y.
            ax: The subplot to save to a file.
            postfix: The file postfix.
            output_dir: The output directory for PNGs.

        """
        super().__init__()
        self.x = x
        self.y = y
        self.ax = ax
        self.postfix = postfix
        self.output_dir = Path(output_dir or get_default_output_path())
        self.filename = None

    def start(self, doc: RunStart) -> None:
        self.filename = (
            self.output_dir
            / f"{_get_rb_num(doc)}"
            / f"{get_instrument()}_{self.x}_{self.y}_{format_time(doc)}Z{self.postfix}.png"
        )

    def stop(self, doc: RunStop) -> None:
        """Write the current plot to a PNG file.

        Args:
            doc: The stop document.

        """
        if self.filename is None:
            raise ValueError("No filename specified for plot PNG")

        self.filename.parent.mkdir(parents=True, exist_ok=True)
        self.ax.figure.savefig(self.filename, format="png")  # pyright: ignore [reportAttributeAccessIssue]

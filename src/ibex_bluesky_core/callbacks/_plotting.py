"""IBEX plotting callbacks."""

import logging
import os
import threading
from pathlib import Path
from typing import Any

import matplotlib
import matplotlib.pyplot as plt
import numpy as np
import numpy.typing as npt
from bluesky.callbacks import LivePlot as _DefaultLivePlot
from bluesky.callbacks.core import get_obj_fields, make_class_safe
from bluesky.callbacks.mpl_plotting import QtAwareCallback
from event_model.documents import Event, RunStart, RunStop
from matplotlib.axes import Axes

from ibex_bluesky_core.callbacks._utils import (
    _get_rb_num,
    format_time,
    get_default_output_path,
    get_instrument,
)

logger = logging.getLogger(__name__)

__all__ = ["LivePColorMesh", "LivePlot", "PlotPNGSaver", "show_plot"]


def show_plot() -> None:
    """Call :py:obj:`matplotlib.pyplot.show` if IBEX matplotlib backend is in use.

    If a different matplotlib backend is in use, do nothing.
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
        """:py:obj:`bluesky.callbacks.mpl_plotting.LivePlot` with support for uncertainties.

        This callback is an extension of :py:obj:`bluesky.callbacks.mpl_plotting.LivePlot`
        with the following additional features:

        - Support for rendering uncertainties as error-bars on the plot.
        - Support for automatically calling :py:obj:`matplotlib.pyplot.show` when needed,
          if using the IBEX matplotlib backend.

        Args:
            y (str): The name of the dependent variable.
            x (str or None, optional): The name of the independent variable.
            yerr (str or None, optional): Name of uncertainty signal.
                Providing None means do not plot uncertainties.
            *args: As per :py:obj:`bluesky.callbacks.mpl_plotting.LivePlot`
            update_on_every_event (bool, optional): Whether to update plot every event,
                or just at the end.
            **kwargs: As per :py:obj:`bluesky.callbacks.mpl_plotting.LivePlot`

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
        """Process an event document (delegate to superclass, then show the plot).

        :meta private:
        """
        new_yerr = None if self.yerr is None else doc["data"][self.yerr]
        self.update_yerr(new_yerr)
        super().event(doc)
        if self.update_on_every_event:
            show_plot()

    def update_plot(self, force: bool = False) -> None:
        """Create error bars if needed, then update plot.

        :meta private:
        """
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
        """Update uncertainties data.

        :meta private:
        """
        self.yerr_data.append(yerr)

    def start(self, doc: RunStart) -> None:
        """Process a start document (delegate to superclass, then show the plot).

        :meta private:
        """
        super().start(doc)
        show_plot()

    def stop(self, doc: RunStop) -> None:
        """Process a stop document (delegate to superclass, then show the plot).

        :meta private:
        """
        super().stop(doc)
        if not self.update_on_every_event:
            self.update_plot(force=True)
            show_plot()


class LivePColorMesh(QtAwareCallback):
    """Live :py:obj:`PColorMesh<matplotlib.pyplot.pcolormesh>`-based heatmap."""

    def __init__(
        self,
        *,
        y: str,
        x: str,
        x_coord: npt.NDArray[np.float64],
        ax: Axes,
        x_name: str | None = None,
        **kwargs: Any,  # noqa: ANN401
    ) -> None:
        """Live :py:obj:`PColorMesh<matplotlib.pyplot.pcolormesh>`-based heatmap.

        This callback displays one row of data in the heatmap per scan point. The ``x``
        signal is therefore expected to contain array data, which should be of the same
        length for every measurement.

        Args:
            y: the name of the signal appearing along the y-axis.
            x: the name of the signal appearing along the x-axis. This signal is
                expected to be an array, representing rows of the heatmap.
            x_coord: coordinates along the x-axis. This is expected to have the same length
                as each row of the heatmap.
            ax: a set of :py:obj:`~matplotlib.axes.Axes` on which to plot.
            x_name: A display name for the x-axis. Defaults to the same as :code:`x`
                if not provided.
            **kwargs: Arbitrary keyword arguments are passed through to
                :py:obj:`matplotlib.pyplot.pcolormesh`

        """
        super().__init__(use_teleporter=kwargs.pop("use_teleporter", None))
        self.__setup_lock = threading.Lock()
        self.__setup_event = threading.Event()
        self._data: npt.NDArray[np.float64] | None = None
        self._x: str = x
        self._y: str = y
        self._y_coords: list[float] = []
        self._x_name: str = x if x_name is None else x_name
        self._x_coords: npt.NDArray[np.float64] = x_coord

        self.ax: Axes = ax
        self.kwargs = kwargs

    def start(self, doc: RunStart) -> RunStart | None:
        """Start a new plot (clear any old data).

        :meta private:
        """
        # The doc is not used; we just use the signal that a new run began.
        self._data = None
        self._y_coords = []

        return super().start(doc)

    def event(self, doc: Event) -> Event:
        """Unpack data from the event and call :code:`self.update()`.

        :meta private:
        """
        new_x = doc["data"][self._x]
        new_y = doc["data"][self._y]

        if self._data is None:
            self._data = np.asarray(new_x).reshape((1, len(new_x)))
        else:
            self._data = np.vstack((self._data, np.asarray(new_x)))

        self._y_coords.append(new_y)

        self.update_plot()
        return super().event(doc)

    def update_plot(self) -> None:
        """Redraw the heatmap.

        :meta private:
        """
        assert self._data is not None
        assert self.ax is not None

        self.ax.clear()
        self.ax.set_xlabel(self._x_name)
        self.ax.set_ylabel(self._y)
        self.ax.pcolormesh(
            self._x_coords,
            self._y_coords,
            self._data,
            vmin=float(np.min(self._data)),
            vmax=float(np.max(self._data)),
            **self.kwargs,
        )
        self.ax.figure.canvas.draw_idle()  # type: ignore
        show_plot()


class PlotPNGSaver(QtAwareCallback):
    """Save plots to PNG files on a run end."""

    def __init__(
        self,
        x: str,
        y: str,
        ax: Axes,
        postfix: str,
        output_dir: str | os.PathLike[str] | None = None,
    ) -> None:
        """Save plots to PNG files on a run end.

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

        :meta private:

        """
        if self.filename is None:
            raise ValueError("No filename specified for plot PNG")

        self.filename.parent.mkdir(parents=True, exist_ok=True)
        self.ax.figure.savefig(self.filename, format="png")  # pyright: ignore [reportAttributeAccessIssue]

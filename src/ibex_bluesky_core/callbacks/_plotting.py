"""IBEX plotting callbacks."""

import logging
import threading
from typing import Any

import matplotlib
import matplotlib.pyplot as plt
import numpy as np
import numpy.typing as npt
from bluesky.callbacks import LivePlot as _DefaultLivePlot
from bluesky.callbacks.core import get_obj_fields, make_class_safe
from bluesky.callbacks.mpl_plotting import QtAwareCallback
from event_model import Event, RunStart, RunStop
from matplotlib.axes import Axes

logger = logging.getLogger(__name__)

__all__ = ["LivePColorMesh", "LivePlot", "show_plot"]


def show_plot() -> None:
    """Call :code:`plt.show()`.

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
        """Process a start document (delegate to superclass, then show the plot)."""
        super().start(doc)
        show_plot()

    def stop(self, doc: RunStop) -> None:
        """Process a stop document (delegate to superclass, then show the plot)."""
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
        """Create a new heatmap.

        Args:
            y: the name of the signal appearing along the y-axis.
            x: the name of the signal appearing along the x-axis. This signal is
                expected to be an array, representing rows of the heatmap.
            x_coord: coordinates along the x-axis. This is expected to have the same length
                as each row of the heatmap.
            ax: a set of matplotlib axes on which to plot.
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
        """Start a new plot (clear any old data)."""
        # The doc is not used; we just use the signal that a new run began.
        self._data = None
        self._y_coords = []

        return super().start(doc)

    def event(self, doc: Event) -> Event:
        """Unpack data from the event and call :code:`self.update()`."""
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
        """Redraw the heatmap."""
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

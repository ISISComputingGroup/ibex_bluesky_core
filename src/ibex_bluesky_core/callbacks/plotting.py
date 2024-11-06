"""IBEX plotting callbacks."""

import logging

import matplotlib
import matplotlib.pyplot as plt
from bluesky.callbacks import LivePlot as _DefaultLivePlot
from bluesky.callbacks.core import make_class_safe, get_obj_fields
from event_model.documents import Event, RunStart

logger = logging.getLogger(__name__)


@make_class_safe(logger=logger)  # pyright: ignore (pyright doesn't understand this decorator)
class LivePlot(_DefaultLivePlot):
    """Live plot, customized for IBEX."""

    def __init__(self, y, x=None, yerr=None, *args, **kwargs):
        super().__init__(y=y, x=x, *args, **kwargs)
        if yerr is not None:
            self.yerr, *others = get_obj_fields([yerr])
        else:
            self.yerr = None
        self.yerr_data = []

    def _show_plot(self) -> None:
        # Play nicely with the "normal" backends too - only force show if we're
        # actually using our custom backend.
        if "genie_python" in matplotlib.get_backend():
            plt.show()

    def event(self, doc: Event):
        """Process an event document (delegate to superclass, then show the plot)."""
        new_yerr = None if self.yerr is None else doc["data"][self.yerr]
        self.update_yerr(new_yerr)
        super().event(doc)
        self._show_plot()

    def update_plot(self):
        if self.yerr is not None:
            self.ax.errorbar(x=self.x_data, y=self.y_data, yerr=self.yerr_data, fmt="none")
        super().update_plot()

    def update_yerr(self, y_err):
        # super.update_caches(x, y)
        self.yerr_data.append(y_err)

    def start(self, doc: RunStart) -> None:
        """Process an start document (delegate to superclass, then show the plot)."""
        super().start(doc)
        self._show_plot()

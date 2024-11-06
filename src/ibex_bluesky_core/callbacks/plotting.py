"""IBEX plotting callbacks."""

import logging

import matplotlib
import matplotlib.pyplot as plt
from bluesky.callbacks import LivePlot as _DefaultLivePlot
from bluesky.callbacks.core import make_class_safe
from event_model.documents import Event, RunStart

logger = logging.getLogger(__name__)


@make_class_safe(logger=logger)  # pyright: ignore (pyright doesn't understand this decorator)
class LivePlot(_DefaultLivePlot):
    """Live plot, customized for IBEX."""

    def __init__(self, y, x=None, yerr=None, *args, **kwargs):
        super().__init__(y=y, x=x, yerr=yerr, *args, **kwargs)

    def _show_plot(self) -> None:
        # Play nicely with the "normal" backends too - only force show if we're
        # actually using our custom backend.
        if "genie_python" in matplotlib.get_backend():
            plt.show()

    def start(self, doc: RunStart) -> None:
        """Process an start document (delegate to superclass, then show the plot)."""
        super().start(doc)
        self._show_plot()

    def event(self, doc: Event) -> None:
        """Process an event document (delegate to superclass, then show the plot)."""

        super().event(doc)
        self._show_plot()

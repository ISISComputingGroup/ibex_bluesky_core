"""IBEX plotting callbacks."""

import logging
from typing import Any

import matplotlib
import matplotlib.pyplot as plt
from bluesky.callbacks import LivePlot as _DefaultLivePlot
from bluesky.callbacks.core import get_obj_fields, make_class_safe
from event_model.documents import Event, RunStart

logger = logging.getLogger(__name__)


@make_class_safe(logger=logger)  # pyright: ignore (pyright doesn't understand this decorator)
class LivePlot(_DefaultLivePlot):
    """Live plot, customized for IBEX."""

    def __init__(
        self,
        y: str,
        x: str | None = None,
        yerr: str | None = None,
        *args: Any,  # noqa: ANN401
        **kwargs: Any,  # noqa: ANN401
    ) -> None:
        """Initialise LivePlot.

        Args:
            y (str): The name of the dependant variable.
            x (str or None, optional): The name of the independant variable.
            yerr (str or None, optional): Name of uncertainties signal.
                Providing None means do not plot uncertainties.
            *args: As per mpl_plotting.py
            **kwargs: As per mpl_plotting.py

        """
        super().__init__(y=y, x=x, *args, **kwargs)  # noqa: B026
        if yerr is not None:
            self.yerr, *others = get_obj_fields([yerr])
        else:
            self.yerr = None
        self.yerr_data = []

    def _show_plot(self) -> None:
        """Call plt.show().

        Play nicely with the "normal" backends too
        - only force show if we're actually using our custom backend.
        """
        if "genie_python" in matplotlib.get_backend():
            logger.debug("Explicitly show()ing plot for IBEX")
            plt.show()

    def event(self, doc: Event) -> None:
        """Process an event document (delegate to superclass, then show the plot)."""
        new_yerr = None if self.yerr is None else doc["data"][self.yerr]
        self.update_yerr(new_yerr)
        super().event(doc)
        self._show_plot()

    def update_plot(self) -> None:
        """Create error bars if needed, then update plot."""
        if self.yerr is not None:
            self.ax.errorbar(x=self.x_data, y=self.y_data, yerr=self.yerr_data, fmt="none")  # type: ignore
        super().update_plot()

    def update_yerr(self, yerr: float | None) -> None:
        """Update uncertainties data."""
        self.yerr_data.append(yerr)

    def start(self, doc: RunStart) -> None:
        """Process an start document (delegate to superclass, then show the plot)."""
        super().start(doc)
        self._show_plot()

"""IBEX line fitting callbacks."""

import logging
import sys
from typing import Callable

import lmfit
import numpy as np
import numpy.typing as npt
from bluesky.callbacks import LiveFit as _DefaultLiveFit
from bluesky.callbacks import LiveFitPlot
from bluesky.callbacks.core import make_class_safe

sys.path.append(r"c:\instrument\apps\python3\lib\site-packages")
import matplotlib
from matplotlib.axes import Axes

matplotlib.use("module://genie_python.matplotlib_backend.ibex_websocket_backend")

import dataclasses


@dataclasses.dataclass
class ModelAndGuess:
    model: lmfit.Model | None
    guess: (
        Callable[[npt.NDArray[np.float_], npt.NDArray[np.float_]], dict[str, lmfit.Parameter]]
        | None
    )


logger = logging.getLogger(__name__)


@make_class_safe(logger=logger)  # pyright: ignore (pyright doesn't understand this decorator)
class LiveFit(_DefaultLiveFit):
    """Live fit, customized for IBEX."""

    def __init__(
        self,
        fit: ModelAndGuess,
        field_name: str,
        independent_vars: dict[str, str],
        *,
        update_every: int = 1,
    ) -> None:
        self.fit = fit

        if self.fit.model is None:
            raise ValueError("Model function cannot be None")

        super().__init__(
            model=fit.model,
            y=field_name,
            independent_vars=independent_vars,
            update_every=update_every,
        )

    def update_fit(self) -> None:
        if self.fit.guess is not None:
            self.init_guess = self.fit.guess(
                np.array(next(iter(self.independent_vars_data.values()))),
                np.array(self.ydata),
                # Calls the guess function on the set of data already collected in the run
            )

        super().update_fit()

    def live_fit_plot(
        self,
        num_points: int = 100,
        legend_keys: list[str] | None = None,
        xlim: tuple[float, float] | None = None,
        ylim: tuple[float, float] | None = None,
        ax: Axes | None = None,
        **kwargs,  # noqa: ANN003 # type: ignore
    ) -> LiveFitPlot:
        return LiveFitPlot(
            livefit=self,
            num_points=num_points,
            legend_keys=legend_keys,
            xlim=xlim,
            ylim=ylim,
            ax=ax,
            **kwargs,
        )

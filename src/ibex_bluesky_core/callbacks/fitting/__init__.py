"""For IBEX Bluesky scan fitting."""

import logging
import warnings
from collections import namedtuple
from typing import Any, Callable

import lmfit
import numpy as np
import numpy.typing as npt
from bluesky.callbacks import LiveFit as _DefaultLiveFit
from bluesky.callbacks.core import make_class_safe
from bluesky.callbacks.fitting import PeakStats as _DefaultPeakStats
from event_model.documents.event import Event

logger = logging.getLogger(__name__)


class FitMethod:
    """Tell LiveFit how to fit to a scan. Has a Model function and a Guess function.

    Model - Takes x values and a set of parameters to return y values.
    Guess - Takes x and y values and returns a rough 'guess' of the original parameters.
    """

    model: lmfit.Model
    guess: Callable[[npt.NDArray[np.float64], npt.NDArray[np.float64]], dict[str, lmfit.Parameter]]

    def __init__(
        self,
        model: lmfit.Model | Callable[[npt.NDArray[np.float64]], npt.NDArray[np.float64]],
        guess: Callable[
            [npt.NDArray[np.float64], npt.NDArray[np.float64]], dict[str, lmfit.Parameter]
        ],
    ) -> None:
        """Assign model and guess functions.

        Args:
            model (lmfit.Model | Callable): The model function to use.
            guess (Callable): The guess function to use.

        """
        self.guess = guess

        if callable(model):
            self.model = lmfit.Model(model)
        else:
            self.model = model


@make_class_safe(logger=logger)  # pyright: ignore (pyright doesn't understand this decorator)
class LiveFit(_DefaultLiveFit):
    """LiveFit, customized for IBEX."""

    def __init__(
        self, method: FitMethod, y: str, x: str, *, update_every: int = 1, yerr: str | None = None
    ) -> None:
        """Call Bluesky LiveFit with assumption that there is only one independant variable.

        Args:
            method (FitMethod): The FitMethod (Model & Guess) to use when fitting.
            y (str): The name of the dependant variable.
            x (str): The name of the independant variable.
            update_every (int, optional): How often to update the fit. (seconds)
            yerr (str or None, optional): Name of field in the Event document
                that provides standard deviation for each Y value. None meaning
                do not use uncertainties in fit.

        """
        self.method = method
        self.yerr = yerr
        self.weight_data = []

        super().__init__(
            model=method.model, y=y, independent_vars={"x": x}, update_every=update_every
        )

    def event(self, doc: Event) -> None:
        """When an event is received, update caches."""
        weight = None
        if self.yerr is not None:
            try:
                weight = 1 / doc["data"][self.yerr]
            except ZeroDivisionError:
                warnings.warn(
                    "standard deviation for y is 0, therefore applying weight of 0 on fit",
                    stacklevel=1,
                )
                weight = 0.0

        self.update_weight(weight)
        super().event(doc)

    def update_weight(self, weight: float | None = 0.0) -> None:
        """Update uncertainties cache."""
        if self.yerr is not None:
            self.weight_data.append(weight)

    def update_fit(self) -> None:
        """Use the provided guess function with the most recent x and y values after every update.

        Args:
            None

        Returns:
            None

        """
        n = len(self.model.param_names)
        if len(self.ydata) < n:
            warnings.warn(
                f"LiveFitPlot cannot update fit until there are at least {n} data points",
                stacklevel=1,
            )
        else:
            logger.debug("updating guess for %s ", self.method)
            self.init_guess = self.method.guess(
                np.array(next(iter(self.independent_vars_data.values()))),
                np.array(self.ydata),
                # Calls the guess function on the set of data already collected in the run
            )

            logger.info("new guess for %s: %s", self.method, self.init_guess)

            kwargs = {}
            kwargs.update(self.independent_vars_data)
            kwargs.update(self.init_guess)
            self.result = self.model.fit(
                self.ydata, weights=None if self.yerr is None else self.weight_data, **kwargs
            )
            self.__stale = False


def center_of_mass(x: npt.NDArray[np.float64], y: npt.NDArray[np.float64]) -> float:
    """Compute the centre of mass of the area under a curve.

    The "area under the curve" is a shape bounded by:
    - Straight line segments joining (x, y) data points, along the top edge
    - min(y), at the bottom
    - min(x), on the left-hand side
    - max(x), on the right-hand side

    Follow these rules:
    - Positive or negative background does not skew CoM
    - Order of data does not skew CoM
    - Non constant point spacing does not skew CoM
    - Always calculates CoM of the area *under* the curve, regardless of sign of Y data.
    """
    # Ensure we do not take CoM of negative masses, sort for ascending X data.
    sort_indices = np.argsort(x, kind="stable")
    x = np.take_along_axis(x, sort_indices, axis=None)
    y = np.take_along_axis(y - np.min(y), sort_indices, axis=None)

    widths = np.diff(x)

    # Area under the curve for two adjacent points is a right trapezoid.
    # Split that trapezoid into a rectangular region, plus a right triangle.
    # Find area and effective X CoM for each.
    rect_areas = widths * np.minimum(y[:-1], y[1:])
    rect_x_com = (x[:-1] + x[1:]) / 2.0
    triangle_areas = widths * np.abs(y[:-1] - y[1:]) / 2.0
    triangle_x_com = np.where(
        y[:-1] > y[1:], x[:-1] + (widths / 3.0), x[:-1] + (2.0 * widths / 3.0)
    )

    if np.sum(rect_areas + triangle_areas) == 0.0:
        # If all data was flat, return central x
        return (x[0] + x[-1]) / 2.0

    return np.sum(rect_areas * rect_x_com + triangle_areas * triangle_x_com) / np.sum(
        rect_areas + triangle_areas
    )


@make_class_safe(logger=logger)  # pyright: ignore (pyright doesn't understand this decorator)
class PeakStats(_DefaultPeakStats):
    """PeakStats, customized for IBEX."""

    @staticmethod
    def _calc_stats(
        x: npt.NDArray[np.float64],
        y: npt.NDArray[np.float64],
        fields: dict[str, float | npt.NDArray[np.float64] | None],
        edge_count: int | None = None,
    ) -> Any:  # noqa: ANN401 Pyright will not understand as return type depends on arguments
        """Call on bluesky PeakStats but calculate our own centre of mass."""
        stats = _DefaultPeakStats._calc_stats(x, y, fields, edge_count)  # noqa: SLF001
        (fields["com"],) = (center_of_mass(x, y),)
        # This will calculate CoM twice, once for Bluesky's calc and one for us
        # but keeps our value. Done this way for sleekness.
        Stats = namedtuple("Stats", field_names=fields.keys())
        stats = Stats(**fields)
        return stats

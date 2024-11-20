"""For IBEX Bluesky scan fitting."""

import logging
from typing import Callable

import lmfit
import numpy as np
import numpy.typing as npt
from bluesky.callbacks import LiveFit as _DefaultLiveFit
from bluesky.callbacks.core import make_class_safe

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
        self,
        method: FitMethod,
        y: str,
        x: str,
        *,
        update_every: int = 1,
    ) -> None:
        """Call Bluesky LiveFit with assumption that there is only one independant variable.

        Args:
            method (FitMethod): The FitMethod (Model & Guess) to use when fitting.
            y (str): The name of the dependant variable.
            x (str): The name of the independant variable.
            update_every (int): How often to update the fit. (seconds)

        """
        self.method = method

        super().__init__(
            model=method.model,
            y=y,
            independent_vars={"x": x},
            update_every=update_every,
        )

    def update_fit(self) -> None:
        """Use the provided guess function with the most recent x and y values after every update.

        Args:
            None

        Returns:
            None

        """
        logger.debug("updating guess for %s ", self.method)
        self.init_guess = self.method.guess(
            np.array(next(iter(self.independent_vars_data.values()))),
            np.array(self.ydata),
            # Calls the guess function on the set of data already collected in the run
        )
        logger.info("new guess for %s: %s", self.method, self.init_guess)

        super().update_fit()

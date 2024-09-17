"""IBEX line fitting callbacks."""

import logging
import sys
from typing import Callable

import lmfit
import numpy as np
import numpy.typing as npt
from bluesky.callbacks import LiveFit as _DefaultLiveFit
from bluesky.callbacks.core import make_class_safe

sys.path.append(r"c:\instrument\apps\python3\lib\site-packages")
import matplotlib

matplotlib.use("module://genie_python.matplotlib_backend.ibex_websocket_backend")


class FitMethod:
    model: lmfit.Model | None
    guess: (
        Callable[[npt.NDArray[np.float64], npt.NDArray[np.float64]], dict[str, lmfit.Parameter]]
        | None
    )

    def __init__(
        self,
        model: lmfit.Model | Callable[..., float] | None,
        guess: Callable[
            [npt.NDArray[np.float64], npt.NDArray[np.float64]], dict[str, lmfit.Parameter]
        ],
    ) -> None:
        if callable(model):
            self.model = lmfit.Model(model)
        else:
            self.model = model

        self.guess = guess


logger = logging.getLogger(__name__)


@make_class_safe(logger=logger)  # pyright: ignore (pyright doesn't understand this decorator)
class LiveFit(_DefaultLiveFit):
    """Live fit, customized for IBEX."""

    def __init__(
        self,
        method: FitMethod,
        dependant_var_name: str,
        independent_var_name: str,
        *,
        update_every: int = 1,
    ) -> None:
        self.method = method

        if self.method.model is None:
            raise ValueError("Model function cannot be None")

        super().__init__(
            model=method.model,
            y=dependant_var_name,
            independent_vars={"x": independent_var_name},
            update_every=update_every,
        )

    def update_fit(self) -> None:
        if self.method.guess is not None:
            self.init_guess = self.method.guess(
                np.array(next(iter(self.independent_vars_data.values()))),
                np.array(self.ydata),
                # Calls the guess function on the set of data already collected in the run
            )

        super().update_fit()

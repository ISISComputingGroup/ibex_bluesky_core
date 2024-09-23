from typing import Any, Callable
from unittest import mock

import numpy as np
from ibex_bluesky_core.callbacks.fitting import LiveFit, FitMethod
import lmfit
import numpy.typing as npt


def test_guess_called():

    guess=mock.MagicMock()
    def model(x: npt.NDArray[np.float64]):
        return x
    fit = FitMethod(model=lmfit.Model(model), guess=guess)
    lf = LiveFit(fit, y="y", x="x")

    x = 1
    y = 2

    # Fake just enough of an event document.
    lf.event({"data": {    # type: ignore
                "y": y,
                "x": x,
            }})

    # Assert that guess_impl was called with the correct arguments
    guess.assert_called_with(x, y)


def test_model_called():

    model_mock = mock.MagicMock()

    def guess(x: npt.NDArray[np.float64], y: npt.NDArray[np.float64]
        ) -> dict[str, lmfit.Parameter]:
            return {}
    
    def model(x: npt.NDArray[np.float64]) -> npt.NDArray[np.float64]:

        model_mock()
        return x
    
    fit = FitMethod(model=lmfit.Model(model), guess=guess)

    lf = LiveFit(fit, y="y", x="x")

    x = 1
    y = 2

    # Fake just enough of an event document.
    lf.event({"data": {    # type: ignore
                "y": y,
                "x": x,
            }})

    # Assert that guess_impl was called with the correct arguments
    model_mock.assert_called()
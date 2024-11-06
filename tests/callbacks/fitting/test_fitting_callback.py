from unittest import mock
from unittest.mock import patch, MagicMock

import lmfit
import numpy as np
import numpy.typing as npt

from ibex_bluesky_core.callbacks.fitting import FitMethod, LiveFit


def test_guess_called():
    guess = mock.MagicMock()

    def model(x: npt.NDArray[np.float64]):
        return x

    fit = FitMethod(model=lmfit.Model(model), guess=guess)
    lf = LiveFit(fit, y="y", x="x")

    x = 1
    y = 2

    # Fake just enough of an event document.
    lf.event(
        {
            "data": {  # type: ignore
                "y": y,
                "x": x,
            }
        }
    )

    # Assert that guess_impl was called with the correct arguments
    guess.assert_called_with(x, y)


def test_lmfit_model_called():
    model_mock = mock.MagicMock()

    def guess(x: npt.NDArray[np.float64], y: npt.NDArray[np.float64]) -> dict[str, lmfit.Parameter]:
        return {}

    def model(x: npt.NDArray[np.float64]) -> npt.NDArray[np.float64]:
        model_mock()
        return x

    fit = FitMethod(model=lmfit.Model(model), guess=guess)

    lf = LiveFit(fit, y="y", x="x")

    x = 1
    y = 2

    # Fake just enough of an event document.
    lf.event(
        {
            "data": {  # type: ignore
                "y": y,
                "x": x,
            }
        }
    )

    model_mock.assert_called()


def test_model_called():
    model_mock = mock.MagicMock()

    def guess(x: npt.NDArray[np.float64], y: npt.NDArray[np.float64]) -> dict[str, lmfit.Parameter]:
        return {}

    def model(x: npt.NDArray[np.float64]) -> npt.NDArray[np.float64]:
        model_mock()
        return x

    fit = FitMethod(model=model, guess=guess)
    # Does not pass the function to lmfit before FitMethod

    lf = LiveFit(fit, y="y", x="x")

    x = 1
    y = 2

    # Fake just enough of an event document.
    lf.event(
        {
            "data": {  # type: ignore
                "y": y,
                "x": x,
            }
        }
    )

    model_mock.assert_called()

# @patch('ibex_bluesky_core.callbacks.fitting.lmfit')
def test_model_called_with_weights_if_yerr_is_given():
    # model_mock = mock.MagicMock()
    #
    def guess(x: npt.NDArray[np.float64], y: npt.NDArray[np.float64]) -> dict[str, lmfit.Parameter]:
        return {}
    #
    # def model(x: npt.NDArray[np.float64]) -> npt.NDArray[np.float64]:
    #     model_mock()
    #     return x

    # fit = mock.MagicMock()
    # type(fit).independent_vars = {"x"}
    # Does not pass the function to lmfit before FitMethod
    model = lmfit.Model(lambda x:x)
    model.fit = MagicMock()
    method = FitMethod(model=model, guess=guess)
    lf = LiveFit(method, y="y", x="x", yerr="yerr")


    x = 1
    y = 2
    yerr = 3

    # Fake just enough of an event document.
    lf.event(
        {
            "data": {  # type: ignore
                "y": y,
                "x": x,
                "yerr": yerr
            }
        }
    )

    lf.update_fit()

    model.fit.assert_called_with([y], weights = [1/yerr], x=[1])

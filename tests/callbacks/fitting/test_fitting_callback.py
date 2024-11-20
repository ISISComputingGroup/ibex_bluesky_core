import warnings
from unittest import mock
from unittest.mock import MagicMock

import lmfit
import numpy as np
import numpy.typing as npt

from ibex_bluesky_core.callbacks.fitting import FitMethod, LiveFit
from ibex_bluesky_core.callbacks.fitting.fitting_utils import Linear


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


def test_model_called_with_weights_if_yerr_is_given():
    def guess(x: npt.NDArray[np.float64], y: npt.NDArray[np.float64]) -> dict[str, lmfit.Parameter]:
        return {}

    model = lmfit.Model(lambda x: x)
    model.fit = MagicMock()
    method = FitMethod(model=model, guess=guess)
    lf = LiveFit(method, y="y", x="x", yerr="yerr")

    x = 1
    y = 2
    yerr = 3

    lf.event(
        {
            "data": {  # type: ignore
                "y": y,
                "x": x,
                "yerr": yerr,
            }
        }
    )

    model.fit.assert_called_with([y], weights=[1 / yerr], x=[1])


def test_warning_given_if_yerr_is_0():
    def guess(x: npt.NDArray[np.float64], y: npt.NDArray[np.float64]) -> dict[str, lmfit.Parameter]:
        return {}

    model = lmfit.Model(lambda x: x)
    model.fit = MagicMock()
    method = FitMethod(model=model, guess=guess)
    lf = LiveFit(method, y="y", x="x", yerr="yerr")

    x = 1
    y = 2
    yerr = 0

    with warnings.catch_warnings(record=True) as w:
        lf.event(
            {
                "data": {  # type: ignore
                    "y": y,
                    "x": x,
                    "yerr": yerr,
                }
            }
        )

        model.fit.assert_called_with([y], weights=[0.0], x=[1])

        assert len(w) == 1
        assert "standard deviation for y is 0, therefore applying weight of 0 on fit" in str(
            w[-1].message
        )


def test_warning_if_no_y_data():
    with warnings.catch_warnings(record=True) as w:
        lf = LiveFit(Linear.fit(), y="y", x="x", yerr="yerr")
        lf.update_fit()

        assert len(w) == 1
        assert "LiveFitPlot cannot update fit until there are at least" in str(w[-1].message)

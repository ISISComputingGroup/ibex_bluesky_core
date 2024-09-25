from typing import Callable
from unittest import mock

import lmfit
import numpy as np
import numpy.typing as npt
import pytest
from ibex_bluesky_core.callbacks.fitting import LiveFit
from ibex_bluesky_core.callbacks.fitting_utils import Fit, Gaussian, Lorentzian

# 2 Tests per fit class

# Test the model func:
#   Given a set of params and input should give the same output always
# Test the guess func:
#   Given x,y sets of data should always give the same closely correct output params

# Some tests for custom fits, custom guess + std model and vice versa


class MockFit(Fit):
    mmock = mock.MagicMock()

    @classmethod
    def get_mmock(cls) -> mock.MagicMock:
        return cls.mmock

    @classmethod
    def model(cls, *args: int) -> lmfit.Model:
        def model(x: npt.NDArray[np.float_], offset: float) -> npt.NDArray[np.float_]:
            cls.mmock()
            return x + offset

        return lmfit.Model(model)

    @classmethod
    def guess(
        cls, *args: int
    ) -> Callable[[npt.NDArray[np.float64], npt.NDArray[np.float64]], dict[str, lmfit.Parameter]]:
        def guess(
            x: npt.NDArray[np.float64], y: npt.NDArray[np.float64]
        ) -> dict[str, lmfit.Parameter]:
            cls.mmock()
            init_guess = {"offset": lmfit.Parameter("offset", 1)}
            return init_guess

        return guess


def test_fit_method_uses_respective_model_and_guess():
    lf = LiveFit(MockFit.fit(), y="y", x="x")

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

    assert MockFit.get_mmock().call_count >= 2


class TestGaussian:
    class TestGaussianModel:
        def test_gaussian_model(self):
            x = np.arange(-5.0, 5.0, 1.0)

            background = 1.0
            amp = 1.0
            sigma = 1
            x0 = 0.0

            outp = Gaussian.model().func(x, amp, sigma, x0=x0, background=background)
            outp1 = Gaussian.model().func(x, amp, sigma + 1, x0=x0, background=background)

            # Check the output starts and ends at background level
            assert pytest.approx(outp[0], rel=1e-2) == background
            assert pytest.approx(outp[-1], rel=1e-2) == background

            # Check the peak is at x0
            peak_index = np.argmin(np.abs(x - x0))
            assert pytest.approx(outp[peak_index], rel=1e-2) == amp + background

            # Check that as sigma increases, steepness of gaussian decreases
            assert np.max(np.diff(outp)) > np.max(np.diff(outp1))

        def test_invalid_gaussian_model(self):
            x = np.arange(-5.0, 5.0, 1.0)

            outp = Gaussian.model().func(x, amp=1.0, sigma=0.0, x0=0.0, background=1.0)
            outp1 = Gaussian.model().func(x, amp=1.0, sigma=1.0, x0=0.0, background=1.0)
            assert np.allclose(outp, outp1)

    class TestGaussianGuess:
        def test_background(self):
            x = np.array([-1.0, 0.0, 1.0])
            y = np.array([1.0, 2.0, 1.0])
            outp = Gaussian.guess()(x, y)

            assert pytest.approx(y[0], rel=1e-2) == outp["background"].value

        def test_amp_x0(self):
            x = np.array([-1.0, 0.0, 1.0])
            y = np.array([1.0, 2.0, 1.0])
            outp = Gaussian.guess()(x, y)

            assert y[1] == pytest.approx(outp["amp"].value + outp["background"].value, rel=1e-2)  # type: ignore

        def test_neg_amp_x0(self):
            x = np.array([-1.0, 0.0, 1.0])
            y = np.array([-1.0, -2.0, -1.0])
            outp = Gaussian.guess()(x, y)

            assert outp["amp"] < 0

        def test_sigma(self):
            x = np.array([-1.0, 0.0, 1.0])
            y = np.array([1.0, 2.0, 1.0])
            y1 = np.array([1.5, 1.75, 1.5])

            outp = Gaussian.guess()(x, y)
            outp1 = Gaussian.guess()(x, y1)

            assert outp["sigma"].value < outp1["sigma"].value  # type: ignore


class TestLorentzian:
    class TestLorentzianModel:
        def test_lorentzian_model(self):
            x = np.arange(-5.0, 5.0, 1.0)

            background = 1.0
            amp = 1.0
            sigma = 1
            center = 0.0

            outp = Lorentzian.model().func(x, amp, sigma, center=center, background=background)
            outp1 = Lorentzian.model().func(x, amp, sigma + 1, center=center, background=background)

            # Check the output starts and ends at background level
            assert pytest.approx(outp[0], rel=1e-1) == background
            assert pytest.approx(outp[-1], rel=1e-1) == background

            # Check the peak is at center
            peak_index = np.argmin(np.abs(x - center))
            assert pytest.approx(outp[peak_index], rel=1e-2) == amp + background

            # Check that as sigma increases, steepness of gaussian decreases
            assert np.max(np.diff(outp)) > np.max(np.diff(outp1))

        def test_invalid_lorentzian_model(self):
            x = np.arange(-5.0, 5.0, 1.0)

            outp = Lorentzian.model().func(x, amp=1.0, sigma=0.0, center=0.0, background=1.0)
            outp1 = Lorentzian.model().func(x, amp=1.0, sigma=1.0, center=0.0, background=1.0)
            assert np.allclose(outp, outp1)

    class TestLorentzianGuess:
        def test_background(self):
            x = np.array([-1.0, 0.0, 1.0])
            y = np.array([1.0, 2.0, 1.0])
            outp = Lorentzian.guess()(x, y)

            assert pytest.approx(y[0], rel=1e-1) == outp["background"].value

        def test_amp_center(self):
            x = np.array([-1.0, 0.0, 1.0])
            y = np.array([1.0, 2.0, 1.0])
            outp = Lorentzian.guess()(x, y)

            assert y[1] == pytest.approx(outp["amp"].value + outp["background"].value, rel=1e-2)  # type: ignore

        def test_neg_amp_x0(self):
            x = np.array([-1.0, 0.0, 1.0])
            y = np.array([-1.0, -2.0, -1.0])
            outp = Lorentzian.guess()(x, y)

            assert outp["amp"] < 0

        def test_sigma(self):
            x = np.array([-1.0, 0.0, 1.0, 2.0])
            y = np.array([0.0, 2.0, 0.0, 0.0])
            y1 = np.array([1.9, 2.0, 1.9, 1.8])

            outp = Lorentzian.guess()(x, y)
            outp1 = Lorentzian.guess()(x, y1)

            assert outp["sigma"].value < outp1["sigma"].value  # type: ignore

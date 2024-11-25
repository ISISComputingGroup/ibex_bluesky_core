import warnings
from typing import Callable
from unittest import mock

import lmfit
import numpy as np
import numpy.typing as npt
import pytest
import scipy.signal as scsi

from ibex_bluesky_core.callbacks.fitting import LiveFit
from ibex_bluesky_core.callbacks.fitting.fitting_utils import (
    ERF,
    ERFC,
    DampedOsc,
    Fit,
    Gaussian,
    Linear,
    Lorentzian,
    Polynomial,
    SlitScan,
    TopHat,
    Trapezoid,
)


class MockFit(Fit):
    mock_model = mock.MagicMock()
    mock_guess = mock.MagicMock()

    @classmethod
    def mocks_called(cls) -> bool:
        return cls.mock_model.called and cls.mock_guess.called

    @classmethod
    def model(cls, *args: int) -> lmfit.Model:
        def model(x: npt.NDArray[np.float64], offset: float) -> npt.NDArray[np.float64]:
            cls.mock_model()
            return x + offset

        return lmfit.Model(model)

    @classmethod
    def guess(
        cls, *args: int
    ) -> Callable[[npt.NDArray[np.float64], npt.NDArray[np.float64]], dict[str, lmfit.Parameter]]:
        def guess(
            x: npt.NDArray[np.float64], y: npt.NDArray[np.float64]
        ) -> dict[str, lmfit.Parameter]:
            cls.mock_guess()
            init_guess = {"offset": lmfit.Parameter("offset", 1)}
            return init_guess

        return guess


def test_fit_method_uses_respective_model_and_guess():
    # Checks that model and guess are called atleast once each
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

    assert MockFit.mocks_called()


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
            # if sigma = 0.0 then gets changed to 1.0 in model func, this asserts that it does this
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
            # upside down gaussian
            x = np.array([-1.0, 0.0, 1.0])
            y = np.array([-1.0, -2.0, -1.0])
            outp = Gaussian.guess()(x, y)

            assert outp["amp"] < 0

        def test_sigma(self):
            x = np.array([-1.0, 0.0, 1.0])
            y = np.array([1.0, 2.0, 1.0])
            # y1 is "wider" so must have higher sigma
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

            outp = Lorentzian.model().func(
                x, amp=amp, sigma=sigma, center=center, background=background
            )
            outp1 = Lorentzian.model().func(
                x, amp=amp, sigma=sigma + 1, center=center, background=background
            )

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
            # if sigma = 0.0 then gets changed to 1.0 in model func, this asserts that it does this
            assert np.allclose(outp, outp1)

    class TestLorentzianGuess:
        def test_background(self):
            x = np.array([-1.0, 0.0, 1.0])
            y = np.array([1.0, 2.0, 1.0])
            outp = Lorentzian.guess()(x, y)

            assert pytest.approx(1.0, rel=1e-1) == outp["background"].value

        def test_amp_center(self):
            x = np.array([-1.0, 0.0, 1.0])
            y = np.array([1.0, 2.0, 1.0])
            outp = Lorentzian.guess()(x, y)

            assert 2.0 == pytest.approx(outp["amp"].value + outp["background"].value, rel=1e-2)  # type: ignore

        def test_neg_amp_x0(self):
            # upside down lorentzian
            x = np.array([-1.0, 0.0, 1.0])
            y = np.array([-1.0, -2.0, -1.0])
            outp = Lorentzian.guess()(x, y)

            assert outp["amp"] < 0

        def test_sigma(self):
            x = np.array([-1.0, 0.0, 1.0, 2.0])
            y = np.array([0.0, 2.0, 0.0, 0.0])
            # y1 is "wider" so must have higher sigma
            y1 = np.array([1.9, 2.0, 1.9, 1.8])

            outp = Lorentzian.guess()(x, y)
            outp1 = Lorentzian.guess()(x, y1)

            assert outp["sigma"].value < outp1["sigma"].value  # type: ignore


class TestLinear:
    class TestLinearModel:
        def test_linear_model(self):
            x = np.arange(-5.0, 5.0, 1.0)
            grad = 3
            y_intercept = 2

            outp = Linear.model().func(x, c1=grad, c0=y_intercept)

            # Check for constant gradient of grad
            outp_m = np.diff(outp)
            assert np.all(outp_m == grad)

            # Check that when x = 0 that y = y intercept
            assert outp[5] == y_intercept

    class TestLinearGuess:
        def test_gradient_guess(self):
            x = np.array([-1.0, 0.0, 1.0])
            y = np.array([-1.0, 0.0, 1.0])
            outp = Linear.guess()(x, y)

            assert pytest.approx(outp["c1"]) == 1.0

            y = np.array([-2.0, 0.0, 2.0])
            outp1 = Linear.guess()(x, y)
            # check with a graph with steeper gradient
            assert outp["c1"] < outp1["c1"]

        def test_y_intercept_guess(self):
            x = np.array([-1.0, 0.0, 1.0])
            y = np.array([-1.0, 0.0, 1.0])
            outp = Linear.guess()(x, y)

            assert pytest.approx(outp["c0"]) == 0.0

        def test_zero_gradient_guess(self):
            x = np.array([-1.0, 0.0, 1.0])
            y = np.array([0.0, 0.0, 0.0])
            outp = Linear.guess()(x, y)

            assert pytest.approx(outp["c1"]) == 0.0


class TestPolynomial:
    class TestPolynomialModel:
        # Polynomial model provided by lmfit so no need to test extensively
        # Just test that polynomial order <= 7 and >= 0

        @pytest.mark.parametrize("deg", [-1, 8])
        def test_polynomial_model_order(self, deg: int):
            # -1 and 8 are both invalid polynomial degrees
            x = np.zeros(3)

            with pytest.raises(ValueError):
                Polynomial.model(deg).func(x)

        def test_polynomial_model(self):
            # check no problems
            x = np.zeros(3)
            Polynomial.model(7).func(x)

    class TestPolynomialGuess:
        # Uses numpy polyfit so no need to test much
        # Check that params and values are allocated correctly

        @pytest.mark.parametrize("deg", [2, 7])
        def test_polynomial_guess(self, deg: int):
            warnings.filterwarnings("ignore")
            # Suppress a rank warning, but np.RankWarning is deprecated

            x = np.array([-1.0, 0.0, 1.0])
            y = np.array([1.0, 0.0, 1.0])

            outp = Polynomial.guess(deg)(x, y)

            assert len(outp) == deg + 1

            for i in range(deg + 1):
                assert outp[f"c{i}"] is not None
            # checks that param values are allocated to param names
            # and that 2 and 7 are both valid polynomial degrees

        @pytest.mark.parametrize("deg", [-1, 8])
        def test_invalid_polynomial_guess(self, deg: int):
            x = np.array([-1.0, 0.0, 1.0])
            y = np.array([1.0, 0.0, 1.0])

            # -1 and 8 are both invalid polynomial degrees
            with pytest.raises(ValueError):
                Polynomial.guess(deg)(x, y)


class TestDampedOsc:
    class TestDampedOscModel:
        def test_damped_osc_model(self):
            x = np.arange(-5.0, 5.0, 1.0)

            amp = 1
            freq = 1
            center = 0
            width = 2

            outp = DampedOsc.model().func(x, center=center, amp=amp, freq=freq, width=width)

            # Check that the model produces no values further away from x-axis than amp
            assert amp >= np.max(outp)
            assert -amp <= np.min(outp)

            # Check that the centre is at a peak
            assert x[np.argmax(outp)] == center or x[np.argmin(outp)] == center

            outp1 = DampedOsc.model().func(
                x, center=center, amp=amp, freq=freq + 3, width=width + 10
            )

            peaks, _ = scsi.find_peaks(outp)
            peaks1, _ = scsi.find_peaks(outp1)

            # Check that the model with the higher freq has more peaks
            assert peaks.size < peaks1.size

            # Check that the model with the greater width will have taller sides
            assert abs(outp[0]) < abs(outp1[0])
            assert abs(outp[-1]) < abs(outp1[-1])

    class TestDampedOscGuess:
        def test_guess_amp_center(self):
            x = np.array([-1.0, 0.0, 1.0])
            y = np.array([1.0, 2.0, 1.0])
            outp = DampedOsc.guess()(x, y)

            assert 2.0 == pytest.approx(outp["amp"].value, rel=1e-2)

        def test_guess_width(self):
            x = np.array([-2.0, -1.0, 0.0, 1.0, 2.0])
            y = np.array([0.0, 1.0, 1.0, 1.0, 0.0])
            outp = DampedOsc.guess()(x, y)

            # Checks that the width guess is max x - min x
            assert pytest.approx(outp["width"].value, rel=1e-2) == 4.0

        def test_guess_freq(self):
            x = np.array([-2.0, -1.0, 0.0, 1.0, 2.0])
            y = np.array([0.0, 2.0, 0.0, -2.0, 0.0])
            outp = DampedOsc.guess()(x, y)

            # freq = pi / (peak_x - valley_x) = pi / (1 - -1)
            assert pytest.approx(outp["freq"].value, rel=1e-2) == np.pi / 2


class TestSlitScan:
    def test_max_slit_width(self):
        x = np.arange(-5.0, 5.0, 1.0)
        y = np.zeros(10)

        # -1 is not a valid max slit gap
        with pytest.raises(ValueError):
            SlitScan.guess(-1)(x, y)

    class TestSlitScanModel:
        def test_slit_scan_model(self):
            x = np.arange(-5.0, 5.0, 1.0)
            background = 1
            height_above_inflection1 = 5
            gradient = 1
            inflections_diff = 6
            inflection0 = -3

            outp = SlitScan.model().func(
                x,
                background=background,
                inflection0=inflection0,
                gradient=gradient,
                inflections_diff=inflections_diff,
                height_above_inflection1=height_above_inflection1,
            )

            # Check that the max outp value is not greater than
            # the highest point of model given params
            assert (
                np.max(outp) <= background + gradient * inflections_diff + height_above_inflection1
            )

            # Check that any points past x = inflection0
            # do not have a y value equal to or below background
            assert np.all(outp[np.where(x > inflection0)] > background)

        def test_slit_scan_model_no_exp(self):
            x = np.arange(-5.0, 5.0, 1.0)
            background = 1
            height_above_inflection1 = 0
            gradient = 1
            inflections_diff = 3
            inflection0 = -3
            # inflection1 at x=0 y=4

            outp = SlitScan.model().func(
                x,
                background=background,
                inflection0=inflection0,
                gradient=gradient,
                inflections_diff=inflections_diff,
                height_above_inflection1=height_above_inflection1,
            )

            # Check that second half of array,
            # starting from inflection1, is a flat line
            # and that all values before are below this line
            line = background + gradient * inflections_diff
            assert np.all(outp[5:] == line)
            assert np.all(outp[:4] < line)

    class TestSlitScanGuess:
        def test_guess_background(self):
            x = np.array([-1.0, 0.0, 1.0, 2.0])
            y = np.array([1.0, 1.0, 2.0, 3.0])
            outp = SlitScan.guess()(x, y)

            assert 1.0 == pytest.approx(outp["background"].value, rel=1e-2)

        def test_guess_gradient(self):
            x = np.array([-1.0, 0.0, 1.0, 2.0, 3.0, 4.0])
            y = np.array([1.0, 1.0, 2.0, 3.0, 4.0, 4.0])
            outp = SlitScan.guess()(x, y)

            assert 1.0 == pytest.approx(outp["gradient"].value, rel=1e-2)

        def test_guess_inflections_diff(self):
            x = np.array([-1.0, 0.0, 1.0, 2.0, 3.0, 4.0])
            y = np.array([1.0, 1.0, 2.0, 3.0, 4.0, 4.0])
            outp = SlitScan.guess()(x, y)

            assert 3.0 == pytest.approx(outp["inflections_diff"].value, rel=1e-2)

        def test_guess_inflections_diff_with_all_zero_data(self):
            x = np.array([-1.0, 0.0, 1.0, 2.0, 3.0, 4.0])
            y = np.array([0.0, 0.0, 0.0, 0.0, 0.0, 0.0])
            outp = SlitScan.guess()(x, y)

            assert 1.0 == pytest.approx(outp["inflections_diff"].value, rel=1e-2)

        def test_guess_height_above_inflection1(self):
            x = np.array([-1.0, 0.0, 1.0, 2.0, 3.0, 4.0])
            y = np.array([1.0, 1.0, 2.0, 3.0, 4.0, 4.0])
            outp = SlitScan.guess()(x, y)

            assert 1.0 == pytest.approx(outp["height_above_inflection1"].value, rel=1e-2)

        def test_guess_inflection0(self):
            x = np.arange(-5.0, 5.0, 1.0)
            y = np.array([0, 0, 0, 0, 0, 1, 2, 3, 4, 5])
            outp = SlitScan.guess()(x, y)

            assert -2.0 == pytest.approx(outp["inflection0"].value, rel=1e-2)


class TestERF:
    class TestERFModel:
        # only need to test for background and scale
        # as using scipy sci model
        def test_erf_model(self):
            x = np.arange(-5.0, 6.0, 1.0)
            cen = 0
            stretch = 1
            scale = 1
            background = 1

            outp = ERF.model().func(x, background=background, cen=cen, stretch=stretch, scale=scale)

            assert background == pytest.approx(np.mean(outp), rel=1e-2)

            outp1 = ERF.model().func(
                x, background=background, cen=cen, stretch=stretch, scale=scale + 5
            )

            # an erf with a greater y-scale should mean greater y mean on absolute values
            assert np.mean(np.abs(outp)) < np.mean(np.abs(outp1))

    class TestERFGuess:
        def test_guess_background(self):
            x = np.array([-1.0, 0.0, 1.0])
            y = x

            outp = ERF.guess()(x, y)

            assert pytest.approx(outp["background"], rel=1e-2) == 0.0

        def test_guess_scale(self):
            x = np.array([-1.0, 0.0, 1.0])
            y = np.array([-2.0, 0.0, 2.0])

            outp = ERF.guess()(x, y)

            assert pytest.approx(outp["scale"], rel=1e-2) == 2.0


class TestERFC:
    class TestERFCModel:
        # only need to test for background and scale
        # as using scipy sci model
        def test_erfc_model(self):
            x = np.arange(-5.0, 6.0, 1.0)
            cen = 0
            stretch = 1
            scale = 1
            background = 1

            outp = ERFC.model().func(
                x, background=background, cen=cen, stretch=stretch, scale=scale
            )

            assert background == pytest.approx(np.min(outp), rel=1e-2)

            outp1 = ERFC.model().func(
                x, background=background, cen=cen, stretch=stretch, scale=scale + 5
            )

            # an erf with a greater y-scale should mean greater y mean on absolute values
            assert np.mean(np.abs(outp)) < np.mean(np.abs(outp1))

    class TestERFCGuess:
        def test_guess_background(self):
            x = np.array([-1.0, 0.0, 1.0])
            y = np.array([2.0, 1.0, 0.0])

            outp = ERFC.guess()(x, y)

            assert pytest.approx(outp["background"], rel=1e-2) == 0.0

        def test_guess_scale(self):
            x = np.array([-1.0, 0.0, 1.0])
            y = np.array([4.0, 2.0, 0.0])

            outp = ERFC.guess()(x, y)

            assert pytest.approx(outp["scale"], rel=1e-2) == 2.0


class TestTopHat:
    class TestTopHatModel:
        def test_top_hat_model(self):
            x = np.arange(-5.0, 6.0, 1.0)
            cen = 0
            width = 1
            height = 1
            background = 1

            outp = TopHat.model().func(
                x, background=background, cen=cen, width=width, height=height
            )

            assert background == pytest.approx(np.min(outp), rel=1e-2)
            assert height + background == pytest.approx(np.max(outp), rel=1e-2)

            outp1 = TopHat.model().func(
                x, background=background, cen=cen + 3, width=width + 3, height=height
            )

            # check width
            assert np.mean(outp) < np.mean(outp1)

            # check centre
            assert np.mean(x[np.where(outp > background)]) < np.mean(
                x[np.where(outp1 > background)]
            )

    class TestTopHatGuess:
        def test_background_guess(self):
            x = np.array([-1.0, 0.0, 1.0, 2.0, 3.0])
            y = np.array([1.0, 2.0, 2.0, 2.0, 1.0])

            outp = TopHat.guess()(x, y)

            assert outp["background"] == pytest.approx(1.0, rel=1e-2)

        def test_cen_height_guess(self):
            x = np.array([-1.0, 0.0, 1.0, 2.0, 3.0])
            y = np.array([1.0, 1.0, 2.0, 1.0, 1.0])

            outp = TopHat.guess()(x, y)

            assert outp["cen"] == pytest.approx(1.0, rel=1e-2)
            assert outp["height"] == pytest.approx(1.0, rel=1e-2)

        def test_width_guess(self):
            x = np.array([-2.0, -1.0, 0.0, 1.0, 2.0, 3.0])
            y = np.array([1.0, 1.0, 2.0, 2.0, 1.0, 1.0])

            outp = TopHat.guess()(x, y)

            assert outp["width"] == pytest.approx(1.0, rel=1e-2)

        def test_guess_given_flat_data(self):
            x = np.arange(-5.0, 5.0, 1.0)
            y = np.zeros_like(x) + 1

            outp = TopHat.guess()(x, y)
            assert outp["width"] == pytest.approx((max(x) - min(x)) / 2, rel=1e-2)


class TestTrapezoid:
    class TestTrapezoidModel:
        def test_trapezoid_model(self):
            x = np.arange(-5.0, 6.0, 1.0)
            cen = 0
            y_offset = 1
            height = 1
            background = 1
            gradient = 1

            outp = Trapezoid.model().func(
                x,
                cen=cen,
                y_offset=y_offset,
                height=height,
                background=background,
                gradient=gradient,
            )

            assert background == pytest.approx(np.min(outp), rel=1e-2)
            assert height + background == pytest.approx(np.max(outp), rel=1e-2)

            outp1 = Trapezoid.model().func(
                x,
                cen=cen + 3,
                y_offset=y_offset,
                height=height,
                background=background,
                gradient=gradient - 0.5,
            )

            # check centre moves when data is shifted
            assert np.mean(x[np.where(outp > background)]) < np.mean(
                x[np.where(outp1 > background)]
            )

            # check gradient: a greater gradient means greater average y values as wider
            assert np.mean(outp) < np.mean(outp1)

            outp2 = Trapezoid.model().func(
                x,
                cen=cen,
                y_offset=y_offset + 5,
                height=height,
                background=background,
                gradient=gradient,
            )

            # check y_offset: a greater y_offset means greater average y values as wider
            assert np.mean(outp) < np.mean(outp2)

    class TestTrapezoidGuess:
        def test_background_guess(self):
            x = np.array([-1.0, 0.0, 1.0, 2.0, 3.0])
            y = np.array([1.0, 2.0, 2.0, 2.0, 1.0])

            outp = Trapezoid.guess()(x, y)

            assert outp["background"] == pytest.approx(1.0, rel=1e-2)

        def test_cen_height_guess(self):
            x = np.array([-1.0, 0.0, 1.0, 2.0, 3.0])
            y = np.array([1.0, 1.0, 2.0, 1.0, 1.0])

            outp = Trapezoid.guess()(x, y)

            assert outp["cen"] == pytest.approx(1.0, rel=1e-2)
            assert outp["height"] == pytest.approx(1.0, rel=1e-2)

        def test_gradient_guess(self):
            x = np.array([-4.0, -3.0, -2.0, -1.0, 0.0, 1.0, 2.0, 3.0, 4.0])
            y = np.array([1.0, 2.0, 4.0, 8.0, 16.0, 8.0, 4.0, 2.0, 1.0])

            # Should choose x = -1.0 as x1 and x = -2.5 as x0
            # height = 16 - 1 = 15
            # gradient = 15 / (-1 - -2.5) = 10

            outp = Trapezoid.guess()(x, y)

            assert outp["gradient"] == pytest.approx(10.0, rel=1e-2)

        def test_y_offset_guess(self):
            x = np.arange(-5.0, 5.0, 1.0)
            y = np.array([1.0, 1.0, 1.0, 2.0, 3.0, 3.0, 3.0, 2.0, 1.0, 1.0, 1.0])

            outp = Trapezoid.guess()(x, y)

            x1 = np.arange(-6.0, 6.0, 1.0)
            y1 = np.array([1.0, 1.0, 1.0, 2.0, 3.0, 3.0, 3.0, 3.0, 3.0, 2.0, 1.0, 1.0, 1.0])

            outp1 = Trapezoid.guess()(x1, y1)

            # Assert that with a greater top width, y_offset increases
            assert outp["y_offset"] < outp1["y_offset"]

        def test_guess_given_flat_data(self):
            x = np.arange(-5.0, 5.0, 1.0)
            y = np.zeros_like(x) + 1

            outp = Trapezoid.guess()(x, y)
            # check that with flat data gradient guess is 0
            assert outp["gradient"] == pytest.approx(0.0, rel=1e-2)

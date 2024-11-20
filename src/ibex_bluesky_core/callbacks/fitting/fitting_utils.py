"""Defines the standard fits. The model and guess functions for each fit."""

from abc import ABC, abstractmethod
from typing import Callable

import lmfit
import numpy as np
import numpy.typing as npt
import scipy
import scipy.special
from lmfit.models import PolynomialModel
from numpy import polynomial as p

from ibex_bluesky_core.callbacks.fitting import FitMethod


class Fit(ABC):
    """Base class for all fits."""

    @classmethod
    @abstractmethod
    def model(cls, *args: int) -> lmfit.Model:
        """Outline base model function.

        Args:
            *args (int): Any extra parameters required for fitting.

        Returns:
            lmfit.Model: Model function
            (x-values: NDArray, parameters: np.float64 -> y-values: NDArray)

        """
        pass

    @classmethod
    @abstractmethod
    def guess(
        cls, *args: int
    ) -> Callable[[npt.NDArray[np.float64], npt.NDArray[np.float64]], dict[str, lmfit.Parameter]]:
        """Outline base Guessing. method.

        Args:
            *args (int): Any extra parameters required for fitting.

        Returns:
            Callable: Guess function
            (x-values: NDArray, y-values: NDArray -> parameters: Dict[str, lmfit.Parameter])

        """
        pass

    @classmethod
    def fit(cls, *args: int) -> FitMethod:
        """Return a FitMethod given model and guess functions to pass to LiveFit."""
        return FitMethod(model=cls.model(*args), guess=cls.guess(*args))


class Gaussian(Fit):
    """Gaussian Fitting."""

    @classmethod
    def model(cls, *args: int) -> lmfit.Model:
        """Gaussian Model."""

        def model(
            x: npt.NDArray[np.float64], amp: float, sigma: float, x0: float, background: float
        ) -> npt.NDArray[np.float64]:
            if sigma == 0:
                sigma = 1

            return amp * np.exp(-((x - x0) ** 2) / (2 * sigma**2)) + background

        return lmfit.Model(model)

    @classmethod
    def guess(
        cls, *args: int
    ) -> Callable[[npt.NDArray[np.float64], npt.NDArray[np.float64]], dict[str, lmfit.Parameter]]:
        """Gaussian Guessing."""

        def guess(
            x: npt.NDArray[np.float64], y: npt.NDArray[np.float64]
        ) -> dict[str, lmfit.Parameter]:
            mean = np.sum(x * y) / np.sum(y)
            sigma = np.sqrt(np.sum(y * (x - mean) ** 2) / np.sum(y))
            background = np.min(y)

            if np.max(y) > abs(np.min(y)):
                amp = np.max(y) - background
            else:
                amp = np.min(y) + background

            init_guess = {
                "amp": lmfit.Parameter("amp", amp),
                "sigma": lmfit.Parameter("sigma", sigma, min=0),
                "x0": lmfit.Parameter("x0", mean),
                "background": lmfit.Parameter("background", background),
            }

            return init_guess

        return guess


class Lorentzian(Fit):
    """Lorentzian Fitting."""

    @classmethod
    def model(cls, *args: int) -> lmfit.Model:
        """Lorentzian Model."""

        def model(
            x: npt.NDArray[np.float64], amp: float, sigma: float, center: float, background: float
        ) -> npt.NDArray[np.float64]:
            if sigma == 0:
                sigma = 1

            return amp / (1 + ((x - center) / sigma) ** 2) + background

        return lmfit.Model(model)

    @classmethod
    def guess(
        cls, *args: int
    ) -> Callable[[npt.NDArray[np.float64], npt.NDArray[np.float64]], dict[str, lmfit.Parameter]]:
        """Lorentzian Guessing."""

        def guess(
            x: npt.NDArray[np.float64], y: npt.NDArray[np.float64]
        ) -> dict[str, lmfit.Parameter]:
            background = np.min(y)

            if np.max(y) > abs(np.min(y)):
                amp_index = np.argmax(y)
                amp = y[amp_index] - background

            else:
                amp_index = np.argmin(y)
                amp = y[amp_index] + background

            center = x[amp_index]

            # Guessing. sigma using FWHM

            half_max = amp / 2
            left_side = np.where(x < center)[0]  # x-values left of the peak
            right_side = np.where(x > center)[0]  # x-values right of the peak

            # Left side
            x1_index = (
                left_side[np.argmin(np.abs(y[left_side] - half_max))] if len(left_side) > 0 else 0
            )

            # Right side
            x2_index = (
                right_side[np.argmin(np.abs(y[right_side] - half_max))]
                if len(right_side) > 0
                else -1
            )

            sigma = (x[x2_index] - x[x1_index]) / 2

            init_guess = {
                "amp": lmfit.Parameter("amp", amp),
                "sigma": lmfit.Parameter("sigma", sigma, min=0),
                "center": lmfit.Parameter("center", center),
                "background": lmfit.Parameter("background", background),
            }

            return init_guess

        return guess


class Linear(Fit):
    """Linear Fitting."""

    @classmethod
    def model(cls, *args: int) -> lmfit.Model:
        """Linear Model."""

        def model(x: npt.NDArray[np.float64], c1: float, c0: float) -> npt.NDArray[np.float64]:
            return c1 * x + c0

        return lmfit.Model(model)

    @classmethod
    def guess(
        cls, *args: int
    ) -> Callable[[npt.NDArray[np.float64], npt.NDArray[np.float64]], dict[str, lmfit.Parameter]]:
        """Linear Guessing."""
        return Polynomial.guess(1)


class Polynomial(Fit):
    """Polynomial Fitting."""

    @classmethod
    def _check_degree(cls, args: tuple[int, ...]) -> int:
        """Check that polynomial degree is valid."""
        degree = args[0] if args else 7
        if not (0 <= degree <= 7):
            raise ValueError("The polynomial degree should be at least 0 and smaller than 8.")
        return degree

    @classmethod
    def model(cls, *args: int) -> lmfit.Model:
        """Polynomial Model."""
        degree = cls._check_degree(args)
        return PolynomialModel(degree=degree)

    @classmethod
    def guess(
        cls, *args: int
    ) -> Callable[[npt.NDArray[np.float64], npt.NDArray[np.float64]], dict[str, lmfit.Parameter]]:
        """Polynomial Guessing."""

        def guess(
            x: npt.NDArray[np.float64], y: npt.NDArray[np.float64]
        ) -> dict[str, lmfit.Parameter]:
            init_guess = {}
            degree = cls._check_degree(args)

            coeffs = p.polynomial.polyfit(x, y, degree)

            for i in range(degree + 1):
                init_guess[f"c{i}"] = coeffs[i]

            return init_guess

        return guess


class DampedOsc(Fit):
    """Damped Oscillator Fitting."""

    @classmethod
    def model(cls, *args: int) -> lmfit.Model:
        """Damped Oscillator Model."""

        def model(
            x: npt.NDArray[np.float64], center: float, amp: float, freq: float, width: float
        ) -> npt.NDArray[np.float64]:
            return amp * np.cos((x - center) * freq) * np.exp(-(((x - center) / width) ** 2))

        return lmfit.Model(model)

    @classmethod
    def guess(
        cls, *args: int
    ) -> Callable[[npt.NDArray[np.float64], npt.NDArray[np.float64]], dict[str, lmfit.Parameter]]:
        """Damped Oscillator Guessing."""

        def guess(
            x: npt.NDArray[np.float64], y: npt.NDArray[np.float64]
        ) -> dict[str, lmfit.Parameter]:
            peak = x[np.argmax(y)]
            valley = x[np.argmin(y)]

            init_guess = {
                "center": lmfit.Parameter("center", peak),
                "amp": lmfit.Parameter("amp", np.max(y)),
                "freq": lmfit.Parameter("freq", np.pi / np.abs(peak - valley)),
                "width": lmfit.Parameter("width", max(x) - min(x)),
            }

            return init_guess

        return guess


class SlitScan(Fit):
    """Slit Scan Fitting."""

    @classmethod
    def _check_input(cls, args: tuple[int, ...]) -> int:
        """Check that provided maximum slit size is atleast 0."""
        max_slit_gap = args[0] if args else 1
        if not (0 <= max_slit_gap):
            raise ValueError("The slit gap should be atleast 0.")
        return max_slit_gap

    @classmethod
    def model(cls, *args: int) -> lmfit.Model:
        """Slit Scan Model."""

        def model(
            x: npt.NDArray[np.float64],
            background: float,
            inflection0: float,
            gradient: float,
            inflections_diff: float,
            height_above_inflection1: float,
        ) -> npt.NDArray[np.float64]:
            linear_seg = background + gradient * (x - inflection0)

            if height_above_inflection1 == 0:
                exp_seg = gradient * inflections_diff + background
            else:
                exp_seg = (
                    height_above_inflection1
                    * scipy.special.erf(
                        gradient
                        * (np.sqrt(np.pi) / (2 * height_above_inflection1))
                        * (x - inflection0 - inflections_diff)
                    )
                    + gradient * inflections_diff
                    + background
                )

            linear_seg = np.maximum(linear_seg, background)
            exp_seg = np.maximum(exp_seg, background)

            y = np.minimum(linear_seg, exp_seg)

            return y

        return lmfit.Model(model)

    @classmethod
    def guess(
        cls, *args: int
    ) -> Callable[[npt.NDArray[np.float64], npt.NDArray[np.float64]], dict[str, lmfit.Parameter]]:
        """Slit Scan Guessing."""

        def guess(
            x: npt.NDArray[np.float64], y: npt.NDArray[np.float64]
        ) -> dict[str, lmfit.Parameter]:
            max_slit_size = cls._check_input(args)

            # Guessing. gradient of linear-slope part of function
            dy = np.gradient(y)  # Return array of differences in y
            max_dy = np.max(dy)  # Return max y difference, this will always be on the upwards slope
            dx = abs(x[1] - x[0])  # Find x step
            gradient = max_dy / dx

            d2y = np.diff(dy)  # Double differentiate y to find how gradients change
            inflection0 = x[np.argmax(d2y)]  # Where there is positive gradient change

            background = min(y)  # The lowest y value is the background
            if gradient != 0.0:
                inflections_diff = -(background - y[np.argmax(y)]) / gradient
            else:
                inflections_diff = dx  # Fallback case, guess one x step
            # As linear, using y - y1 = m(x - x1) -> x = (y - y1) / gradient - x1

            # The highest y value + slightly more to account for further convergence
            # - y distance travelled from inflection0 to inflection1
            height_above_inflection1 = np.max(y) + (y[-1] - y[-2]) - (gradient * inflections_diff)

            init_guess = {
                "background": lmfit.Parameter("background", background),
                "inflection0": lmfit.Parameter("inflection0", inflection0),
                "gradient": lmfit.Parameter("gradient", gradient, min=0),
                "inflections_diff": lmfit.Parameter(
                    "inflections_diff", inflections_diff, min=max_slit_size
                ),
                "height_above_inflection1": lmfit.Parameter(
                    "height_above_inflection1", height_above_inflection1, min=0
                ),
            }

            return init_guess

        return guess


class ERF(Fit):
    """Error Function Fitting."""

    @classmethod
    def model(cls, *args: int) -> lmfit.Model:
        """Error Function Model."""

        def model(
            x: npt.NDArray[np.float64], cen: float, stretch: float, scale: float, background: float
        ) -> npt.NDArray[np.float64]:
            return background + scale * scipy.special.erf(stretch * (x - cen))

        return lmfit.Model(model)

    @classmethod
    def guess(
        cls, *args: int
    ) -> Callable[[npt.NDArray[np.float64], npt.NDArray[np.float64]], dict[str, lmfit.Parameter]]:
        """Error Function Guessing."""

        def guess(
            x: npt.NDArray[np.float64], y: npt.NDArray[np.float64]
        ) -> dict[str, lmfit.Parameter]:
            init_guess = {
                "cen": lmfit.Parameter("cen", np.mean(x)),
                "stretch": lmfit.Parameter("stretch", (max(x) - min(x)) / 2),
                "scale": lmfit.Parameter("scale", (max(y) - min(y)) / 2),
                "background": lmfit.Parameter("background", np.mean(y)),
            }

            return init_guess

        return guess


class ERFC(Fit):
    """Complementary Error Function Fitting."""

    @classmethod
    def model(cls, *args: int) -> lmfit.Model:
        """Complementary Error Function Model."""

        def model(
            x: npt.NDArray[np.float64], cen: float, stretch: float, scale: float, background: float
        ) -> npt.NDArray[np.float64]:
            return background + scale * scipy.special.erfc(stretch * (x - cen))

        return lmfit.Model(model)

    @classmethod
    def guess(
        cls, *args: int
    ) -> Callable[[npt.NDArray[np.float64], npt.NDArray[np.float64]], dict[str, lmfit.Parameter]]:
        """Complementary Error Function Guessing."""

        def guess(
            x: npt.NDArray[np.float64], y: npt.NDArray[np.float64]
        ) -> dict[str, lmfit.Parameter]:
            init_guess = {
                "cen": lmfit.Parameter("cen", np.mean(x)),
                "stretch": lmfit.Parameter("stretch", (max(x) - min(x)) / 2),
                "scale": lmfit.Parameter("scale", (max(y) - min(y)) / 2),
                "background": lmfit.Parameter("background", np.min(y)),
            }

            return init_guess

        return guess


class TopHat(Fit):
    """Top Hat Fitting."""

    @classmethod
    def model(cls, *args: int) -> lmfit.Model:
        """Top Hat Model."""

        def model(
            x: npt.NDArray[np.float64], cen: float, width: float, height: float, background: float
        ) -> npt.NDArray[np.float64]:
            y = x * 0
            y[np.abs(x - cen) < width / 2] = height
            return background + y

        return lmfit.Model(model)

    @classmethod
    def guess(
        cls, *args: int
    ) -> Callable[[npt.NDArray[np.float64], npt.NDArray[np.float64]], dict[str, lmfit.Parameter]]:
        """Top Hat Guessing."""

        def guess(
            x: npt.NDArray[np.float64], y: npt.NDArray[np.float64]
        ) -> dict[str, lmfit.Parameter]:
            top = np.where(y > np.mean(y))[0]
            # Guess that any value above the mean is the top part

            if len(top) > 0:
                width = x[np.max(top)] - x[np.min(top)]
            else:
                width = (max(x) - min(x)) / 2

            init_guess = {
                "cen": lmfit.Parameter("cen", np.mean(x)),
                "width": lmfit.Parameter("width", width),
                "height": lmfit.Parameter("height", (max(y) - min(y))),
                "background": lmfit.Parameter("background", min(y)),
            }

            return init_guess

        return guess


class Trapezoid(Fit):
    """Trapezoid Fitting."""

    @classmethod
    def model(cls, *args: int) -> lmfit.Model:
        """Trapezoid Model."""

        def model(
            x: npt.NDArray[np.float64],
            cen: float,
            gradient: float,
            height: float,
            background: float,
            y_offset: float,  # Acts as a width multiplier
        ) -> npt.NDArray[np.float64]:
            y = y_offset + height + background - gradient * np.abs(x - cen)
            y = np.maximum(y, background)
            y = np.minimum(y, background + height)
            return y

        return lmfit.Model(model)

    @classmethod
    def guess(
        cls, *args: int
    ) -> Callable[[npt.NDArray[np.float64], npt.NDArray[np.float64]], dict[str, lmfit.Parameter]]:
        """Trapezoid Guessing."""

        def guess(
            x: npt.NDArray[np.float64], y: npt.NDArray[np.float64]
        ) -> dict[str, lmfit.Parameter]:
            top = np.where(y > np.mean(y))[0]
            # Guess that any value above the y mean is the top part

            cen = np.mean(x)
            background = np.min(y)
            height = np.max(y) - background

            if top.size > 0:
                i = np.min(top)
                x1 = x[i]  # x1 is the left of the top part
            else:
                width_top = (np.max(x) - np.min(x)) / 2
                x1 = cen - width_top / 2

            x0 = 0.5 * (np.min(x) + x1)  # Guess that x0 is half way between min(x) and x1

            if height == 0.0:
                gradient = 0.0
            else:
                gradient = height / (x1 - x0)

            y_intercept0 = np.max(y) - gradient * x1  # To find the slope function
            y_tip = gradient * cen + y_intercept0
            y_offset = y_tip - height - background

            init_guess = {
                "cen": lmfit.Parameter("cen", cen),
                "gradient": lmfit.Parameter("gradient", gradient, min=0),
                "height": lmfit.Parameter("height", height, min=0),
                "background": lmfit.Parameter("background", background),
                "y_offset": lmfit.Parameter("y_offset", y_offset, min=0),
            }

            return init_guess

        return guess

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
    @classmethod
    @abstractmethod
    def model(cls, *args: int) -> lmfit.Model:
        pass

    @classmethod
    @abstractmethod
    def guess(
        cls, *args: int
    ) -> Callable[[npt.NDArray[np.float64], npt.NDArray[np.float64]], dict[str, lmfit.Parameter]]:
        pass

    @classmethod
    def fit(cls, *args: int) -> FitMethod:
        return FitMethod(model=cls.model(*args), guess=cls.guess(*args))


class Gaussian(Fit):
    @classmethod
    def model(cls, *args: int) -> lmfit.Model:
        def model(
            x: npt.NDArray[np.float_], amp: float, sigma: float, x0: float, background: float
        ) -> npt.NDArray[np.float_]:
            if sigma == 0:
                sigma = 1

            return amp * np.exp(-((x - x0) ** 2) / (2 * sigma**2)) + background

        return lmfit.Model(model)

    @classmethod
    def guess(
        cls, *args: int
    ) -> Callable[[npt.NDArray[np.float64], npt.NDArray[np.float64]], dict[str, lmfit.Parameter]]:
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

            if sigma == 0:
                sigma = 1

            init_guess = {
                "amp": lmfit.Parameter("A", amp),
                "sigma": lmfit.Parameter("sigma", sigma, min=0),
                "x0": lmfit.Parameter("x0", mean),
                "background": lmfit.Parameter("background", background),
            }

            return init_guess

        return guess


class Lorentzian(Fit):
    @classmethod
    def model(cls, *args: int) -> lmfit.Model:
        def model(
            x: npt.NDArray[np.float_], amp: float, sigma: float, center: float, background: float
        ) -> npt.NDArray[np.float_]:
            if sigma == 0:
                sigma = 1

            return amp / (1 + ((x - center) / sigma) ** 2) + background

        return lmfit.Model(model)

    @classmethod
    def guess(
        cls, *args: int
    ) -> Callable[[npt.NDArray[np.float64], npt.NDArray[np.float64]], dict[str, lmfit.Parameter]]:
        def guess(
            x: npt.NDArray[np.float64], y: npt.NDArray[np.float64]
        ) -> dict[str, lmfit.Parameter]:
            background = np.min(y)

            if np.max(y) > abs(np.min(y)):
                amp_index = np.argmax(y)
                amp = y[amp_index] - background

            else:
                amp_index = np.argmin(y)
                amp = y[amp_index] + -background

            center = x[amp_index]

            # Guessing sigma using FWHM

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
            if sigma == 0:
                sigma = 1

            init_guess = {
                "amp": lmfit.Parameter("A", amp),
                "sigma": lmfit.Parameter("sigma", sigma, min=0),
                "center": lmfit.Parameter("center", center),
                "background": lmfit.Parameter("background", background),
            }

            return init_guess

        return guess


class Linear(Fit):
    @classmethod
    def model(cls, *args: int) -> lmfit.Model:
        def model(x: npt.NDArray[np.float_], m: float, c: float) -> npt.NDArray[np.float_]:
            return m * x + c

        return lmfit.Model(model)

    @classmethod
    def guess(
        cls, *args: int
    ) -> Callable[[npt.NDArray[np.float64], npt.NDArray[np.float64]], dict[str, lmfit.Parameter]]:
        def guess(
            x: npt.NDArray[np.float64], y: npt.NDArray[np.float64]
        ) -> dict[str, lmfit.Parameter]:
            # Linear Regression
            numerator = sum(x * y) - sum(x) * sum(y)
            denominator = sum(x**2) - sum(x) ** 2

            m = numerator / denominator
            c = (sum(y) - m * sum(x)) / len(x)

            init_guess = {
                "m": lmfit.Parameter("m", m),
                "c": lmfit.Parameter("c", c),
            }

            return init_guess

        return guess


class Polynomial(Fit):
    @classmethod
    def _check_degree(cls, args: tuple[int, ...]) -> int:
        degree = args[0] if args else 7
        if not (0 <= degree <= 7):
            raise ValueError("The polynomial degree should be at least 0 and smaller than 8.")
        return degree

    @classmethod
    def model(cls, *args: int) -> lmfit.Model:
        degree = cls._check_degree(args)
        return PolynomialModel(degree=degree)

    @classmethod
    def guess(
        cls, *args: int
    ) -> Callable[[npt.NDArray[np.float64], npt.NDArray[np.float64]], dict[str, lmfit.Parameter]]:
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
    @classmethod
    def model(cls, *args: int) -> lmfit.Model:
        def model(
            x: npt.NDArray[np.float_], center: float, amp: float, freq: float, width: float
        ) -> npt.NDArray[np.float_]:
            return amp * np.cos((x - center) * freq) * np.exp(-(((x - center) / width) ** 2))

        return lmfit.Model(model)

    @classmethod
    def guess(
        cls, *args: int
    ) -> Callable[[npt.NDArray[np.float64], npt.NDArray[np.float64]], dict[str, lmfit.Parameter]]:
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
    @classmethod
    def _check_input(cls, args: tuple[int, ...]) -> int:
        max_slit_gap = args[0] if args else 1
        if not (0 <= max_slit_gap):
            raise ValueError("The slit gap should be atleast 0.")
        return max_slit_gap

    @classmethod
    def _check_params(
        cls,
        background: float,
        inflection_1: float,
        gradient: float,
        inflection_2: float,
        asymptote: float,
    ) -> float:
        if gradient < 0:
            return 0

        elif inflection_2 <= inflection_1:
            return 0

        baseline = gradient * (inflection_2 - inflection_1) + background - asymptote
        # What y value should the function start from

        if baseline >= 0:
            return 0

        return baseline

    @classmethod
    def model(cls, *args: int) -> lmfit.Model:
        def model(
            x: npt.NDArray[np.float_],
            background: float,
            inflection_1: float,
            gradient: float,
            inflection_2: float,
            asymptote: float,
        ) -> npt.NDArray[np.float_]:
            baseline = cls._check_params(
                background, inflection_1, gradient, inflection_2, asymptote
            )

            y = np.zeros_like(x)

            if baseline == 0:
                y.fill(background)
                return y

            for i, xi in enumerate(x):
                if xi <= inflection_1:  # Flat part before inflection_1
                    y[i] = background

                elif (
                    inflection_1 < xi <= inflection_2
                ):  # Sloped linear part between inflection_1 and inflection_2
                    y[i] = gradient * (xi - inflection_1) + background

                elif xi > inflection_2:  # Curved part converging to a y value after inflection_2
                    y[i] = asymptote + baseline * np.e ** (
                        (gradient / baseline) * (xi - inflection_2)
                    )

            return y

        return lmfit.Model(model)

    @classmethod
    def guess(
        cls, *args: int
    ) -> Callable[[npt.NDArray[np.float64], npt.NDArray[np.float64]], dict[str, lmfit.Parameter]]:
        def guess(
            x: npt.NDArray[np.float64], y: npt.NDArray[np.float64]
        ) -> dict[str, lmfit.Parameter]:
            max_slit_size = cls._check_input(args)

            # Guessing gradient of linear-slope part of function
            dy = np.gradient(y)  # Return array of differences in y
            max_dy = np.max(dy)  # Return max y difference, this will always be on the upwards slope
            dx = x[1] - x[0]  # Find x step
            gradient = max_dy / dx

            d2y = np.diff(dy)  # Double differentiate y to find how gradients change
            inflection_2x = x[
                np.argmin(d2y)
            ]  # Where there is negative gradient change ~ inflection pt2

            background = min(y)  # The lowest y value is the background
            inflection_1x = inflection_2x + (background - y[np.argmax(y)]) / gradient
            # As linear, using y - y1 = m(x - x1) -> x = (y - y1) / gradient - x1
            # To find inflection pt1

            # The highest y value + slightly more to account for further convergence
            asymptote = np.max(y) + (y[-1] - y[-2])

            baseline = cls._check_params(
                background, inflection_1x, gradient, inflection_2x, asymptote
            )  # Check that params produce a value function output

            if baseline == 0:
                return {
                    "background": lmfit.Parameter("background", 0),
                    "inflection_1": lmfit.Parameter("inflection_1", 1),
                    "gradient": lmfit.Parameter("gradient", 1),
                    "inflection_2": lmfit.Parameter("inflection_2", 10),
                    "asymptote": lmfit.Parameter("asymptote", 11),
                }

            return {
                "background": lmfit.Parameter("background", background),
                "inflection_1": lmfit.Parameter("inflection_1", inflection_1x),
                "gradient": lmfit.Parameter("gradient", gradient),
                "inflection_2": lmfit.Parameter(
                    "inflection_2", inflection_2x, min=inflection_1x + max_slit_size
                ),
                "asymptote": lmfit.Parameter("asymptote", asymptote),
            }

        return guess


class ERF(Fit):
    @classmethod
    def model(cls, *args: int) -> lmfit.Model:
        def model(
            x: npt.NDArray[np.float_], cen: float, stretch: float, scale: float, background: float
        ) -> npt.NDArray[np.float_]:
            return background + scale * scipy.special.erf(stretch * (x - cen))

        return lmfit.Model(model)

    @classmethod
    def guess(
        cls, *args: int
    ) -> Callable[[npt.NDArray[np.float64], npt.NDArray[np.float64]], dict[str, lmfit.Parameter]]:
        def guess(
            x: npt.NDArray[np.float64], y: npt.NDArray[np.float64]
        ) -> dict[str, lmfit.Parameter]:
            init_guess = {
                "cen": lmfit.Parameter("cen", np.mean(x)),
                "stretch": lmfit.Parameter("stretch", (max(x) - min(x)) / 2),
                "scale": lmfit.Parameter("scale", (max(y) - min(y)) / 2),
                "background": lmfit.Parameter("background", min(y)),
            }

            return init_guess

        return guess


class ERFC(Fit):
    @classmethod
    def model(cls, *args: int) -> lmfit.Model:
        def model(
            x: npt.NDArray[np.float_], cen: float, stretch: float, scale: float, background: float
        ) -> npt.NDArray[np.float_]:
            return background + scale * scipy.special.erfc(stretch * (x - cen))

        return lmfit.Model(model)

    @classmethod
    def guess(
        cls, *args: int
    ) -> Callable[[npt.NDArray[np.float64], npt.NDArray[np.float64]], dict[str, lmfit.Parameter]]:
        def guess(
            x: npt.NDArray[np.float64], y: npt.NDArray[np.float64]
        ) -> dict[str, lmfit.Parameter]:
            init_guess = {
                "cen": lmfit.Parameter("cen", np.mean(x)),
                "stretch": lmfit.Parameter("stretch", (max(x) - min(x)) / 2),
                "scale": lmfit.Parameter("scale", (max(y) - min(y)) / 2),
                "background": lmfit.Parameter("background", min(y)),
            }

            return init_guess

        return guess


class TopHat(Fit):
    @classmethod
    def model(cls, *args: int) -> lmfit.Model:
        def model(
            x: npt.NDArray[np.float_], cen: float, width: float, height: float, background: float
        ) -> npt.NDArray[np.float_]:
            y = x * 0
            y[np.abs(x - cen) < width / 2] = height
            return background + y

        return lmfit.Model(model)

    @classmethod
    def guess(
        cls, *args: int
    ) -> Callable[[npt.NDArray[np.float64], npt.NDArray[np.float64]], dict[str, lmfit.Parameter]]:
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
    @classmethod
    def model(cls, *args: int) -> lmfit.Model:
        def model(
            x: npt.NDArray[np.float_],
            cen: float,
            gradient: float,
            height: float,
            background: float,
            y_offset: float,
        ) -> npt.NDArray[np.float_]:
            y = y_offset + height + background - gradient * np.abs(x - cen)
            y = np.maximum(y, background)
            y = np.minimum(y, background + height)
            return y

        return lmfit.Model(model)

    @classmethod
    def guess(
        cls, *args: int
    ) -> Callable[[npt.NDArray[np.float64], npt.NDArray[np.float64]], dict[str, lmfit.Parameter]]:
        def guess(
            x: npt.NDArray[np.float64], y: npt.NDArray[np.float64]
        ) -> dict[str, lmfit.Parameter]:
            top = np.where(y > np.mean(y))[0]
            # Guess that any value above the y mean is the top part

            cen = np.mean(x)
            height = max(y) - min(y)
            background = min(y)

            if len(top) > 0:
                x1 = x[np.min(top)]  # x1 is the left of the top part
            else:
                width_top = (max(x) - min(x)) / 2
                x1 = cen - width_top / 2

            x0 = 0.5 * (np.min(x) + x1)  # Guess that x0 is half way between min(x) and x1

            gradient = (x1 - x0) / height

            y_intercept0 = background - gradient * x0  # To find the slope function
            y_tip = gradient * cen + y_intercept0
            y_offset = y_tip - height

            init_guess = {
                "cen": lmfit.Parameter("cen", cen),
                "gradient": lmfit.Parameter("gradient", gradient, min=0),
                "height": lmfit.Parameter("height", height, min=0),
                "background": lmfit.Parameter("background", background),
                "y_offset": lmfit.Parameter("y_offset", y_offset, min=0),
            }

            return init_guess

        return guess

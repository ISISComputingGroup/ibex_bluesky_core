from abc import ABC, abstractmethod
from typing import Callable

import lmfit
import numpy as np
import numpy.typing as npt
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
            x: npt.NDArray[np.float_], amp: float, sigma: float, x0: float
        ) -> npt.NDArray[np.float_]:
            if sigma == 0:
                sigma = 1

            return amp * np.exp(-((x - x0) ** 2) / (2 * sigma**2))

        return lmfit.Model(model)

    @classmethod
    def guess(
        cls, *args: int
    ) -> Callable[[npt.NDArray[np.float64], npt.NDArray[np.float64]], dict[str, lmfit.Parameter]]:
        def guess(
            x: npt.NDArray[np.float64], y: npt.NDArray[np.float64]
        ) -> dict[str, lmfit.Parameter]:
            if len(y) == 0:  # No data so guessing standard gaussian
                return {
                    "amp": lmfit.Parameter("A", 1),
                    "sigma": lmfit.Parameter("sigma", x.mean(), min=0),
                    "x0": lmfit.Parameter("x0", 0),
                }

            amp = np.max(y) if np.max(y) > abs(np.min(y)) else np.min(y)
            mean = np.sum(x * y) / np.sum(y)
            sigma = np.sqrt(np.sum(y * (x - mean) ** 2) / np.sum(y))

            if sigma == 0:
                sigma = 1

            init_guess = {
                "amp": lmfit.Parameter("A", amp),
                "sigma": lmfit.Parameter("sigma", sigma, min=0),
                "x0": lmfit.Parameter("x0", mean),
            }

            return init_guess

        return guess


class Lorentzian(Fit):
    @classmethod
    def model(cls, *args: int) -> lmfit.Model:
        def model(
            x: npt.NDArray[np.float_], amp: float, sigma: float, center: float
        ) -> npt.NDArray[np.float_]:
            if sigma == 0:
                sigma = 1

            return amp / (1 + ((x - center) / sigma) ** 2)

        return lmfit.Model(model)

    @classmethod
    def guess(
        cls, *args: int
    ) -> Callable[[npt.NDArray[np.float64], npt.NDArray[np.float64]], dict[str, lmfit.Parameter]]:
        def guess(
            x: npt.NDArray[np.float64], y: npt.NDArray[np.float64]
        ) -> dict[str, lmfit.Parameter]:
            if len(y) == 0:  # No data so guessing standard lorentzian
                return {
                    "amp": lmfit.Parameter("A", 1),
                    "sigma": lmfit.Parameter("sigma", 1, min=0),
                    "center": lmfit.Parameter("center", 0),
                }

            amp_index = np.argmax(y) if np.max(y) > abs(np.min(y)) else np.argmin(y)
            amp = y[amp_index]
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
            if len(y) == 0:  # No data so guessing standard DampedOsc
                return {
                    "center": lmfit.Parameter("center", 0),
                    "amp": lmfit.Parameter("amp", 1),
                    "freq": lmfit.Parameter("freq", 2 * np.pi),
                    "width": lmfit.Parameter("width", 1),
                }

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
            
            baseline = cls._check_params(background, inflection_1, gradient, inflection_2, asymptote)

            y = np.zeros_like(x)

            if baseline == 0:
                y.fill(background)
                return y

            for i, xi in enumerate(x):
                if xi <= inflection_1: # Flat part before inflection_1
                    y[i] = background

                elif inflection_1 < xi <= inflection_2: # Sloped linear part between inflection_1 and inflection_2
                    y[i] = gradient * (xi - inflection_1) + background

                elif xi > inflection_2: # Curved part converging to a y value after inflection_2
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
            dy = np.gradient(y) # Return array of differences in y
            max_dy = np.max(dy) # Return max y difference, this will always be on the upwards slope
            dx = x[1] - x[0] # Find x step 
            gradient = max_dy / dx

            d2y = np.diff(dy) # Double differentiate y to find how gradients change
            inflection_2x = x[np.argmin(d2y)] # Where there is negative gradient change ~ inflection pt2

            background = min(y) # The lowest y value is the background
            inflection_1x = inflection_2x + (background - y[np.argmax(y)]) / gradient
            # As linear, using y - y1 = m(x - x1) -> x = (y - y1) / gradient - x1
            # To find inflection pt1

            # The highest y value + slightly more to account for further convergence
            asymptote = np.max(y) + (y[-1] - y[-2])

            baseline = cls._check_params(
                background, inflection_1x, gradient, inflection_2x, asymptote
            ) # Check that params produce a value function output

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
                "inflection_2": lmfit.Parameter("inflection_2", inflection_2x, min=inflection_1x + max_slit_size),
                "asymptote": lmfit.Parameter("asymptote", np.max(y) + (y[-1] - y[-2])),
            }

        return guess

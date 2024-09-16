from abc import ABC, abstractmethod
from typing import Callable

import lmfit
import numpy as np
import numpy.typing as npt
from lmfit.models import PolynomialModel, DampedOscillatorModel
from numpy import polynomial as p
from scipy.signal import find_peaks

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
    ) -> Callable[[npt.NDArray[np.float_], npt.NDArray[np.float_]], dict[str, lmfit.Parameter]]:
        pass

    @classmethod
    def fit(cls, *args: int) -> FitMethod:
        return FitMethod(model=cls.model(*args), guess=cls.guess(*args))


class Gaussian(Fit):
    @classmethod
    def model(cls, *args: int) -> lmfit.Model:
        def model(x: float, amp: float, sigma: float, x0: float) -> float:
            if sigma == 0:
                return 0

            return amp * np.exp(-((x - x0) ** 2) / (2 * sigma**2))

        return lmfit.Model(model)

    @classmethod
    def guess(
        cls, *args: int
    ) -> Callable[[npt.NDArray[np.float_], npt.NDArray[np.float_]], dict[str, lmfit.Parameter]]:
        def guess(
            x: npt.NDArray[np.float_], y: npt.NDArray[np.float_]
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
        def model(x: float, amp: float, sigma: float, center: float) -> float:
            if sigma == 0:
                return 0

            return amp / (1 + ((x - center) / sigma) ** 2)

        return lmfit.Model(model)

    @classmethod
    def guess(
        cls, *args: int
    ) -> Callable[[npt.NDArray[np.float_], npt.NDArray[np.float_]], dict[str, lmfit.Parameter]]:
        def guess(
            x: npt.NDArray[np.float_], y: npt.NDArray[np.float_]
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
                left_side[np.argmin(np.abs(y[left_side] - half_max))]
                if len(left_side) > 0
                else 0
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
        def model(x: float, m: float, c: float) -> float:
            return m * x + c

        return lmfit.Model(model)

    @classmethod
    def guess(
        cls, *args: int
    ) -> Callable[[npt.NDArray[np.float_], npt.NDArray[np.float_]], dict[str, lmfit.Parameter]]:
        def guess(
            x: npt.NDArray[np.float_], y: npt.NDArray[np.float_]
        ) -> dict[str, lmfit.Parameter]:
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
    ) -> Callable[[npt.NDArray[np.float_], npt.NDArray[np.float_]], dict[str, lmfit.Parameter]]:
        def guess(
            x: npt.NDArray[np.float_], y: npt.NDArray[np.float_]
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

        def model(x: float, center: float, amp: float, freq: float, width: float):
            return amp * np.cos((x - center) * freq) * \
                np.exp(-((x - center) / width)**2)
        
        return lmfit.Model(model)

    @classmethod
    def guess(
        cls, *args: int
    ) -> Callable[[npt.NDArray[np.float_], npt.NDArray[np.float_]], dict[str, lmfit.Parameter]]:
        def guess(
            x: npt.NDArray[np.float_], y: npt.NDArray[np.float_]
        ) -> dict[str, lmfit.Parameter]:

            if len(y) == 0:  # No data so guessing standard DampedOsc
                return {
                    "center": lmfit.Parameter("center",0),
                    "amp": lmfit.Parameter("amp",1),
                    "freq": lmfit.Parameter("freq", 2 * np.pi),
                    "width": lmfit.Parameter("width",1) 
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
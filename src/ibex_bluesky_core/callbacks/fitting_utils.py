from abc import ABC, abstractmethod
from typing import Callable

import lmfit
import numpy as np
import numpy.typing as npt

from ibex_bluesky_core.callbacks.fitting import ModelAndGuess


class Model(ABC):
    @classmethod
    @abstractmethod
    def model(cls) -> lmfit.Model:
        pass

    @classmethod
    @abstractmethod
    def guess(
        cls,
    ) -> Callable[[npt.NDArray[np.float_], npt.NDArray[np.float_]], dict[str, lmfit.Parameter]]:
        pass

    @classmethod
    def fit(cls) -> ModelAndGuess:
        return ModelAndGuess(model=cls.model(), guess=cls.guess())


class Gaussian(Model):
    @classmethod
    def model(cls) -> lmfit.Model:
        def model(x: float, amp: float, sigma: float, x0: float) -> float:
            if sigma == 0:
                return 0

            return amp * np.exp(-((x - x0) ** 2) / (2 * sigma**2))

        return lmfit.Model(model)

    @classmethod
    def guess(
        cls,
    ) -> Callable[[npt.NDArray[np.float_], npt.NDArray[np.float_]], dict[str, lmfit.Parameter]]:
        def guess(
            x: npt.NDArray[np.float_], y: npt.NDArray[np.float_]
        ) -> dict[str, lmfit.Parameter]:
            if np.sum(y) == 0:  # No data so guessing standard gaussian
                return {
                    "amp": lmfit.Parameter("A", 1),
                    "sigma": lmfit.Parameter("sigma", x.mean(), min=0),
                    "x0": lmfit.Parameter("x0", 0),
                }

            mean = np.sum(x * y) / np.sum(y)
            sigma = np.sqrt(np.sum(y * (x - mean) ** 2) / np.sum(y))

            if sigma == 0:
                sigma = 1

            amp = np.max(y) - np.min(y)

            init_guess = {
                "amp": lmfit.Parameter("A", amp),
                "sigma": lmfit.Parameter("sigma", sigma, min=0),
                "x0": lmfit.Parameter("x0", mean),
            }

            return init_guess

        return guess


class Linear(Model):
    @classmethod
    def model(cls) -> lmfit.Model:
        def model(x: float, m: float, c: float) -> float:
            return m * x + c

        return lmfit.Model(model)

    @classmethod
    def guess(
        cls,
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

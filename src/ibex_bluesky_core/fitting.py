"""Fitting methods used by the LiveFit callback."""

import math
from abc import ABC, abstractmethod
from collections.abc import Callable

import lmfit
import numpy as np
from lmfit.models import PolynomialModel
from numpy import typing as npt
from scipy.special import erf, erfc, erfcinv, erfinv

__all__ = [
    "ERF",
    "ERFC",
    "DampedOsc",
    "Fit",
    "FitMethod",
    "Gaussian",
    "Linear",
    "Lorentzian",
    "MuonMomentum",
    "NegativeTrapezoid",
    "Polynomial",
    "SlitScan",
    "TopHat",
    "Trapezoid",
]

from ibex_bluesky_core.utils import center_of_mass_of_area_under_curve


class FitMethod:
    """Tell LiveFit how to fit to a scan. Has a Model function and a Guess function.

    Model - Takes x values and a set of parameters to return y values.
    Guess - Takes x and y values and returns a rough 'guess' of the original parameters.
    """

    model: lmfit.Model
    guess: Callable[[npt.NDArray[np.float64], npt.NDArray[np.float64]], dict[str, lmfit.Parameter]]

    def __init__(
        self,
        model: lmfit.Model | Callable[[npt.NDArray[np.float64]], npt.NDArray[np.float64]],
        guess: Callable[
            [npt.NDArray[np.float64], npt.NDArray[np.float64]], dict[str, lmfit.Parameter]
        ],
    ) -> None:
        """Tell :py:obj:`~ibex_bluesky_core.callbacks.LiveFit` how to fit to data points.

        Contains a model function and a guess function.

        Args:
            model (lmfit.Model | Callable): The model function to use.
            guess (Callable): The guess function to use.

        """
        self.guess = guess

        if callable(model):
            self.model = lmfit.Model(model)
        else:
            self.model = model


class Fit(ABC):
    """Base class for all fits."""

    equation: str = ""

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

    @classmethod
    def fit(cls, *args: int) -> FitMethod:
        """Return a FitMethod given model and guess functions to pass to LiveFit."""
        return FitMethod(model=cls.model(*args), guess=cls.guess(*args))


def _guess_cen_and_width(
    x: npt.NDArray[np.float64], y: npt.NDArray[np.float64]
) -> tuple[float, float]:
    """Guess the center and width of a positive peak."""
    com, total_area = center_of_mass_of_area_under_curve(x, y)
    y_range = np.max(y) - np.min(y)
    if y_range == 0.0:
        width = (np.max(x) - np.min(x)) / 2
    else:
        width = total_area / y_range
    return com, width


class Gaussian(Fit):
    """Gaussian Fitting.

    See Also:
        :ref:`fit_gaussian` model and parameter descriptions

    """

    equation = "amp * exp(-((x - x0) ** 2) / (2 * sigma**2)) + background"

    @classmethod
    def model(cls, *args: int) -> lmfit.Model:
        """Gaussian Model.

        :meta private:
        """

        def model(
            x: npt.NDArray[np.float64], amp: float, sigma: float, x0: float, background: float
        ) -> npt.NDArray[np.float64]:
            if sigma == 0:
                sigma = 1

            return amp * np.exp(-((x - x0) ** 2) / (2 * sigma**2)) + background

        return lmfit.Model(model, name=f"{cls.__name__}  [{cls.equation}]")

    @classmethod
    def guess(
        cls, *args: int
    ) -> Callable[[npt.NDArray[np.float64], npt.NDArray[np.float64]], dict[str, lmfit.Parameter]]:
        """Gaussian Guessing.

        :meta private:
        """

        def guess(
            x: npt.NDArray[np.float64], y: npt.NDArray[np.float64]
        ) -> dict[str, lmfit.Parameter]:
            cen, width = _guess_cen_and_width(x, y)
            sigma = width / math.sqrt(2 * math.pi)  # From expected area under gaussian

            background = np.min(y)

            if np.max(y) > abs(np.min(y)):
                amp = np.max(y) - background
            else:
                amp = np.min(y) + background

            init_guess = {
                "amp": lmfit.Parameter("amp", amp),
                "sigma": lmfit.Parameter("sigma", sigma, min=0),
                "x0": lmfit.Parameter("x0", cen),
                "background": lmfit.Parameter("background", background),
            }

            return init_guess

        return guess


class Lorentzian(Fit):
    """Lorentzian Fitting.

    See Also:
        :ref:`fit_lorentzian` model and parameter descriptions

    """

    equation = "amp / (1 + ((x - center) / sigma) ** 2) + background"

    @classmethod
    def model(cls, *args: int) -> lmfit.Model:
        """Lorentzian Model.

        :meta private:
        """

        def model(
            x: npt.NDArray[np.float64], amp: float, sigma: float, center: float, background: float
        ) -> npt.NDArray[np.float64]:
            if sigma == 0:
                sigma = 1

            return amp / (1 + ((x - center) / sigma) ** 2) + background

        return lmfit.Model(model, name=f"{cls.__name__}  [{cls.equation}]")

    @classmethod
    def guess(
        cls, *args: int
    ) -> Callable[[npt.NDArray[np.float64], npt.NDArray[np.float64]], dict[str, lmfit.Parameter]]:
        """Lorentzian Guessing.

        :meta private:
        """

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
    """Linear Fitting.

    See Also:
        :ref:`fit_linear` model and parameter descriptions

    """

    equation = "c1 * x + c0"

    @classmethod
    def model(cls, *args: int) -> lmfit.Model:
        """Linear Model.

        :meta private:
        """

        def model(x: npt.NDArray[np.float64], c1: float, c0: float) -> npt.NDArray[np.float64]:
            return c1 * x + c0

        return lmfit.Model(model, name=f"{cls.__name__}  [{cls.equation}]")

    @classmethod
    def guess(
        cls, *args: int
    ) -> Callable[[npt.NDArray[np.float64], npt.NDArray[np.float64]], dict[str, lmfit.Parameter]]:
        """Linear Guessing.

        :meta private:
        """
        return Polynomial.guess(1)


class Polynomial(Fit):
    """Polynomial Fitting.

    See Also:
        :ref:`fit_polynomial` model and parameter descriptions

    """

    equation = "cn * x^n + ... + c1 * x^1 + c0"

    @classmethod
    def _check_degree(cls, args: tuple[int, ...]) -> int:
        """Check that polynomial degree is valid."""
        max_degree = 7
        degree = args[0] if args else max_degree
        if not (0 <= degree <= max_degree):
            raise ValueError("The polynomial degree should be at least 0 and smaller than 8.")
        return degree

    @classmethod
    def model(cls, *args: int) -> lmfit.Model:
        """Polynomial Model.

        :meta private:
        """
        degree = cls._check_degree(args)
        return PolynomialModel(degree=degree)

    @classmethod
    def guess(
        cls, *args: int
    ) -> Callable[[npt.NDArray[np.float64], npt.NDArray[np.float64]], dict[str, lmfit.Parameter]]:
        """Polynomial Guessing.

        :meta private:
        """

        def guess(
            x: npt.NDArray[np.float64], y: npt.NDArray[np.float64]
        ) -> dict[str, lmfit.Parameter]:
            init_guess = {}
            degree = cls._check_degree(args)

            coeffs = np.polynomial.polynomial.polyfit(x, y, degree)

            for i in range(degree + 1):
                init_guess[f"c{i}"] = coeffs[i]

            return init_guess

        return guess


class DampedOsc(Fit):
    """Damped Oscillator Fitting.

    See Also:
        :ref:`fit_damped_osc` model and parameter descriptions

    """

    equation = "amp * cos((x - center) * freq) * exp(-(((x - center) / width) ** 2))"

    @classmethod
    def model(cls, *args: int) -> lmfit.Model:
        """Damped Oscillator Model.

        :meta private:
        """

        def model(
            x: npt.NDArray[np.float64], center: float, amp: float, freq: float, width: float
        ) -> npt.NDArray[np.float64]:
            return amp * np.cos((x - center) * freq) * np.exp(-(((x - center) / width) ** 2))

        return lmfit.Model(model, name=f"{cls.__name__}  [{cls.equation}]")

    @classmethod
    def guess(
        cls, *args: int
    ) -> Callable[[npt.NDArray[np.float64], npt.NDArray[np.float64]], dict[str, lmfit.Parameter]]:
        """Damped Oscillator Guessing.

        :meta private:
        """

        def guess(
            x: npt.NDArray[np.float64], y: npt.NDArray[np.float64]
        ) -> dict[str, lmfit.Parameter]:
            peak = x[np.argmax(y)]
            valley = x[np.argmin(y)]

            init_guess = {
                "center": lmfit.Parameter("center", peak),
                "amp": lmfit.Parameter("amp", np.max(y)),
                "freq": lmfit.Parameter("freq", np.pi / np.abs(peak - valley)),
                "width": lmfit.Parameter("width", np.max(x) - np.min(x)),
            }

            return init_guess

        return guess


class SlitScan(Fit):
    """Slit Scan Fitting.

    See Also:
        :ref:`fit_slitscan` model and parameter descriptions

    """

    equation = """See
    https://isiscomputinggroup.github.io/ibex_bluesky_core/fitting/standard_fits.html#fit_slitscan
    for model function"""

    @classmethod
    def model(cls, *args: int) -> lmfit.Model:
        """Slit Scan Model.

        :meta private:
        """

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
                    * erf(
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

        return lmfit.Model(model, name=f"{cls.__name__}  [{cls.equation}]")

    @classmethod
    def guess(
        cls, *args: int
    ) -> Callable[[npt.NDArray[np.float64], npt.NDArray[np.float64]], dict[str, lmfit.Parameter]]:
        """Slit Scan Guessing.

        :meta private:
        """

        def guess(
            x: npt.NDArray[np.float64], y: npt.NDArray[np.float64]
        ) -> dict[str, lmfit.Parameter]:
            background = np.min(y)
            inflection0 = np.min(x) + (1 / 3) * (np.max(x) - np.min(x))
            inflections_diff = (1 / 3) * (np.max(x) - np.min(x))
            gradient = 2 * (np.max(y) - np.min(y)) / (np.max(x) - np.min(x))
            height_above_inflection1 = (np.max(y) - np.min(y)) / 5.0

            init_guess = {
                "background": lmfit.Parameter("background", background),
                "inflection0": lmfit.Parameter("inflection0", inflection0),
                "gradient": lmfit.Parameter("gradient", gradient, min=0),
                "inflections_diff": lmfit.Parameter(
                    "inflections_diff", inflections_diff, min=0, max=float(np.max(x) - np.min(x))
                ),
                "height_above_inflection1": lmfit.Parameter(
                    "height_above_inflection1", height_above_inflection1, min=0
                ),
            }

            return init_guess

        return guess


def _calculate_erf_stretch(
    x: npt.NDArray[np.float64],
    y: npt.NDArray[np.float64],
    erfc: bool = False,
    tails: float = 0.1,
    pre_sorted: bool = False,
) -> float:
    """Calculate the scaling factor needed to fit an error function (erf) to data.

    This function determines how much to stretch or compress a standard error function
    by comparing the x-range in your data to the x-range of a standard erf function
    over the same y-value interval. Specifically:

    1. It finds two y-values in your data: y_front (at tails percentile) and
       y_back (at 1-tails percentile)
    2. Finds the corresponding x-values in your data for these y-values
    3. Compares this x-range with the x-range between inverse erf(tails) and
       inverse erf(1-tails) of a standard error function

    The ratio between these ranges gives the stretch factor needed to scale
    a standard erf function to match your data.

    Args:
        x: The x-axis values of your data points.
        y: The y-axis values of your data points.
        erfc: If True, use the complementary error function (erfc) instead of erf.
        tails: Fraction to ignore at both ends of the y-range. Default 0.1 means
              the function analyses between the 10th and 90th percentiles of the y-range.
        pre_sorted: If True, assumes x and y are already sorted by x values.

    Returns:
        A scaling factor that can be used to stretch (>1) or compress (<1) a standard
        erf function to better fit the data. This is calculated as:
        (data x-value difference) / (inverse_erf difference)

    """
    if not pre_sorted:
        index_array = np.argsort(x)
        x = x[index_array]
        y = y[index_array]

    dy = np.max(y) - np.min(y)
    y_front = np.min(y) + tails * dy
    y_back = np.min(y) + (1 - tails) * dy

    front_i = np.argmin(np.abs(y - y_front))
    back_i = np.argmin(np.abs(y - y_back))

    x_front = x[front_i]
    x_back = x[back_i]

    deltax = (
        np.abs(erfcinv(2 * (1 - tails)) - erfcinv(2 * tails))
        if erfc
        else np.abs(erfinv(1 - tails) - erfinv(tails))
    )

    return np.abs(x_front - x_back) / deltax


class ERF(Fit):
    """Error Function Fitting.

    See Also:
        :ref:`fit_erf` model and parameter descriptions

    """

    equation = "background + scale * erf(stretch * (x - cen))"

    @classmethod
    def model(cls, *args: int) -> lmfit.Model:
        """Error Function Model.

        :meta private:
        """

        def model(
            x: npt.NDArray[np.float64], cen: float, stretch: float, scale: float, background: float
        ) -> npt.NDArray[np.float64]:
            return background + scale * erf(stretch * (x - cen))

        return lmfit.Model(model, name=f"{cls.__name__}  [{cls.equation}]")

    @classmethod
    def guess(
        cls, *args: int
    ) -> Callable[[npt.NDArray[np.float64], npt.NDArray[np.float64]], dict[str, lmfit.Parameter]]:
        """Error Function Guessing.

        :meta private:
        """

        def guess(
            x: npt.NDArray[np.float64], y: npt.NDArray[np.float64]
        ) -> dict[str, lmfit.Parameter]:
            center = np.mean(x)
            scale = (np.max(y) - np.min(y)) / 2
            background = np.min(y) + (np.max(y) - np.min(y)) / 2
            stretch = _calculate_erf_stretch(x, y)

            init_guess = {
                "cen": lmfit.Parameter("cen", center),
                "stretch": lmfit.Parameter("stretch", stretch),
                "scale": lmfit.Parameter("scale", scale),
                "background": lmfit.Parameter("background", background),
            }

            return init_guess

        return guess


class ERFC(Fit):
    """Complementary Error Function Fitting.

    See Also:
        :ref:`fit_erfc` model and parameter descriptions

    """

    equation = "background + scale * erfc(stretch * (x - cen))"

    @classmethod
    def model(cls, *args: int) -> lmfit.Model:
        """Complementary Error Function Model.

        :meta private:
        """

        def model(
            x: npt.NDArray[np.float64], cen: float, stretch: float, scale: float, background: float
        ) -> npt.NDArray[np.float64]:
            return background + scale * erfc(stretch * (x - cen))

        return lmfit.Model(model, name=f"{cls.__name__}  [{cls.equation}]")

    @classmethod
    def guess(
        cls, *args: int
    ) -> Callable[[npt.NDArray[np.float64], npt.NDArray[np.float64]], dict[str, lmfit.Parameter]]:
        """Complementary Error Function Guessing.

        :meta private:
        """

        def guess(
            x: npt.NDArray[np.float64], y: npt.NDArray[np.float64]
        ) -> dict[str, lmfit.Parameter]:
            center = np.mean(x)
            scale = (np.max(y) - np.min(y)) / 2
            background = np.min(y)
            stretch = _calculate_erf_stretch(x, y, True)

            init_guess = {
                "cen": lmfit.Parameter("cen", center),
                "stretch": lmfit.Parameter("stretch", stretch),
                "scale": lmfit.Parameter("scale", scale),
                "background": lmfit.Parameter("background", background),
            }

            return init_guess

        return guess


class TopHat(Fit):
    """Top Hat Fitting.

    See Also:
        :ref:`fit_tophat` model and parameter descriptions

    """

    equation = "if (abs(x - cen) < width / 2) { background + height } else { background }"

    @classmethod
    def model(cls, *args: int) -> lmfit.Model:
        """Top Hat Model.

        :meta private:
        """

        def model(
            x: npt.NDArray[np.float64], cen: float, width: float, height: float, background: float
        ) -> npt.NDArray[np.float64]:
            y = x * 0
            y[np.abs(x - cen) < width / 2] = height
            return background + y

        return lmfit.Model(model, name=f"{cls.__name__}  [{cls.equation}]")

    @classmethod
    def guess(
        cls, *args: int
    ) -> Callable[[npt.NDArray[np.float64], npt.NDArray[np.float64]], dict[str, lmfit.Parameter]]:
        """Top Hat Guessing.

        :meta private:
        """

        def guess(
            x: npt.NDArray[np.float64], y: npt.NDArray[np.float64]
        ) -> dict[str, lmfit.Parameter]:
            cen, width = _guess_cen_and_width(x, y)

            init_guess = {
                "cen": lmfit.Parameter("cen", cen),
                "width": lmfit.Parameter("width", width, min=0),
                "height": lmfit.Parameter(
                    "height",
                    np.max(y) - np.min(y),
                ),
                "background": lmfit.Parameter("background", np.min(y)),
            }

            return init_guess

        return guess


def _guess_trapezoid_gradient(x: npt.NDArray[np.float64], y: npt.NDArray[np.float64]) -> float:
    gradients = np.zeros_like(x[1:], dtype=np.float64)
    x_diffs = x[:-1] - x[1:]
    y_diffs = y[:-1] - y[1:]
    np.divide(y_diffs, x_diffs, out=gradients, where=x_diffs != 0)
    return np.max(np.abs(gradients))


class Trapezoid(Fit):
    """Trapezoid Fitting.

    See Also:
        :ref:`fit_trapezoid` model and parameter descriptions

    """

    equation = """
    y = clip(y_offset + height + background - gradient * abs(x - cen),
     background, background + height)"""

    @classmethod
    def model(cls, *args: int) -> lmfit.Model:
        """Trapezoid Model.

        :meta private:
        """

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

        return lmfit.Model(model, name=f"{cls.__name__}  [{cls.equation}]")

    @classmethod
    def guess(
        cls, *args: int
    ) -> Callable[[npt.NDArray[np.float64], npt.NDArray[np.float64]], dict[str, lmfit.Parameter]]:
        """Trapezoid Guessing.

        :meta private:
        """

        def guess(
            x: npt.NDArray[np.float64], y: npt.NDArray[np.float64]
        ) -> dict[str, lmfit.Parameter]:
            cen, width = _guess_cen_and_width(x, y)
            gradient_guess = _guess_trapezoid_gradient(x, y)

            height = np.max(y) - np.min(y)
            background = np.min(y)
            y_offset = gradient_guess * width / 2.0

            init_guess = {
                "cen": lmfit.Parameter("cen", cen, min=np.min(x), max=np.max(x)),
                "gradient": lmfit.Parameter("gradient", gradient_guess, min=0),
                "height": lmfit.Parameter("height", height, min=0),
                "background": lmfit.Parameter("background", background),
                "y_offset": lmfit.Parameter("y_offset", y_offset),
            }

            return init_guess

        return guess


class NegativeTrapezoid(Fit):
    """Negative Trapezoid Fitting.

    See Also:
        :ref:`fit_neg_trapezoid` model and parameter descriptions

    """

    equation = """
    y = clip(y_offset - height + background + gradient * abs(x - cen),
     background - height, background)"""

    @classmethod
    def model(cls, *args: int) -> lmfit.Model:
        """Negative Trapezoid Model.

        :meta private:
        """

        def model(
            x: npt.NDArray[np.float64],
            cen: float,
            gradient: float,
            height: float,
            background: float,
            y_offset: float,  # Acts as a width multiplier
        ) -> npt.NDArray[np.float64]:
            y = y_offset - height + background + gradient * np.abs(x - cen)
            y = np.maximum(y, background - height)
            y = np.minimum(y, background)
            return y

        return lmfit.Model(model, name=f"{cls.__name__}  [{cls.equation}]")

    @classmethod
    def guess(
        cls, *args: int
    ) -> Callable[[npt.NDArray[np.float64], npt.NDArray[np.float64]], dict[str, lmfit.Parameter]]:
        """Negative Trapezoid Guessing.

        :meta private:
        """

        def guess(
            x: npt.NDArray[np.float64], y: npt.NDArray[np.float64]
        ) -> dict[str, lmfit.Parameter]:
            cen, width = _guess_cen_and_width(x, -y)
            gradient_guess = _guess_trapezoid_gradient(x, y)

            height = np.max(y) - np.min(y)
            background = np.max(y)
            y_offset = -gradient_guess * width / 2.0

            init_guess = {
                "cen": lmfit.Parameter("cen", cen, min=np.min(x), max=np.max(x)),
                "gradient": lmfit.Parameter("gradient", gradient_guess, min=0),
                "height": lmfit.Parameter("height", height, min=0),
                "background": lmfit.Parameter("background", background),
                "y_offset": lmfit.Parameter("y_offset", y_offset),
            }

            return init_guess

        return guess


class MuonMomentum(Fit):
    """Muon momentum fitting.

    See Also:
        :ref:`fit_muon_momentum` model and parameter descriptions

    """

    equation = """
        y=(erfc((x-x0/w))*(r/2)+b)*((x/x0)**p)"""

    @classmethod
    def model(cls, *args: int) -> lmfit.Model:
        """Momentum scan model.

        :meta private:
        """

        def model(
            x: npt.NDArray[np.float64], x0: float, r: float, w: float, p: float, b: float
        ) -> npt.NDArray[np.float64]:
            return (erfc((x - x0) / w) * (r / 2) + b) * ((x / x0) ** p)

        return lmfit.Model(model, name=f"{cls.__name__}  [{cls.equation}]")

    @classmethod
    def guess(
        cls, *args: int
    ) -> Callable[[npt.NDArray[np.float64], npt.NDArray[np.float64]], dict[str, lmfit.Parameter]]:
        """Momentum Scan Fit Guessing.

        :meta private:
        """

        def guess(
            x: npt.NDArray[np.float64], y: npt.NDArray[np.float64]
        ) -> dict[str, lmfit.Parameter]:
            index_array = np.argsort(x)
            x = x[index_array]
            y = y[index_array]

            index_min_y = np.argmin(y)
            index_max_y = np.argmax(y)

            b = np.min(y)
            r = np.max(y) - b

            x_slope = x[
                index_max_y:index_min_y
            ]  # Gets all x values between the maximum and minimum y

            if len(x_slope) != 0:
                x0 = np.mean(x_slope)
            else:
                x0 = x[-1]  # Picked as it can't be 0

            p = 1  # Expected value, not likely to change
            w = 1 / _calculate_erf_stretch(x, y, erfc=True, pre_sorted=True)

            init_guess = {
                "b": lmfit.Parameter("b", b),
                "r": lmfit.Parameter("r", r, min=0),
                "x0": lmfit.Parameter("x0", x0, min=0),
                "p": lmfit.Parameter("p", p, min=0),
                "w": lmfit.Parameter("w", w, min=0),
            }
            return init_guess

        return guess

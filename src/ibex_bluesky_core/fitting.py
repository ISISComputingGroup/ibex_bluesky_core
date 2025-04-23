"""Fitting methods used by the LiveFit callback."""

from abc import ABC, abstractmethod
from collections.abc import Callable

import lmfit
import numpy as np
import scipy
import scipy.special
from lmfit.models import PolynomialModel
from numpy import polynomial as p
from numpy import typing as npt

__all__ = [
    "ERF",
    "ERFC",
    "DampedOsc",
    "Fit",
    "FitMethod",
    "Gaussian",
    "Linear",
    "Lorentzian",
    "NegativeTrapezoid",
    "Polynomial",
    "SlitScan",
    "TopHat",
    "Trapezoid",
]


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
        """Assign model and guess functions.

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


class Gaussian(Fit):
    """Gaussian Fitting."""

    equation = "amp * exp(-((x - x0) ** 2) / (2 * sigma**2)) + background"

    @classmethod
    def model(cls, *args: int) -> lmfit.Model:
        """Gaussian Model."""

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

    equation = "amp / (1 + ((x - center) / sigma) ** 2) + background"

    @classmethod
    def model(cls, *args: int) -> lmfit.Model:
        """Lorentzian Model."""

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

    equation = "c1 * x + c0"

    @classmethod
    def model(cls, *args: int) -> lmfit.Model:
        """Linear Model."""

        def model(x: npt.NDArray[np.float64], c1: float, c0: float) -> npt.NDArray[np.float64]:
            return c1 * x + c0

        return lmfit.Model(model, name=f"{cls.__name__}  [{cls.equation}]")

    @classmethod
    def guess(
        cls, *args: int
    ) -> Callable[[npt.NDArray[np.float64], npt.NDArray[np.float64]], dict[str, lmfit.Parameter]]:
        """Linear Guessing."""
        return Polynomial.guess(1)


class Polynomial(Fit):
    """Polynomial Fitting."""

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

    equation = "amp * cos((x - center) * freq) * exp(-(((x - center) / width) ** 2))"

    @classmethod
    def model(cls, *args: int) -> lmfit.Model:
        """Damped Oscillator Model."""

        def model(
            x: npt.NDArray[np.float64], center: float, amp: float, freq: float, width: float
        ) -> npt.NDArray[np.float64]:
            return amp * np.cos((x - center) * freq) * np.exp(-(((x - center) / width) ** 2))

        return lmfit.Model(model, name=f"{cls.__name__}  [{cls.equation}]")

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

    equation = """See
    https://isiscomputinggroup.github.io/ibex_bluesky_core/fitting/standard_fits.html#slit-scan-slitscan
    for model function"""

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

        return lmfit.Model(model, name=f"{cls.__name__}  [{cls.equation}]")

    @classmethod
    def guess(
        cls, *args: int
    ) -> Callable[[npt.NDArray[np.float64], npt.NDArray[np.float64]], dict[str, lmfit.Parameter]]:
        """Slit Scan Guessing."""

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


class ERF(Fit):
    """Error Function Fitting."""

    equation = "background + scale * erf(stretch * (x - cen))"

    @classmethod
    def model(cls, *args: int) -> lmfit.Model:
        """Error Function Model."""

        def model(
            x: npt.NDArray[np.float64], cen: float, stretch: float, scale: float, background: float
        ) -> npt.NDArray[np.float64]:
            return background + scale * scipy.special.erf(stretch * (x - cen))

        return lmfit.Model(model, name=f"{cls.__name__}  [{cls.equation}]")

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

    equation = "background + scale * erfc(stretch * (x - cen))"

    @classmethod
    def model(cls, *args: int) -> lmfit.Model:
        """Complementary Error Function Model."""

        def model(
            x: npt.NDArray[np.float64], cen: float, stretch: float, scale: float, background: float
        ) -> npt.NDArray[np.float64]:
            return background + scale * scipy.special.erfc(stretch * (x - cen))

        return lmfit.Model(model, name=f"{cls.__name__}  [{cls.equation}]")

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


def _center_of_mass_and_mass(
    x: npt.NDArray[np.float64], y: npt.NDArray[np.float64]
) -> tuple[float, float]:
    """Compute the centre of mass of the area under a curve defined by a series of (x, y) points.

    The "area under the curve" is a shape bounded by:
    - min(y), along the bottom edge
    - min(x), on the left-hand edge
    - max(x), on the right-hand edge
    - straight lines joining (x, y) data points to their nearest neighbours
        along the x-axis, along the top edge
    This is implemented by geometric decomposition of the shape into a series of trapezoids,
    which are further decomposed into rectangular and triangular regions.
    """
    sort_indices = np.argsort(x, kind="stable")
    x = np.take_along_axis(x, sort_indices, axis=None)
    y = np.take_along_axis(y - np.min(y), sort_indices, axis=None)
    widths = np.diff(x)

    # Area under the curve for two adjacent points is a right trapezoid.
    # Split that trapezoid into a rectangular region, plus a right triangle.
    # Find area and effective X CoM for each.
    rect_areas = widths * np.minimum(y[:-1], y[1:])
    rect_x_com = (x[:-1] + x[1:]) / 2.0
    triangle_areas = widths * np.abs(y[:-1] - y[1:]) / 2.0
    triangle_x_com = np.where(
        y[:-1] > y[1:], x[:-1] + (widths / 3.0), x[:-1] + (2.0 * widths / 3.0)
    )

    total_area = np.sum(rect_areas + triangle_areas)
    if total_area == 0.0:
        # If all data was flat, return central x
        return (x[0] + x[-1]) / 2.0, 0

    com = np.sum(rect_areas * rect_x_com + triangle_areas * triangle_x_com) / total_area
    return com, total_area


def _guess_cen_and_width(
    x: npt.NDArray[np.float64], y: npt.NDArray[np.float64]
) -> tuple[float, float]:
    """Guess the center and width of a positive peak."""
    com, total_area = _center_of_mass_and_mass(x, y)
    y_range = np.max(y) - np.min(y)
    if y_range == 0.0:
        width = (np.max(x) - np.min(x)) / 2
    else:
        width = total_area / y_range
    return com, width


class TopHat(Fit):
    """Top Hat Fitting."""

    equation = "if (abs(x - cen) < width / 2) { background + height } else { background }"

    @classmethod
    def model(cls, *args: int) -> lmfit.Model:
        """Top Hat Model."""

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
        """Top Hat Guessing."""

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
    """Trapezoid Fitting."""

    equation = """
    y = clip(y_offset + height + background - gradient * abs(x - cen),
     background, background + height)"""

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

        return lmfit.Model(model, name=f"{cls.__name__}  [{cls.equation}]")

    @classmethod
    def guess(
        cls, *args: int
    ) -> Callable[[npt.NDArray[np.float64], npt.NDArray[np.float64]], dict[str, lmfit.Parameter]]:
        """Trapezoid Guessing."""

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
    """Negative Trapezoid Fitting."""

    equation = """
    y = clip(y_offset - height + background + gradient * abs(x - cen),
     background - height, background)"""

    @classmethod
    def model(cls, *args: int) -> lmfit.Model:
        """Negative Trapezoid Model."""

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
        """Negative Trapezoid Guessing."""

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

"""Utilities for plans which are not plan stubs."""

from __future__ import annotations

import os
from typing import Any, Protocol

import matplotlib
import numpy as np
import numpy.typing as npt
import scipp as sc
from bluesky.protocols import NamedMovable, Readable

__all__ = [
    "NamedReadableAndMovable",
    "calculate_erf_stretch",
    "calculate_polarisation",
    "centred_pixel",
    "get_pv_prefix",
    "is_matplotlib_backend_qt",
]

from scipy.special import erfcinv, erfinv


def is_matplotlib_backend_qt() -> bool:
    """Return True if matplotlib is using a qt backend."""
    return "qt" in matplotlib.get_backend().lower()


def centred_pixel(centre: int, pixel_range: int) -> list[int]:
    """Given a centre and range, return a contiguous range of pixels around the centre, inclusive.

    ie. a centre of 50 with a range of 3 will give [47, 48, 49, 50, 51, 52, 53]

    Args:
          centre (int): The centre pixel number.
          pixel_range (int): The range of pixels either side to surround the centre.

    Returns a list of pixel numbers.

    """
    return [s for s in range(centre - pixel_range, centre + pixel_range + 1)]


def get_pv_prefix() -> str:
    """Return the PV prefix for the current instrument."""
    prefix = os.getenv("MYPVPREFIX")

    if prefix is None:
        raise OSError("MYPVPREFIX environment variable not available - please define")

    return prefix


class NamedReadableAndMovable(Readable[Any], NamedMovable[Any], Protocol):
    """Abstract class for type checking that an object is readable, named and movable."""


def calculate_polarisation(
    a: sc.Variable | sc.DataArray, b: sc.Variable | sc.DataArray
) -> sc.Variable | sc.DataArray:
    """Calculate polarisation value and propagate uncertainties.

    This function computes the polarisation given by the formula (a-b)/(a+b)
    and propagates the uncertainties associated with a and b.

    Args:
        a: scipp :external+scipp:py:obj:`Variable <scipp.Variable>`
            or :external+scipp:py:obj:`DataArray <scipp.DataArray>`
        b: scipp :external+scipp:py:obj:`Variable <scipp.Variable>`
            or :external+scipp:py:obj:`DataArray <scipp.DataArray>`

    Returns:
        polarisation, ``(a - b) / (a + b)``, as a scipp
        :external+scipp:py:obj:`Variable <scipp.Variable>`
        or :external+scipp:py:obj:`DataArray <scipp.DataArray>`

    On SANS instruments e.g. LARMOR, A and B correspond to intensity in different DAE
    periods (before/after switching a flipper) and the output is interpreted as a neutron
    polarisation ratio.

    On reflectometry instruments e.g. POLREF, the situation is the same as on LARMOR.

    On muon instruments, A and B correspond to measuring from forward/backward detector
    banks, and the output is interpreted as a muon asymmetry.

    """
    if a.unit != b.unit:
        raise ValueError("The units of a and b are not equivalent.")
    if a.sizes != b.sizes:
        raise ValueError("Dimensions/shape of a and b must match.")

    # This line allows for dims, units, and dtype to be handled by scipp
    polarisation_value = (a - b) / (a + b)

    variances_a = a.variances
    variances_b = b.variances
    values_a = a.values
    values_b = b.values

    # Calculate partial derivatives
    partial_a = 2 * values_b / (values_a + values_b) ** 2
    partial_b = -2 * values_a / (values_a + values_b) ** 2

    variance_return = (partial_a**2 * variances_a) + (partial_b**2 * variances_b)

    # Propagate uncertainties
    polarisation_value.variances = variance_return

    return polarisation_value


def calculate_erf_stretch(
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

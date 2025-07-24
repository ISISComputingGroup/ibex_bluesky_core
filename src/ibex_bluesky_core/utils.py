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
    "calculate_polarisation",
    "center_of_mass_of_area_under_curve",
    "centred_pixel",
    "get_pv_prefix",
    "is_matplotlib_backend_qt",
]


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


def center_of_mass_of_area_under_curve(
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

    Returns a tuple of the centre of mass and the total area under the curve.

    """
    # Sorting here avoids special-cases with disordered points, which may occur
    # from a there-and-back scan, or from an adaptive scan.
    sort_indices = np.argsort(x, kind="stable")
    x = np.take_along_axis(x, sort_indices, axis=None)
    y = np.take_along_axis(y - np.min(y), sort_indices, axis=None)

    # If the data points are "fence-posts", this calculates the x width of
    # each "fence panel".
    widths = np.diff(x)

    # Area under the curve for two adjacent points is a right trapezoid.
    # Split that trapezoid into a rectangular region, plus a right triangle.
    # Find area and effective X CoM for each.

    # We want the area of the rectangular part of the right trapezoid.
    # This is width * [height of either left or right point, whichever is lowest]
    rect_areas = widths * np.minimum(y[:-1], y[1:])
    # CoM of a rectangle in x is simply the average x.
    rect_x_com = (x[:-1] + x[1:]) / 2.0

    # Now the area of the triangular part of the right trapezoid - this is
    # width * height / 2, where height is the absolute difference between the
    # two y values.
    triangle_areas = widths * np.abs(y[:-1] - y[1:]) / 2.0
    # CoM of a right triangle is 1/3 along the base, from the right angle
    # y[:-1] > y[1:] is true if y_[n] > y_[n+1], (i.e. if the right angle is on the
    # left-hand side of the triangle).
    # If that's true, the CoM lies 1/3 of the way along the x axis
    # Otherwise, the CoM lies 2/3 of the way along the x axis (1/3 from the right angle)
    triangle_x_com = np.where(
        y[:-1] > y[1:], x[:-1] + (widths / 3.0), x[:-1] + (2.0 * widths / 3.0)
    )

    total_area = np.sum(rect_areas + triangle_areas)
    if total_area == 0.0:
        # If all data was flat, return central x
        return (x[0] + x[-1]) / 2.0, total_area

    return np.sum(
        rect_areas * rect_x_com + triangle_areas * triangle_x_com
    ) / total_area, total_area


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

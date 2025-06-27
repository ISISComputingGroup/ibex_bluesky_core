"""Utilities for plans which are not plan stubs."""

from __future__ import annotations

import os
from typing import Any, Protocol

import matplotlib
import numpy as np
import numpy.typing as npt
from bluesky.protocols import NamedMovable, Readable

__all__ = [
    "NamedReadableAndMovable",
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
        return (x[0] + x[-1]) / 2.0, total_area

    return np.sum(
        rect_areas * rect_x_com + triangle_areas * triangle_x_com
    ) / total_area, total_area

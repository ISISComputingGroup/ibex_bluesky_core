"""Utilities for plans which are not plan stubs."""

from __future__ import annotations

import os
from typing import Any, Protocol

import matplotlib
import scipp as sc
from bluesky.protocols import NamedMovable, Readable

__all__ = [
    "NamedReadableAndMovable",
    "calculate_polarisation",
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

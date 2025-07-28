"""Utilities for plans which are not plan stubs."""

from __future__ import annotations

import os
from typing import Any, Protocol, TypeVar

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

T = TypeVar("T", sc.Variable, sc.DataArray)


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
    a: T,
    b: T,
    alpha: float = 1.0,
) -> T:
    r"""Calculate polarisation or asymmetry, propagating uncertainties.

    The value returned by this function is:

    .. math::

        f(a, b, \alpha) = \frac{a - \alpha b}{a + \alpha b}

    Where :math:`a` and :math:`b` are the two input scipp
    :external+scipp:py:obj:`variables <scipp.Variable>`, which may have corresponding
    variances, and :math:`\alpha` is an optional scalar (float). If :math:`\alpha` is
    not provided, it defaults to 1.

    The variances are propagated using the partial derivatives of :math:`f` with
    respect to :math:`a` and :math:`b`:

    .. math::

        \frac{\partial f}{\partial a} = \frac{2 b \alpha}{(a + b \alpha)^2}

        \frac{\partial f}{\partial b} = \frac{-2 a \alpha}{(a + b \alpha)^2}

        \sigma_f^2 = (\frac{\partial f}{\partial a})^2 \sigma_a^2
            + (\frac{\partial f}{\partial b})^2 \sigma_b^2

    .. note::

        :math:`\alpha` is a scalar constant and is assumed not to have a variance.

    On SANS instruments (e.g. LARMOR) and reflectometry instruments (e.g. POLREF),
    :math:`a` and :math:`b` correspond to intensity in different DAE periods
    (before/after switching a flipper) and the output is interpreted as a neutron
    polarisation ratio. :math:`\alpha` is fixed at 1.

    On muon instruments, :math:`a` and :math:`b` correspond to measuring from
    forward/backward detector banks, and the output is interpreted as a muon asymmetry.
    :math:`\alpha` will not necessarily be 1.

    Args:
        a: scipp :external+scipp:py:obj:`Variable <scipp.Variable>`
            or :external+scipp:py:obj:`DataArray <scipp.DataArray>`
        b: scipp :external+scipp:py:obj:`Variable <scipp.Variable>`
            or :external+scipp:py:obj:`DataArray <scipp.DataArray>`
        alpha: Optional scalar, defaults to 1.

    Returns:
        Polarisation or asymmetry as a scipp
        :external+scipp:py:obj:`Variable <scipp.Variable>`
        or :external+scipp:py:obj:`DataArray <scipp.DataArray>`

    """
    if a.unit != b.unit:
        raise ValueError("The units of a and b are not equivalent.")
    if a.sizes != b.sizes:
        raise ValueError("Dimensions/shape of a and b must match.")

    # Allows dims, units, and dtype to be handled by scipp
    polarisation = (a - alpha * b) / (a + alpha * b)

    # Calculate partial derivatives
    partial_a = 2 * b.values * alpha / (a.values + b.values * alpha) ** 2
    partial_b = -2 * a.values * alpha / (a.values + b.values * alpha) ** 2

    # Propagate uncertainties
    polarisation.variances = (partial_a**2 * a.variances) + (partial_b**2 * b.variances)

    return polarisation

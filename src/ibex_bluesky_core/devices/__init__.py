"""Common utilities for use across devices."""

import os


def get_pv_prefix() -> str:
    """Return the PV prefix for the current instrument."""
    prefix = os.getenv("MYPVPREFIX")

    if prefix is None:
        raise EnvironmentError("MYPVPREFIX environment variable not available - please define")

    return prefix

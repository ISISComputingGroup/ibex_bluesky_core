"""Generic plan helpers."""

from collections.abc import Generator

import bluesky.plan_stubs as bps
from bluesky.utils import Msg

from ibex_bluesky_core.devices.simpledae import SimpleDae


def set_num_periods(dae: SimpleDae, nperiods: int) -> Generator[Msg, None, None]:
    """Set the number of periods for a DAE.

    Args:
        dae (SimpleDae): DAE object.
        nperiods (int): number of periods to set.

    """
    yield from bps.mv(dae.number_of_periods, nperiods)  # type: ignore
    actual = yield from bps.rd(dae.number_of_periods)
    if actual != nperiods:
        raise ValueError(
            f"Could not set {nperiods} periods on DAE (probably requesting too many points, "
            f"or already running)"
        )

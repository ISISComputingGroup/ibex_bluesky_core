"""Wrap a plan with temporary modification to Periods Settings."""

import copy
from collections.abc import Generator

import bluesky.plan_stubs as bps
import bluesky.preprocessors as bpp
from bluesky.utils import Msg
from ophyd_async.plan_stubs import ensure_connected

from ibex_bluesky_core.devices.dae import Dae


def num_periods_wrapper(
        plan: Generator[Msg, None, None],
        dae: "Dae",
        **modified_periods: int | str | None) -> Generator[Msg, None, None]:
    """Wrap a plan with temporary modification to Periods Settings."""
    yield from ensure_connected(dae)

    original_num_periods = None

    def _inner() -> Generator[Msg, None, None]:
        nonlocal original_num_periods
        original_num_periods = yield from bps.rd(dae.period_settings)

        new_num_periods = copy.deepcopy(original_num_periods)

        for key, value in modified_periods.items():
            if hasattr(new_num_periods, key):
                setattr(new_num_periods, key, value)

        yield from bps.mv(dae.period_settings, new_num_periods)
        yield from plan

    def _onexit() -> Generator[Msg, None, None]:
        nonlocal original_num_periods
        if original_num_periods is not None:
            yield from bps.mv(dae.period_settings, original_num_periods)

    return (yield from bpp.finalize_wrapper(_inner(), _onexit()))

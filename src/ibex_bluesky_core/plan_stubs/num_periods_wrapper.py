"""Wrap a plan with temporary modification to Periods Settings."""

import copy
from collections.abc import Generator

import bluesky.plan_stubs as bps
import bluesky.preprocessors as bpp
from bluesky.utils import Msg
from ophyd_async.plan_stubs import ensure_connected

from ibex_bluesky_core.devices.dae import DaePeriodSettings


def with_num_periods(
        plan: Generator[Msg, None, None],
        dae: DaePeriodSettings) -> Generator[Msg, None, None]:
    """Wrap a plan with temporary modification to Periods Settings.
    
    Args:
        plan: The plan to wrap.
        dae: The Dae instance.
    
    Returns:
        A generator which runs the plan with the modified DAE settings, restoring the original
        settings afterwards.
    """

    yield from ensure_connected(dae)

    original_num_periods = None

    def _inner() -> Generator[Msg, None, None]:
        nonlocal original_num_periods
        original_num_periods = yield from bps.rd(dae.number_of_periods)

        yield from plan

    def _onexit() -> Generator[Msg, None, None]:
        nonlocal original_num_periods
        if original_num_periods is not None:
            yield from bps.mv(dae.number_of_periods, original_num_periods)

    return (yield from bpp.finalize_wrapper(_inner(), _onexit()))

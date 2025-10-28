"""Wrap a plan with temporary modification to Periods Settings."""

import copy
from collections.abc import Generator

import bluesky.plan_stubs as bps
import bluesky.preprocessors as bpp
from bluesky.utils import Msg
from ophyd_async.plan_stubs import ensure_connected
from ibex_bluesky_core.devices.dae import DaePeriodSettings, Dae


def with_num_periods(
    plan: Generator[Msg, None, None], dae: Dae, number_of_periods: int
) -> Generator[Msg, None, None]:
    """Wrap a plan with temporary modification to Periods Settings.

    Args:
        plan: The plan to wrap.
        dae: The Dae instance.
        number_of_periods: The number of periods to set to temporarily.

    Returns:
        A generator which runs the plan with the modified number of periods, restoring the original
        number of periods afterwards.

    """

    original_num_periods = None

    def _inner() -> Generator[Msg, None, None]:
        yield from ensure_connected(dae)
        nonlocal original_num_periods
        original_num_periods = yield from bps.rd(dae.number_of_periods)

        yield from bps.mv(dae.number_of_periods, number_of_periods)

        yield from plan

    def _cleanup() -> Generator[Msg, None, None]:
        yield from bps.mv(dae.number_of_periods, original_num_periods)

    return (yield from bpp.finalize_wrapper(_inner(), _cleanup()))

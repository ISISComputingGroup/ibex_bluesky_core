"""Wrap a plan with temporary modification to Time Channel Settings."""

from collections.abc import Generator

import bluesky.plan_stubs as bps
import bluesky.preprocessors as bpp
from bluesky.utils import Msg
from ophyd_async.plan_stubs import ensure_connected

from ibex_bluesky_core.devices.dae import Dae


def with_time_channels(
    plan: Generator[Msg, None, None], dae: Dae
) -> Generator[Msg, None, None]:
    """Wrap a plan with temporary modification to Time Channel Settings.

    Args:
        plan: The plan to wrap.
        dae: The Dae instance.

    Returns:
        A generator which runs the plan with the modified DAE settings, restoring the original
        settings afterwards.

    """
    yield from ensure_connected(dae)

    original_time_channels = None

    def _inner() -> Generator[Msg, None, None]:
        nonlocal original_time_channels
        original_time_channels = yield from bps.rd(dae.tcb_settings) #type: ignore

        yield from plan

    def _onexit() -> Generator[Msg, None, None]:
        nonlocal original_time_channels
        if original_time_channels is not None:
            yield from bps.mv(dae.tcb_settings, original_time_channels)

    return (yield from bpp.finalize_wrapper(_inner(), _onexit()))

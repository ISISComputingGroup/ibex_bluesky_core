"""Wrap a plan with temporary modification to Time Channel Settings."""

import copy
from collections.abc import Generator

import bluesky.plan_stubs as bps
import bluesky.preprocessors as bpp
from bluesky.utils import Msg
from ophyd_async.plan_stubs import ensure_connected

from ibex_bluesky_core.devices.dae import Dae


def tcb_wrapper(
        plan: Generator[Msg, None, None],
        dae: "Dae",
        **modified_dae: int | str | None) -> Generator[Msg, None, None]:
    """Wrap a plan with temporary modification to DAE Settings."""
    yield from ensure_connected(dae)

    original_time_channels = None

    def _inner() -> Generator[Msg, None, None]:
        nonlocal original_time_channels
        original_time_channels = yield from bps.rd(dae.tcb_settings)

        new_time_channels = copy.deepcopy(original_time_channels)

        for key, value in modified_dae.items():
            if hasattr(new_time_channels, key):
                setattr(new_time_channels, key, value)

        yield from bps.mv(dae.tcb_settings, new_time_channels)
        yield from plan

    def _onexit() -> Generator[Msg, None, None]:
        nonlocal original_time_channels
        if original_time_channels is not None:
            yield from bps.mv(dae.tcb_settings, original_time_channels)

    return (yield from bpp.finalize_wrapper(_inner(), _onexit()))

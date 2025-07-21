"""Wrap a plan with temporary modification to DAE Settings."""

import copy
from collections.abc import Generator

import bluesky.plan_stubs as bps
import bluesky.preprocessors as bpp
from bluesky.utils import Msg
from ophyd_async.plan_stubs import ensure_connected

from ibex_bluesky_core.devices.dae import Dae


def time_channels_wrapper(
        plan: Generator[Msg, None, None],
        dae: "Dae",
        **modified_dae: int | str | None) -> Generator[Msg, None, None]:
    """Wrap a plan with temporary modification to DAE Settings."""
    yield from ensure_connected(dae)

    original_dae_setting = None

    def _inner() -> Generator[Msg, None, None]:
        nonlocal original_dae_setting
        original_dae_setting = yield from bps.rd(dae.dae_settings)

        new_dea_tables = copy.deepcopy(original_dae_setting)

        for key, value in modified_dae.items():
            if hasattr(new_dea_tables, key):
                setattr(new_dea_tables, key, value)

        yield from bps.mv(dae.dae_settings, original_dae_setting)
        yield from plan

    def _onexit() -> Generator[Msg, None, None]:
        nonlocal original_dae_setting
        if original_dae_setting is not None:
            yield from bps.mv(dae.dae_settings, original_dae_setting)

    return (yield from bpp.finalize_wrapper(_inner(), _onexit()))

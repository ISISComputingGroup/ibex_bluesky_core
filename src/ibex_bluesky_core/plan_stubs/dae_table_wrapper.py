"""Wrap a plan with temporary modification to DAE Settings."""

from collections.abc import Generator

import bluesky.plan_stubs as bps
import bluesky.preprocessors as bpp
from bluesky.utils import Msg
from ophyd_async.plan_stubs import ensure_connected

from ibex_bluesky_core.devices.dae import Dae, DaeSettingsData


def _with_dae_tables(
    plan: Generator[Msg, None, None], dae: Dae, new_settings: DaeSettingsData
) -> Generator[Msg, None, None]:
    """Wrap a plan with temporary modification to DAE Settings.

    Args:
        plan: The plan to wrap.
        dae: The Dae instance.
        new_settings: The new DAE Settings to apply temporarily.

    Returns:
        A generator which runs the plan with the modified DAE settings, restoring the original
        settings afterwards.

    """
    yield from ensure_connected(dae)

    original_dae_setting = None

    def _inner() -> Generator[Msg, None, None]:
        nonlocal original_dae_setting
        original_dae_setting = yield from bps.rd(dae.dae_settings)

        yield from bps.mv(dae.dae_settings, new_settings)

        yield from plan

    def _cleanup() -> Generator[Msg, None, None]:
        yield from bps.mv(dae.dae_settings, original_dae_setting)

    return (yield from bpp.finalize_wrapper(_inner(), _cleanup()))

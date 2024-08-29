"""Demonstration plan showing basic bluesky functionality."""

from typing import Generator

import bluesky.plan_stubs as bps
from bluesky.callbacks import LiveTable
from bluesky.preprocessors import run_decorator
from bluesky.utils import Msg
from ophyd_async.plan_stubs import ensure_connected

from ibex_bluesky_core.devices import get_pv_prefix
from ibex_bluesky_core.devices.block import BlockRwRbv, block_rw_rbv
from ibex_bluesky_core.devices.dae.dae import Dae
from ibex_bluesky_core.devices.dae.dae_settings import DaeSettingsData
from ibex_bluesky_core.devices.dae.dae_tcb_settings import DaeTCBSettingsData
from ibex_bluesky_core.run_engine import get_run_engine

__all__ = ["run_demo_plan", "demo_plan"]

from ibex_bluesky_core.devices.dae.dae_period_settings import DaePeriodSettingsData


def run_demo_plan() -> None:
    """Run the demo plan, including setup which would usually be done outside the plan.

    You will need a DAE in a state which can begin, and a settable & readable
    floating-point block named "mot".

    Run using:
    >>> from ibex_bluesky_core.demo_plan import run_demo_plan
    >>> run_demo_plan()
    """
    RE = get_run_engine()
    prefix = get_pv_prefix()
    block = block_rw_rbv(float, "mot")
    dae = Dae(prefix)
    RE(
        demo_plan(block, dae),
        [
            LiveTable(
                [
                    "mot",
                    "DAE-good_uah",
                    "DAE-run_state",
                    "DAE-rb_number",
                    "DAE-period-run_duration",
                ],
                default_prec=10,
            ),
            print,
        ],
    )
    # RE(demo_plan(block, dae), print)


def demo_plan(block: BlockRwRbv[float], dae: Dae) -> Generator[Msg, None, None]:
    """Demonstration plan which moves a block and reads the DAE."""
    yield from ensure_connected(block, dae, force_reconnect=True)

    @run_decorator(md={})
    def _inner() -> Generator[Msg, None, None]:
        current_period_settings: DaePeriodSettingsData = yield from bps.rd(dae.period_settings)
        print(current_period_settings)
        current_period_settings.periods_type = 0

        current_period_settings.periods_src = 0

        yield from bps.mv(dae.period_settings, current_period_settings)

        current_dae_settings: DaeSettingsData = yield from bps.rd(dae.dae_settings)
        print(current_dae_settings)

        # current_dae_settings.mon_spect = random.randint(1, 10)
        current_dae_settings.spectra_filepath = (
            "C:/Instrument/Settings/config/NDLT1542/configurations/tables/spectra_ibextest.dat"
        )
        yield from bps.mv(dae.dae_settings, current_dae_settings)

        new_dae_settings: DaeSettingsData = yield from bps.rd(dae.dae_settings)
        print(new_dae_settings)

        current_tcb_settings: DaeTCBSettingsData = yield from bps.rd(dae.tcb_settings)
        print(current_tcb_settings)
        current_tcb_settings.time_unit = 1 if current_tcb_settings.time_unit == 0 else 0
        yield from bps.mv(dae.tcb_settings, current_tcb_settings)

        # A "simple" acquisition using trigger_and_read.
        yield from bps.abs_set(block, 1.0, wait=True)
        yield from bps.trigger_and_read([block, dae])

        # More complicated acquisition showing arbitrary DAE control to support complex use-cases.
        yield from bps.abs_set(block, 2.0, wait=True)
        yield from bps.trigger(dae.controls.begin_run, wait=True)
        yield from bps.sleep(2)  # ... some complicated logic ...
        yield from bps.trigger(dae.controls.end_run, wait=True)
        yield from bps.create()  # Create a bundle of readings
        yield from bps.read(block)
        yield from bps.read(dae)
        yield from bps.save()

    yield from _inner()


if __name__ == "__main__":
    run_demo_plan()

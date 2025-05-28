"""Demonstration plan showing basic bluesky functionality."""

import os
from collections.abc import Generator

import bluesky.plans as bp
import bluesky.preprocessors as bpp
import matplotlib
import matplotlib.pyplot as plt
import numpy as np
import scipp as sc
from bluesky.utils import Msg
from ophyd_async.plan_stubs import ensure_connected

from ibex_bluesky_core.callbacks import LivePColorMesh
from ibex_bluesky_core.devices.block import block_rw_rbv
from ibex_bluesky_core.devices.simpledae import (
    DSpacingMappingReducer,
    GoodUahWaiter,
    RunPerPointController,
    SimpleDae,
)
from ibex_bluesky_core.plan_stubs import call_qt_aware
from ibex_bluesky_core.run_engine import get_run_engine
from ibex_bluesky_core.utils import get_pv_prefix

NUM_POINTS: int = 10


def dae_scan_plan() -> Generator[Msg, None, None]:
    """Manual system test which moves a block and reads the DAE.

    Prerequisites:
    - A block named "mot" pointing at MOT:MTR0101.RBV
    - A galil IOC in RECSIM mode with MTRCTRL=1 so that the above PV is available
    - A DAE in a setup which can begin and end simulated runs.

    Expected result:
    - A sensible-looking LiveTable has been displayed
      * Shows mot stepping from 0 to 10 in 3 evenly-spaced steps
    - A plot has been displayed (in IBEX if running in the IBEX gui, in a QT window otherwise)
      * Should plot "noise" on the Y axis from the simulated DAE
      * Y axis should be named "normalized counts"
      * X axis should be named "mot"
    - The DAE was started and ended once per point
    - The DAE waited for at least 500 good frames at each point
    """
    prefix = get_pv_prefix()
    block = block_rw_rbv(float, "mot")

    controller = RunPerPointController(save_run=False)
    waiter = GoodUahWaiter(0.05)
    dspacing_bin_edges = np.linspace(0.0, 5.0, num=201, dtype=np.float64)
    dspacing_bin_centres = (dspacing_bin_edges[:-1] + dspacing_bin_edges[1:]) / 2

    reducer = DSpacingMappingReducer(
        prefix=prefix,
        detectors=np.arange(1, 18000 + 1),
        two_theta=sc.linspace(
            dim="spec", start=0.1, stop=3.0515926535897926, num=18000, unit=sc.units.rad
        ),
        l_total=sc.linspace(dim="spec", start=0.05, stop=0.5, num=18000, unit=sc.units.m),
        dspacing_bin_edges=sc.array(
            dims=["tof"], values=dspacing_bin_edges, unit=sc.units.angstrom
        ),
    )

    dae = SimpleDae(
        prefix=prefix,
        controller=controller,
        waiter=waiter,
        reducer=reducer,
    )

    yield from ensure_connected(block, dae, force_reconnect=True)

    _, ax = yield from call_qt_aware(plt.subplots)

    @bpp.subs_decorator(
        [
            LivePColorMesh(
                y=block.name,
                x=dae.reducer.dspacing.name,
                x_name="d-spacing",
                x_coord=dspacing_bin_centres,
                ax=ax,
                cmap="hot",
            )
        ]
    )
    def _inner() -> Generator[Msg, None, None]:
        yield from bp.scan([dae], block, 0, 10, num=NUM_POINTS)

    yield from _inner()


if __name__ == "__main__" and not os.environ.get("FROM_IBEX") == "True":
    matplotlib.use("qtagg")
    plt.ion()
    RE = get_run_engine()
    RE(dae_scan_plan())
    input("Plan complete, press return to close plot and exit")

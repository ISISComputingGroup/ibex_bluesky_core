"""Demonstration plan showing basic bluesky functionality."""

import os
from collections.abc import Generator

import bluesky.plans as bp
import lmfit
import matplotlib
import matplotlib.pyplot as plt
import numpy as np
import scipp as sc
from bluesky.utils import Msg
from ophyd_async.plan_stubs import ensure_connected

from ibex_bluesky_core.devices.block import block_rw_rbv
from ibex_bluesky_core.devices.muon import MuonAsymmetryReducer
from ibex_bluesky_core.devices.simpledae import (
    PeriodGoodFramesWaiter,
    RunPerPointController,
    SimpleDae,
)
from ibex_bluesky_core.run_engine import get_run_engine
from ibex_bluesky_core.utils import get_pv_prefix

NUM_POINTS: int = 3


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

    model = lmfit.Model(lambda t, m, c: m * t + c)
    parameters = lmfit.Parameters()
    parameters.add("m", 0)
    parameters.add("c", 0)

    controller = RunPerPointController(save_run=True)
    waiter = PeriodGoodFramesWaiter(500)
    reducer = MuonAsymmetryReducer(
        prefix=prefix,
        forward_detectors=np.array([1, 2, 3, 4]),
        backward_detectors=np.array([5, 6, 7, 8]),
        time_bin_edges=sc.linspace(
            start=180, stop=200, num=100, unit=sc.units.us, dtype="float64", dim="tof"
        ),
        alpha=1.0,
        model=model,
        fit_parameters=parameters,
    )

    dae = SimpleDae(
        prefix=prefix,
        controller=controller,
        waiter=waiter,
        reducer=reducer,
    )

    # Demo giving some signals more user-friendly names
    controller.run_number.set_name("run number")

    yield from ensure_connected(block, dae, force_reconnect=True)

    def _inner() -> Generator[Msg, None, None]:
        yield from bp.scan([dae], block, 0, 10, num=NUM_POINTS)

    yield from _inner()


if __name__ == "__main__" and not os.environ.get("FROM_IBEX") == "True":
    matplotlib.use("qtagg")
    plt.ion()
    RE = get_run_engine()
    RE(dae_scan_plan())
    input("Plan complete, press return to close plot and exit")

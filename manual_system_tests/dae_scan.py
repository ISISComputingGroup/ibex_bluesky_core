"""Demonstration plan showing basic bluesky functionality."""

import os
from collections.abc import Generator
from pathlib import Path

import bluesky.plans as bp
import matplotlib
import matplotlib.pyplot as plt
from bluesky.utils import Msg
from ophyd_async.plan_stubs import ensure_connected

from ibex_bluesky_core.callbacks import ISISCallbacks
from ibex_bluesky_core.devices.block import block_rw_rbv
from ibex_bluesky_core.devices.simpledae import (
    PeriodGoodFramesNormalizer,
    PeriodGoodFramesWaiter,
    RunPerPointController,
    SimpleDae,
)
from ibex_bluesky_core.fitting import Linear
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

    controller = RunPerPointController(save_run=True)
    waiter = PeriodGoodFramesWaiter(500)
    reducer = PeriodGoodFramesNormalizer(
        prefix=prefix,
        detector_spectra=[i for i in range(1, 100)],
    )

    dae = SimpleDae(
        prefix=prefix,
        controller=controller,
        waiter=waiter,
        reducer=reducer,
    )

    # Demo giving some signals more user-friendly names
    controller.run_number.set_name("run number")
    reducer.intensity.set_name("normalized counts")

    yield from ensure_connected(block, dae, force_reconnect=True)

    icc = ISISCallbacks(
        x=block.name,
        y=reducer.intensity.name,
        yerr=reducer.intensity_stddev.name,
        fit=Linear.fit(),
        measured_fields=[
            controller.run_number.name,
            reducer.det_counts.name,
            reducer.det_counts_stddev.name,
            dae.good_frames.name,
        ],
        human_readable_file_output_dir=Path("C:\\")
        / "instrument"
        / "var"
        / "logs"
        / "bluesky"
        / "output_files",
        live_fit_logger_output_dir=Path("C:\\")
        / "instrument"
        / "var"
        / "logs"
        / "bluesky"
        / "fitting",
    )

    @icc
    def _inner() -> Generator[Msg, None, None]:
        yield from bp.scan([dae], block, 0, 10, num=NUM_POINTS)
        print(icc.live_fit.result.fit_report())
        print(f"COM: {icc.peak_stats['com']}")

    yield from _inner()


if __name__ == "__main__" and not os.environ.get("FROM_IBEX") == "True":
    matplotlib.use("qtagg")
    plt.ion()
    RE = get_run_engine()
    RE(dae_scan_plan())
    input("Plan complete, press return to close plot and exit")

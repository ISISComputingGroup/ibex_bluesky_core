"""e.g.
RE(scan("S4VG", -1, 1, 25, frames=20, model=fitting_utils.SlitScan())).
"""

from pathlib import Path

import bluesky.plans as bp
import bluesky.plan_stubs as bps
import bluesky.preprocessors as bpp
import matplotlib
import matplotlib.pyplot as plt
from bluesky.callbacks import LiveFitPlot, LiveTable
from ibex_bluesky_core.devices.block import BlockRw, block_r, block_rw_rbv
from ophyd_async.plan_stubs import ensure_connected

from ibex_bluesky_core.callbacks.file_logger import HumanReadableFileCallback
from ibex_bluesky_core.callbacks.fitting import FitMethod, LiveFit
from ibex_bluesky_core.callbacks.fitting.fitting_utils import Fit, Gaussian
from ibex_bluesky_core.callbacks.fitting.livefit_logger import LiveFitLogger
from ibex_bluesky_core.plans.reflectometry import centred_pixel, refl_parameter, motor_with_tolerance
from ibex_bluesky_core.callbacks.plotting import LivePlot
from ibex_bluesky_core.devices import get_pv_prefix
from ibex_bluesky_core.devices.simpledae import SimpleDae
from ibex_bluesky_core.devices.simpledae.controllers import (
    PeriodPerPointController,
    RunPerPointController,
)
from ibex_bluesky_core.devices.simpledae.reducers import MonitorNormalizer
from ibex_bluesky_core.devices.simpledae.waiters import GoodFramesWaiter, PeriodGoodFramesWaiter
from ibex_bluesky_core.devices.block import block_rw
from ibex_bluesky_core.plan_stubs import call_qt_aware
from ibex_bluesky_core.run_engine import get_run_engine
from ibex_bluesky_core.callbacks import ISISCallbacks as ICC

matplotlib.rcParams["figure.autolayout"] = True
matplotlib.rcParams["font.size"] = 8

RE = get_run_engine()

READABLE_FILE_OUTPUT_DIR = Path("C:\\") / "instrument" / "var" / "logs" / "bluesky" / "output_files"
DEFAULT_DET = 3
DEFAULT_MON = 1

def polref_dae(
    *,
    det_pixels: list[int],
    frames: int,
    periods: bool = True,
    monitor: int = DEFAULT_MON,
    save_run: bool = False,
) -> SimpleDae:
    prefix = get_pv_prefix()

    if periods:
        controller = PeriodPerPointController(save_run=save_run)
        waiter = PeriodGoodFramesWaiter(frames)
    else:
        controller = RunPerPointController(save_run=save_run)
        waiter = GoodFramesWaiter(frames)

    reducer = MonitorNormalizer(
        prefix=prefix,
        detector_spectra=det_pixels,
        monitor_spectra=[monitor],
    )

    dae = SimpleDae(
        prefix=prefix,
        controller=controller,
        waiter=waiter,
        reducer=reducer,
    )

    dae.reducer.intensity.set_name("intensity")  # type: ignore
    dae.reducer.intensity_stddev.set_name("intensity_stddev")  # type: ignore
    return dae


def find_centre_and_move(
    param: str,
    start: float,
    stop: float,
    count: int,
    *,
    frames: int,
    min_step: float,
    max_step: float,
    target_delta: float,
    det: int = DEFAULT_DET,
    mon: int = DEFAULT_MON,
    pixel_range: int = 0,
    fit: FitMethod = Gaussian().fit(),
    periods: bool = True,
    save_run: bool = False,
):
    # block = refl_parameter(param)
    #block = BlockRw(block_name=param, prefix="TE:NDW2452:", datatype=float)
    block = block_rw(float, param)
    block1 = block_r(float, "alice")
    # det_pixels = centred_pixel(det, pixel_range)
    # dae = polref_dae(
    #     det_pixels=det_pixels, frames=frames, periods=periods, save_run=save_run, monitor=mon
    # )

    yield from ensure_connected(block1, block)
    # yield from set_num_periods(dae, count if periods else 1)

    fields = [
        #dae.reducer.intensity.name, # type: ignore
        #dae.reducer.intensity_stddev.name, # type: ignore
        #block1.name
    ]

    # if periods:
    #     fields.append(dae.period_num.name)  # type: ignore
    # elif save_run:
    #     fields.append(dae.controller.run_number.name)  # type: ignore

    _, ax = yield from call_qt_aware(plt.subplots)

    icc = ICC(
        x=block.name,
        y=block1.name, # type: ignore
        #yerr=dae.reducer.intensity_stddev.name, # type: ignore
        measured_fields=fields,
        live_fit_logger_output_dir=READABLE_FILE_OUTPUT_DIR,
        human_readable_file_output_dir=READABLE_FILE_OUTPUT_DIR,
        fields_for_hr_file=fields,
        fit=fit,
        live_fit_logger_postfix="_plan1",
        ax=ax,
    )

    @icc
    def _inner():
        plan = bp.rel_adaptive_scan
        print("TEST")
        yield from bp.rel_adaptive_scan(
            detectors=[block1],
            target_field = block1.name, # type: ignore
            motor=block,
            start=start,
            stop=stop,
            min_step=min_step,
            max_step = max_step,
            target_delta=target_delta,
            backstep=True,
        )

    yield from _inner()

    print(f"Files written to {READABLE_FILE_OUTPUT_DIR}\n")

    if icc.live_fit.result is not None:
        print(icc.live_fit.result.fit_report())
        cen = icc.live_fit.result.values["cen"] # make standard

        bps.mv(block, cen) # type: ignore

    else:
        print("No LiveFit result, likely fit failed")
        return None

### notes

# read operation mode default to NR / disabled
# whats in the beam? read constant PVs
# set initial values to refl params jaws + theta + phi

# we will need two plans
#   one for sample alignment
#   other for beam alignment

def polref_full_auto():

    params = ["bob", "bob", "bob"]

    for param in params:
        yield from find_centre_and_move(param=param, start=-2.0, stop=2.0, count=10, frames=500, min_step=0.01, max_step=0.1, target_delta=0.1)

    # motor list = [a, b, c ,d] in order from beginning of beamline

    # for m in motor list:

        # x = get motor pos of m

        ###############

        # r = something reasonable  
        # x-r ---------- x ---------- x+r
        
        # while r > some much smaller but reasonable range
        
            # start = x - r
            # end = x + r

            # scan over m, from start to end, return centre
            # move motor m to centre

            # make r smaller by some degree to be agreed on

        ############### or 

        # do an adaptive scan that is strict but has high sampling rate on the backstep
        # return centre and move

        ###############

    pass

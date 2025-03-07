from datetime import datetime
from math import isclose
from pathlib import Path
import winsound
from ophyd_async.plan_stubs import ensure_connected
from bluesky.utils import Msg
from collections.abc import Generator
from ibex_bluesky_core.callbacks.fitting.fitting_utils import Gaussian
from ibex_bluesky_core.devices import get_pv_prefix
from ibex_bluesky_core.devices.simpledae import SimpleDae
from ibex_bluesky_core.devices.simpledae.controllers import (
    PeriodPerPointController,
    RunPerPointController,
)
from ibex_bluesky_core.devices.simpledae.reducers import MonitorNormalizer
from ibex_bluesky_core.devices.simpledae.waiters import GoodFramesWaiter, PeriodGoodFramesWaiter
from ibex_bluesky_core.plans import set_num_periods, common_dae
from ibex_bluesky_core.plans.reflectometry import centred_pixel, autoalign_utils
from lmfit.model import ModelResult
import matplotlib.pyplot as plt

PREFIX = get_pv_prefix()
COUNT = 50
FRAMES = 500
READABLE_FILE_OUTPUT_DIR = (
    Path("C:\\") / "instrument" / "var" / "logs" / "bluesky" / "output_files" / ""
)
DEFAULT_DET = 3
DEFAULT_MON = 1
PIXEL_RANGE = 0
PERIODS = True
SAVE_RUN = True


def s1vg_checks(result: ModelResult, param_value: float) -> bool:
    rsquared_confidence = 0.9
    expected_param_value = 1.0
    expected_param_value_tol = 0.1
    max_peak_factor = 5.0

    if result.rsquared < rsquared_confidence:
        return True

    # For the parameter you're optimising, provide a value you would expect for it, assert if its not close by a provided factor
    if not isclose(expected_param_value, param_value, abs_tol=expected_param_value_tol):
        return True

    # Is the peak above the background by some factor (optional because param may not be for a peak, or background may not be a parameter in the model).
    if result.values["background"] / result.model.func(param_value) <= max_peak_factor:
        return True

    return False


parameters = [
    autoalign_utils.AlignmentParam(
        name="S1VG",
        rel_scan_ranges=[0.3],
        fit_method=Gaussian.fit(),
        fit_param="x0",
        do_checks=s1vg_checks,
        pre_align_param_positions={
            "THETA": 0,
            "PHI": 0,
            "S1VG": -0.1,
            "S2VG": 10,
            "S3N": 5,
            "S3S": -5,
            "S1HG": 40,
            "S2HG": 30,
            "S3E": 15,
            "S3W": 15,
        },
    ),
]


def full_autoalign_plan() -> Generator[Msg, None, None]:
    
    det_pixels = centred_pixel(DEFAULT_DET, PIXEL_RANGE)
    dae = common_dae(det_pixels=det_pixels, frames=FRAMES, periods=PERIODS, save_run=SAVE_RUN, monitor=DEFAULT_MON)

    yield from set_num_periods(dae, COUNT if PERIODS else 1)

    axes_sig = [parameters[i].get_signal() for i in range(len(parameters))]
    yield from ensure_connected(*axes_sig, dae)

    print("Starting auto-alignment...")

    for i in range(len(parameters)):
        print(f"Next alignment parameter is {parameters[i].name}")
        winsound.Beep(2500, 200)

        yield from autoalign_utils.optimise_axis_against_intensity(
            dae=dae,
            alignment_param=parameters[i],
            fields=[],
            periods=PERIODS,
            save_run=SAVE_RUN,
            files_output_dir=READABLE_FILE_OUTPUT_DIR,
            callback_if_problem=lambda: winsound.Beep(1000, 500),
            callback_pre_align=lambda: parameters[i].pre_align_params(parameters),
            callback_post_align=lambda: plt.savefig(
                fname=f"{READABLE_FILE_OUTPUT_DIR}{parameters[i].name}_{datetime.now().strftime('%H%M%S')}"
            ),
        )

    print("Auto alignment complete.")

import winsound
from collections.abc import Generator
from datetime import datetime
from math import isclose
from pathlib import Path

import matplotlib.pyplot as plt
from bluesky.utils import Msg
from ibex_bluesky_core.callbacks.fitting.fitting_utils import Gaussian, SlitScan
from ibex_bluesky_core.plan_stubs import call_sync
from ibex_bluesky_core.utils import get_pv_prefix
from ibex_bluesky_core.devices.simpledae import monitor_normalising_dae
from ibex_bluesky_core.plans.reflectometry import autoalign_utils, centred_pixel
from lmfit.model import ModelResult
from ophyd_async.plan_stubs import ensure_connected
from bluesky import plan_stubs as bps

PREFIX = get_pv_prefix()
COUNT = 20
FRAMES = 500
READABLE_FILE_OUTPUT_DIR = (
    Path("C:\\") / "instrument" / "var" / "logs" / "bluesky" / "output_files" / ""
)
DEFAULT_DET = 280
DEFAULT_MON = 2
PIXEL_RANGE = 5
PERIODS = True
SAVE_RUN = True
NUM_POINTS = 21


def s1vg_checks(result: ModelResult, fit_param: str) -> bool:

    alignment_param_value = result.values[fit_param]

    rsquared_confidence = 0.9
    expected_param_value = 1.0
    expected_param_value_tol = 0.1
    max_peak_factor = 5.0

    if result.rsquared < rsquared_confidence:
        return True

    # For S1VG, provide a value you would expect for it,
    # assert if its not close by a provided factor
    if not isclose(expected_param_value, alignment_param_value, abs_tol=expected_param_value_tol):
        return True

    # Is the peak above the background by some factor (optional because param may not be for
    # a peak, or background may not be a parameter in the model).
    if result.values["background"] / result.model.func(alignment_param_value) <= max_peak_factor:
        return True

    return False


parameters = [
    autoalign_utils.AlignmentParam(
        name="S1VG",
        rel_scan_ranges=[0.3, 0.05],
        fit_method=SlitScan.fit(),
        fit_param="inflection0",
        check_func=s1vg_checks,
        pre_align_param_positions={
            "THETA": 0,
            "PHI": 0,
            "S1VG": -0.1, # 0.2?
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
    dae = monitor_normalising_dae(
        det_pixels=det_pixels,
        frames=FRAMES,
        periods=PERIODS,
        save_run=SAVE_RUN,
        monitor=DEFAULT_MON,
    )

    yield from bps.mv(dae.number_of_periods, COUNT if PERIODS else 1)  # type: ignore

    axes_sig = [parameters[i].get_movable() for i in range(len(parameters))]
    yield from ensure_connected(*axes_sig, dae) #  type: ignore

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
            num_points=NUM_POINTS,
            files_output_dir=READABLE_FILE_OUTPUT_DIR,
            problem_found_plan=lambda: call_sync(winsound.Beep, 1000, 500),
            pre_align_plan=lambda: parameters[i].pre_align_params(parameters),
            post_align_plan=lambda: call_sync(plt.savefig, 
                fname=f"{READABLE_FILE_OUTPUT_DIR}{parameters[i].name}_{datetime.now().strftime('%H%M%S')}"
            ),
        )

    print("Auto alignment complete.")

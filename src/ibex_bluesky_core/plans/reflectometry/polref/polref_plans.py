from math import isclose
from pathlib import Path
import winsound
import bluesky.plan_stubs as bps
from ophyd_async.plan_stubs import ensure_connected
from bluesky.utils import Msg
from collections.abc import Generator
from ophyd_async.epics.core import epics_signal_r
from ibex_bluesky_core.callbacks.fitting import FitMethod
from ibex_bluesky_core.callbacks.fitting.fitting_utils import Gaussian
from ibex_bluesky_core.devices import get_pv_prefix
from ibex_bluesky_core.devices.simpledae import SimpleDae
from ibex_bluesky_core.devices.simpledae.controllers import (
    PeriodPerPointController,
    RunPerPointController,
)
from ibex_bluesky_core.devices.simpledae.reducers import MonitorNormalizer
from ibex_bluesky_core.devices.simpledae.waiters import GoodFramesWaiter, PeriodGoodFramesWaiter
from ibex_bluesky_core.plans import set_num_periods
from ibex_bluesky_core.plans.reflectometry import centred_pixel, refl_parameter, autoalign_utils
from functools import partial
from lmfit.model import ModelResult

PREFIX = get_pv_prefix()
COUNT = 50
FRAMES = 500
READABLE_FILE_OUTPUT_DIR = Path("C:\\") / "instrument" / "var" / "logs" / "bluesky" / "output_files"
DEFAULT_DET = 3
DEFAULT_MON = 1
PIXEL_RANGE = 0
PERIODS = True
SAVE_RUN = True

####################


def get_dae(
    *,
    det_pixels: list[int],
    frames: int,
    periods: bool = True,
    monitor: int = DEFAULT_MON,
    save_run: bool = False,
) -> SimpleDae:
    if periods:
        controller = PeriodPerPointController(save_run=save_run)
        waiter = PeriodGoodFramesWaiter(frames)
    else:
        controller = RunPerPointController(save_run=save_run)
        waiter = GoodFramesWaiter(frames)

    reducer = MonitorNormalizer(
        prefix=PREFIX,
        detector_spectra=det_pixels,
        monitor_spectra=[monitor],
    )

    dae = SimpleDae(
        prefix=PREFIX,
        controller=controller,
        waiter=waiter,
        reducer=reducer,
    )

    dae.reducer.intensity.set_name("intensity")  # type: ignore
    dae.reducer.intensity_stddev.set_name("intensity_stddev")  # type: ignore
    return dae


#################### ^^ above to be removed

def theta_checks(result: ModelResult, param_value: float) -> bool:

    rsquared_confidence = 0.9
    expected_param_value = 1.0
    expected_param_value_tol = 0.1 
    max_peak_factor = 5.0

    if result.rsquared < rsquared_confidence:
        return False
    
    # For the parameter you're optimising, provide a value you would expect for it, assert if its not close by a provided factor
    if not isclose(expected_param_value, param_value, abs_tol=expected_param_value_tol):
        return False
        
    # Is the peak above the background by some factor (optional because param may not be for a peak, or background may not be a parameter in the model).
    if result.values["background"] / result.model.func(param_value) <= max_peak_factor:
        return False
    
    return True


parameters = [
    autoalign_utils.AlignmentParam("theta", 5, Gaussian.fit(), "x0", 0.0, do_checks=theta_checks),
    # add when one beamline?
]


def pre_align_plan() -> Generator[Msg, None, None]:
    """Move all given axes to their default positions at the same time."""

    mode = epics_signal_r(str, f"{PREFIX}REFL_01:CONST:IS_HORIZONTAL", name="refl_mode")
    if (yield from bps.read(mode)) != "YES":
        return

    axes_sig = [parameters[i].get_device() for i in range(len(parameters))]
    yield from ensure_connected(*axes_sig)

    print("Moving the following axes to their initial positions...")
    print(*axes_sig)
    yield from autoalign_utils.pre_align(parameters)


def full_autoalign_plan() -> Generator[Msg, None, None]:
    det_pixels = centred_pixel(DEFAULT_DET, PIXEL_RANGE)
    dae = get_dae(
        det_pixels=det_pixels,
        frames=FRAMES,
        periods=PERIODS,
        save_run=SAVE_RUN,
        monitor=DEFAULT_MON,
    )

    yield from set_num_periods(dae, COUNT if PERIODS else 1)

    axes_sig = [parameters[i].get_device() for i in range(len(parameters))]
    yield from ensure_connected(*axes_sig, dae)

    print("Starting auto-alignment...")

    for i in range(len(parameters)):
        print(f"Next axis is {parameters[i].name}")
        winsound.Beep(2500, 200)

        yield from autoalign_utils.optimise_axis_against_intensity(
            dae=dae,
            device=parameters[i].get_device(),
            fit=parameters[i].fit_method,
            optimised_param=parameters[i].fit_param,
            rel_scan_range=parameters[i].rel_scan_range,
            fields=[],
            periods=PERIODS,
            save_run=SAVE_RUN,
            files_output_dir=READABLE_FILE_OUTPUT_DIR,
            callback_if_problem=partial(winsound.Beep, 1000, 500),
        )


def sample_autoalign_plan():
    pass

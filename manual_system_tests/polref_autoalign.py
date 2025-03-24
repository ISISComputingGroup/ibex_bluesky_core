"""Auto-alignment scripts for POLREF reflectometer."""
from typing import TypeAlias, Callable

from collections.abc import Generator
from datetime import datetime
from math import isclose

import winsound
from ophyd_async.epics.motor import Motor
from winsound import Beep

from bluesky import plan_stubs as bps
from bluesky.utils import Msg
from lmfit.model import ModelResult
from matplotlib import pyplot as plt
from ophyd_async.plan_stubs import ensure_connected

from ibex_bluesky_core.callbacks.fitting.fitting_utils import SlitScan, Trapezoid, Gaussian, ERFC
from ibex_bluesky_core.devices.block import BlockMot, block_rw, BlockWriteConfig
from ibex_bluesky_core.devices.reflectometry import ReflParameter, refl_parameter
from ibex_bluesky_core.devices.simpledae import SimpleDae, monitor_normalising_dae, \
    PeriodGoodFramesWaiter, GoodFramesWaiter, MonitorNormalizer, Controller, \
    PeriodPerPointController, RunPerPointController
from ibex_bluesky_core.log import set_bluesky_log_levels
from ibex_bluesky_core.plan_stubs import call_sync, redefine_refl_parameter, redefine_motor
from ibex_bluesky_core.plans.reflectometry import centred_pixel, optimise_axis_against_intensity
from ibex_bluesky_core.utils import get_pv_prefix
from ibex_bluesky_core.callbacks._utils import get_default_output_path

PREFIX = get_pv_prefix()
DEFAULT_DET = 280
DEFAULT_MON = 2
PIXEL_RANGE = 5
NUM_POINTS = 21

set_bluesky_log_levels("DEBUG")


def save_plt(movable_name: str):
    plt.savefig(fname=f"{get_default_output_path()}{movable_name}_plot_{datetime.now().strftime('%H%M%S')}")


def gaussian_checks(*, rsquared: float) -> Callable[[ModelResult, float], bool]:
    def _checks(result: ModelResult, alignment_param_value: float) -> bool:
        """Check for optimised S1VG value."""
        rsquared_confidence = rsquared
        expected_param_value = 1.0
        expected_param_value_tol = 0.1
        max_peak_factor = 5.0

        if result.rsquared < rsquared_confidence:
            return True

        # Is the peak above the background by some factor (optional because param may not be for
        # a peak, or background may not be a parameter in the model).
        if result.values["background"] / result.model.func(alignment_param_value) <= max_peak_factor:
            return True

        return False

    return _checks


S1VG = refl_parameter(name="S1VG")
S1HG = refl_parameter(name="S1HG")
S2VG = refl_parameter(name="S2VG")
S2HG = refl_parameter(name="S2HG")
S3VG = refl_parameter(name="S3VG")
S2OFFSET = refl_parameter(name="S2OFFSET")
BENCHSEESAW = refl_parameter(name="BENCHSEESA")
BENCHOFFSET = refl_parameter(name="BENCHOFFSE")
S3VC = refl_parameter(name="S3HEIGHT")
THETA = refl_parameter(name="THETA", has_redefine=False)
PHI = refl_parameter(name="SAMPPHI")
FOFFSET = refl_parameter(name="FOFFSET")
FTHETA = refl_parameter(name="FTHETA")
SMOFFSET = refl_parameter(name="SMOFFSET")
SMANGLE = refl_parameter(name="SMANGLE")
HEIGHT = refl_parameter(name="SAMPOFFSET")

MODE = block_rw(str, "MODE", write_config=BlockWriteConfig(use_global_moving_flag=True, settle_time_s=2))
MOVE = block_rw(int, "MOVE", write_config=BlockWriteConfig(use_global_moving_flag=True, settle_time_s=2), sp_suffix="")

SMINBEAM = block_rw(str, "SMINBEAM", write_config=BlockWriteConfig(use_global_moving_flag=True, settle_time_s=2))

S3SOUTH = Motor(name="S3SOUTH", prefix=get_pv_prefix() + "MOT:MTR0601")
S3NORTH = Motor(name="S3NORTH", prefix=get_pv_prefix() + "MOT:MTR0602")
S3EAST = Motor(name="S3EAST", prefix=get_pv_prefix() + "MOT:MTR0603")
S3WEST = Motor(name="S3WEST", prefix=get_pv_prefix() + "MOT:MTR0604")
SLIT2Z_RAW = Motor(name="SLIT2Z_RAW", prefix = get_pv_prefix() + "MOT:MTR0402")

PolrefDae: TypeAlias = SimpleDae[PeriodPerPointController | RunPerPointController, PeriodGoodFramesWaiter | GoodFramesWaiter, MonitorNormalizer]


def beep():
    for i in range (1000, 8000, 1000):
        yield from call_sync(Beep, i, 100)
    yield from call_sync(winsound.PlaySound, r"C:\Users\luj96656\Downloads\happy-goat-6463.wav", winsound.SND_FILENAME)


def change_mode(mode: str):
    yield from bps.mv(MODE, mode)

    sm_out_options = ["NR", "ANR"]
    sm_in_options = ["PNR", "PA"]
    other_options = ["DISABLED"]

    if mode in sm_out_options:
        yield from bps.mv(SMINBEAM, "OUT")
        yield from bps.mv(SMANGLE, 0.0)
        yield from bps.mv(MOVE, 1)
        yield from bps.mv(HEIGHT, 0.0)
    elif mode in other_options:
        pass
    elif mode in sm_in_options:
        yield from bps.mv(SMINBEAM, "IN")
        yield from bps.mv(SMANGLE, 0.55)
        yield from bps.mv(MOVE, 1)
        yield from bps.mv(HEIGHT, 0.0)
    else:
        raise ValueError(f"Mode name '{mode}' not recognised")


def next_param(name: str):
    print(f"Next alignment parameter is {name}")
    yield from beep()


def _optimise_axis(dae, frames, param, fit, fit_param: str, rel_scan_ranges: list[float], num):
    yield from bps.mv(dae.waiter.finish_wait_at, frames)
    yield from optimise_axis_against_intensity(
        dae=dae,
        alignment_param=param,
        fit_method=fit,
        fit_param=fit_param,
        rel_scan_ranges=rel_scan_ranges,
        # is_good_fit=,
        periods=True,
        save_run=True,
        num_points=num,
        problem_found_plan=beep
    )
    save_plt(param.name)

def initial_move(theta=0.5, phi=0.5,
                  s1vg=None, s2vg=None, s3n=None, s3s=None,
                  s1hg=None, s2hg=None, s3e=None, s3w=None):
    moves = []
    if theta is not None:
        moves.extend([THETA, theta])
    if phi is not None:
        moves.extend([PHI, phi])
    if s1vg is not None:
        moves.extend([S1VG, s1vg])
    if s2vg is not None:
        moves.extend([S2VG, s2vg])
    if s3n is not None:
        moves.extend([S3NORTH, s3n])
    if s3s is not None:
        moves.extend([S3SOUTH, s3s])
    if s1hg is not None:
        moves.extend([S1HG, s1hg])
    if s2hg is not None:
        moves.extend([S2HG, s2hg])
    if s3e is not None:
        moves.extend([S3EAST, s3e])
    if s3w is not None:
        moves.extend([S3WEST, s3w])

    yield from bps.mv(*moves)


def s1vg_align(dae: PolrefDae) -> Generator[Msg, None, None]:
    yield from next_param(S1VG.name)
    yield from initial_move(theta=0, phi=0, s1vg=-0.1, s2vg=10, s3n=5, s3s=-5, s1hg=40, s2hg=30, s3e=15, s3w=15)

    yield from _optimise_axis(
        dae=dae,
        frames=10,
        param=S1VG,
        fit=SlitScan.fit(),
        fit_param="inflection0",
        rel_scan_ranges=[0.6, 0.1, 0.1],
        num=21
    )

    yield from redefine_refl_parameter(S1VG, 0.0)


def s2vg_align(dae: PolrefDae) -> Generator[Msg, None, None]:
    yield from next_param(S2VG.name)
    yield from initial_move(theta=0, phi=0, s1vg=1.0, s2vg=-0.1, s3n=5, s3s=-5, s1hg=40, s2hg=30, s3e=15, s3w=15)

    yield from _optimise_axis(
        dae=dae,
        frames=10,
        param=S2VG,
        fit=SlitScan.fit(),
        fit_param="inflection0",
        rel_scan_ranges=[0.3],
        num=21,
    )

    yield from _optimise_axis(
        dae=dae,
        frames=20,
        param=S2VG,
        fit=SlitScan.fit(),
        fit_param="inflection0",
        rel_scan_ranges=[0.2, 0.2],
        num=21,
    )

    yield from redefine_refl_parameter(S2VG, 0.0)


def s3vg_align(dae: PolrefDae) -> Generator[Msg, None, None]:
    yield from next_param(S3VG.name)
    yield from initial_move(theta=0, phi=0, s1vg=1.0, s2vg=1.0, s3n=-0.1, s3s=0.1, s1hg=40, s2hg=30, s3e=15, s3w=15)

    yield from _optimise_axis(
        dae=dae,
        frames=10,
        param=S3VG,
        fit=SlitScan.fit(),
        fit_param="inflection0",
        rel_scan_ranges=[2],
        num=21,
    )
    yield from _optimise_axis(
        dae=dae,
        frames=20,
        param=S3VG,
        fit=SlitScan.fit(),
        fit_param="inflection0",
        rel_scan_ranges=[0.2, 0.2],
        num=21,
    )

    yield from redefine_refl_parameter(S3VG, 0.0)


def s2offset_align(dae: PolrefDae) -> Generator[Msg, None, None]:
    yield from next_param(S2OFFSET.name)
    yield from initial_move(theta=0, phi=0, s1vg=0.1, s2vg=0.1, s3n=15, s3s=-15, s1hg=40, s2hg=30, s3e=15, s3w=15)

    yield from _optimise_axis(
        dae=dae,
        frames=20,
        param=S2OFFSET,
        fit=Trapezoid.fit(),
        fit_param="cen",
        rel_scan_ranges=[10, 5, 5],
        num=31,
    )

    yield from redefine_refl_parameter(S2OFFSET, 0.0)

def benchseesaw_align(dae: PolrefDae) -> Generator[Msg, None, None]:
    yield from next_param(BENCHSEESAW.name)
    yield from initial_move(theta=0, phi=0, s1vg=0.1, s2vg=0.1, s3n=15, s3s=-15, s1hg=40, s2hg=30, s3e=15, s3w=15)

    yield from _optimise_axis(
        dae=dae,
        frames=120,
        param=BENCHSEESAW,
        fit=Gaussian.fit(),
        fit_param="x0",
        rel_scan_ranges=[2],
        num=21,
    )

    yield from redefine_refl_parameter(BENCHSEESAW, 0.0)

def benchoffset_align(dae: PolrefDae) -> Generator[Msg, None, None]:
    yield from next_param(BENCHOFFSET.name)
    yield from initial_move(theta=0, phi=0, s1vg=0.1, s2vg=0.1, s3n=15, s3s=-15, s1hg=40, s2hg=30, s3e=15, s3w=15)

    yield from _optimise_axis(
        dae=dae,
        frames=80,
        param=BENCHOFFSET,
        fit=Gaussian.fit(),
        fit_param="x0",
        rel_scan_ranges=[2],
        num=21,
    )

    yield from redefine_refl_parameter(BENCHOFFSET, 0.0)

def s3vc_align(dae: PolrefDae) -> Generator[Msg, None, None]:
    yield from next_param(S3VC.name)
    yield from initial_move(theta=0, phi=0, s1vg=0.1, s2vg=0.1, s3n=0.1, s3s=-0.1, s1hg=40, s2hg=30, s3e=15, s3w=15)

    yield from _optimise_axis(
        dae=dae,
        frames=20,
        param=S3VC,
        fit=Gaussian.fit(),
        fit_param="x0",
        rel_scan_ranges=[4],
        num=31,
    )

    for _ in range(2):
        yield from _optimise_axis(
            dae=dae,
            frames=60,
            param=S3VC,
            fit=Gaussian.fit(),
            fit_param="x0",
            rel_scan_ranges=[0.8],
            num=21,
        )

        yield from bps.mv(S3VG, 0)

        yield from redefine_motor(S3NORTH, 0)
        yield from redefine_motor(S3SOUTH, 0)

        yield from bps.mv(S3VG, 0.2)

def foffset_align(dae: PolrefDae) -> Generator[Msg, None, None]:
    yield from initial_move(theta=0, phi=0, s1vg=0.1, s2vg=0.1, s3n=0.1, s3s=-0.1, s1hg=40, s2hg=30, s3e=15, s3w=15)
    yield from bps.mv(FTHETA, 0, FOFFSET, 29.875)

    yield from _optimise_axis(
        dae=dae,
        frames=120,
        param=FOFFSET,
        rel_scan_ranges=[0.75],
        fit=ERFC.fit(),
        fit_param="cen",
        num=15
    )
    yield from redefine_refl_parameter(FOFFSET, 30)
    yield from bps.mv(FTHETA, 5.8)

def ftheta_align(dae:PolrefDae) -> Generator[Msg, None, None]:
    yield from initial_move(theta=0, phi=0, s1vg=0.1, s2vg=0.1, s3n=0.1, s3s=-0.1, s1hg=40, s2hg=30, s3e=15, s3w=15)
    yield from bps.mv(FTHETA, 0, FOFFSET, 30)

    yield from _optimise_axis(
        dae=dae,
        frames=120,
        param=FTHETA,
        rel_scan_ranges=[0.6],
        fit=Gaussian.fit(),
        fit_param="x0",
        num=15
    )
    yield from redefine_refl_parameter(FTHETA, 0)

    yield from _optimise_axis(
        dae=dae,
        frames=120,
        param=FTHETA,
        rel_scan_ranges=[0.3],
        fit=Gaussian.fit(),
        fit_param="x0",
        num=15
    )
    yield from redefine_refl_parameter(FTHETA, 0)

    yield from _optimise_axis(
        dae=dae,
        frames=200,
        param=FTHETA,
        rel_scan_ranges=[0.2],
        fit=Gaussian.fit(),
        fit_param="x0",
        num=21
    )
    yield from redefine_refl_parameter(FTHETA, 0)
    yield from bps.mv(FTHETA, 5.8)


def sm_align_setup() -> Generator[Msg, None, None]:
    yield from initial_move(theta=0, phi=0, s1vg=0.2, s2vg=0.2, s3n=5, s3s=-5, s1hg=40, s2hg=30, s3e=15, s3w=15)
    yield from bps.mv(SMINBEAM, "IN")
    yield from bps.mv(SMANGLE, 0.0)
    yield from change_mode("DISABLED")

def smoffset_align(dae: PolrefDae) -> Generator[Msg, None, None]:
    yield from initial_move(theta=0, phi=0, s1vg=0.2, s2vg=0.2, s3n=5, s3s=-5, s1hg=40, s2hg=30, s3e=15, s3w=15)
    yield from _optimise_axis(
        dae, frames=120, rel_scan_ranges=[1], param=SMOFFSET, fit=ERFC.fit(), fit_param="cen", num=21,
    )
    yield from redefine_refl_parameter(SMOFFSET, 0)

def smangle_align(dae: PolrefDae) -> Generator[Msg, None, None]:
    yield from initial_move(theta=0, phi=0, s1vg=0.2, s2vg=0.2, s3n=5, s3s=-5, s1hg=40, s2hg=30, s3e=15, s3w=15)
    yield from _optimise_axis(dae, frames=120, param=SMANGLE, rel_scan_ranges=[0.2], fit=Gaussian.fit(), fit_param="x0", num=21)
    yield from redefine_refl_parameter(SMANGLE, 0)

def pnr_setup() -> Generator[Msg, None, None]:
    yield from initial_move(theta=0, phi=0, s1vg=0.2, s2vg=0.2, s3n=5, s3s=-5, s1hg=40, s2hg=30, s3e=15, s3w=15)
    yield from bps.mv(HEIGHT, 0.0)
    yield from change_mode("PNR")

def s2offset_pnr_align(dae: PolrefDae) -> Generator[Msg, None, None]:
    yield from initial_move(theta=0, phi=0, s1vg=0.1, s2vg=0.1, s3n=15, s3s=-15, s1hg=40, s2hg=30, s3e=15, s3w=15)
    yield from _optimise_axis(dae, frames=80, param=S2OFFSET, rel_scan_ranges=[10], fit=Gaussian.fit(), fit_param="x0", num=21)
    yield from _optimise_axis(dae, frames=80, param=S2OFFSET, rel_scan_ranges=[6, 6],
                              fit=Gaussian.fit(), fit_param="x0", num=31)
    s2_pnr_offset = yield from bps.rd(SLIT2Z_RAW)
    print("S2 PNR OFFSET = ", s2_pnr_offset - 56.614)


def full_autoalign_plan() -> Generator[Msg, None, None]:
    """Full autoalign plan for POLREF."""
    det_pixels = centred_pixel(DEFAULT_DET, PIXEL_RANGE)
    dae: PolrefDae = monitor_normalising_dae(
        det_pixels=det_pixels,
        frames=10,
        periods=True,
        save_run=True,
        monitor=DEFAULT_MON,
    )

    yield from bps.mv(dae.waiter.finish_wait_at, 500)

    yield from ensure_connected(
        dae, S1VG, S1HG, S2VG, S2HG, S3VG, S2OFFSET,
        BENCHSEESAW, BENCHOFFSET, S3VC, FOFFSET,
        FTHETA, SMOFFSET, SMANGLE, S3NORTH, S3SOUTH, S3EAST, S3WEST, THETA,
        PHI, SMINBEAM, MODE, MOVE, SLIT2Z_RAW
    )

    print("Starting auto-alignment...")

    # yield from s1vg_align(dae=dae)
    # yield from s2vg_align(dae=dae)
    # yield from s3vg_align(dae=dae)
    # yield from s2offset_align(dae=dae)
    #
    # for _ in range(3):
    #     yield from benchseesaw_align(dae=dae)
    #     yield from benchoffset_align(dae=dae)
    #
    # yield from s3vg_align(dae=dae)
    # yield from s3vc_align(dae=dae)
    #
    # yield from foffset_align(dae=dae)
    # yield from ftheta_align(dae=dae)
    # yield from foffset_align(dae=dae)
    yield from sm_align_setup()
    for _ in range(2):
        yield from smoffset_align(dae=dae)
        yield from smangle_align(dae=dae)
    yield from pnr_setup()


    # Other params
    # ....

    print("Auto alignment complete.")


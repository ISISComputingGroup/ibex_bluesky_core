"""Demonstration plan showing basic bluesky functionality."""

from collections.abc import Generator
from pathlib import Path

import bluesky.plan_stubs as bps
import bluesky.plans as bp
import bluesky.preprocessors as bpp
import matplotlib.pyplot as plt
from bluesky.callbacks import LiveFitPlot, LiveTable
from bluesky.callbacks.fitting import PeakStats
from bluesky.plan_stubs import trigger_and_read
from bluesky.preprocessors import finalize_wrapper, run_decorator, subs_decorator
from bluesky.utils import Msg
from ophyd_async.plan_stubs import ensure_connected

from ibex_bluesky_core.callbacks.file_logger import HumanReadableFileCallback
from ibex_bluesky_core.callbacks.fitting import FitMethod, LiveFit
from ibex_bluesky_core.callbacks.fitting.fitting_utils import Linear, Trapezoid
from ibex_bluesky_core.callbacks.plotting import LivePlot
from ibex_bluesky_core.devices import get_pv_prefix
from ibex_bluesky_core.devices.block import BlockMot, BlockWriteConfig, block_mot, block_r, block_rw
from ibex_bluesky_core.devices.simpledae import SimpleDae
from ibex_bluesky_core.devices.simpledae.controllers import (
    PeriodPerPointController,
    RunPerPointController,
)
from ibex_bluesky_core.devices.simpledae.reducers import MonitorNormalizer
from ibex_bluesky_core.devices.simpledae.waiters import GoodFramesWaiter, PeriodGoodFramesWaiter
from ibex_bluesky_core.plan_stubs import call_qt_aware

NUM_POINTS: int = 3
DEFAULT_DET = 3
DEFAULT_MON = 1
READABLE_FILE_OUTPUT_DIR = Path("C:\\") / "instrument" / "var" / "logs" / "bluesky" / "output_files"
DEFAULT_FIT_METHOD = Linear().fit()


def continuous_scan_plan(
    mot_block: BlockMot, centre: float, size: float, time: float, iterations: int
) -> Generator[Msg, None, None]:
    """Continuous scan plan for scanning a motor against a laser diode readback.
    time is given as the time taken for one 'sweep' for the total size (width).

    """
    motor = mot_block

    laser_intensity = block_r(float, "changer_scan_intensity")
    _, ax = plt.subplots()
    lf = LiveFit(Trapezoid.fit(), y=laser_intensity.name, x=motor.name)

    initial_position = centre - 0.5 * size
    final_position = centre + 0.5 * size

    yield from ensure_connected(
        laser_intensity,
        motor,
    )
    initial_velocity = yield from bps.rd(motor.velocity)

    @subs_decorator(
        [
            HumanReadableFileCallback(
                output_dir=Path("C:\\") / "instrument" / "var" / "logs" / "bluesky" / "output_files",
                fields=[motor.name, laser_intensity.name],
            ),
            LiveFitPlot(livefit=lf, ax=ax),
            LivePlot(
                y=laser_intensity.name,
                x=motor.name,
                marker="x",
                linestyle="none",
                ax=ax,
            ),
        ]
    )
    @run_decorator(md={})
    def _inner() -> Generator[Msg, None, None]:
        def polling_plan(destination: float):
            yield from bps.checkpoint()
            yield from bps.create()
            reading = yield from bps.read(motor)
            yield from bps.read(laser_intensity)
            yield from bps.save()

            # start the ramp
            status = yield from bps.abs_set(motor, destination, wait=False)
            while not status.done:
                yield from bps.create()
                new_reading = yield from bps.read(motor)
                yield from bps.read(laser_intensity)

                if new_reading[motor.name]["value"] == reading[motor.name]["value"]:
                    yield from bps.drop()
                else:
                    reading = new_reading
                    yield from bps.save()

            # take a 'post' data point
            yield from trigger_and_read([motor, laser_intensity])

        yield from bps.mv(motor, initial_position)
        yield from bps.mv(motor.velocity, size / time)
        for _i in range(iterations):
            yield from polling_plan(final_position)
            yield from polling_plan(initial_position)

    def _set_motor_back_to_original_velocity():
        yield from bps.mv(motor.velocity, initial_velocity)

    yield from finalize_wrapper(_inner(), _set_motor_back_to_original_velocity)
    return lf.result


def loq_dae(
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


def set_num_periods(dae: SimpleDae, nperiods: int):
    yield from bps.mv(dae.number_of_periods, nperiods)  # type: ignore
    actual = yield from bps.rd(dae.number_of_periods)
    if actual != nperiods:
        raise ValueError(
            f"Could not set {nperiods} periods on DAE (probably requesting too many points, or already running)"
        )


def scan(
    block_name: str,
    start: float,
    stop: float,
    count: int,
    *,
    frames: int,
    det: int = DEFAULT_DET,
    mon: int = DEFAULT_MON,
    model: FitMethod = DEFAULT_FIT_METHOD,
    periods: bool = True,
    save_run: bool = False,
    rel: bool = False,
):
    block = block_rw(float, block_name, write_config=BlockWriteConfig(use_global_moving_flag=True))
    dae = loq_dae(det_pixels=[det], frames=frames, periods=periods, save_run=save_run, monitor=mon)

    yield from ensure_connected(dae, block)

    yield from set_num_periods(dae, count if periods else 1)

    yield from call_qt_aware(plt.close, "all")
    _, ax = yield from call_qt_aware(plt.subplots)

    livefit = LiveFit(
        model,
        y=dae.reducer.intensity.name,
        yerr=dae.reducer.intensity_stddev.name,
        x=block.name,  # type: ignore
    )

    fields = [block.name]
    if periods:
        fields.append(dae.period_num.name)  # type: ignore
    elif save_run:
        fields.append(dae.controller.run_number.name)  # type: ignore

    fields.extend(
        [
            dae.reducer.intensity.name,  # type: ignore
            dae.reducer.intensity_stddev.name,  # type: ignore
        ]
    )

    peak_stats = PeakStats(x=block.name, y=dae.reducer.intensity.name)  # type: ignore

    @bpp.subs_decorator(
        [
            HumanReadableFileCallback(output_dir=READABLE_FILE_OUTPUT_DIR, fields=fields),
            LivePlot(
                y=dae.reducer.intensity.name,  # type: ignore
                yerr=dae.reducer.intensity_stddev.name,  # type: ignore
                x=block.name,
                marker="x",
                linestyle="none",
                ax=ax,
            ),
            LiveFitPlot(livefit, ax=ax),
            LiveTable(fields),
            peak_stats,
        ]
    )
    def _inner():
        if rel:
            plan = bp.rel_scan
        else:
            plan = bp.scan
        yield from plan([dae], block, start, stop, num=count)

    yield from _inner()

    print(f"Files written to {READABLE_FILE_OUTPUT_DIR}\n")
    print(f"Centre-of-mass from PeakStats: {peak_stats['com']}\n")

    if livefit.result is not None:
        print(livefit.result.fit_report())
        return livefit.result.params
    else:
        print("No LiveFit result, likely fit failed")
        return None


def adaptive_scan(
    block_name: str,
    start: float,
    stop: float,
    min_step: float,
    max_step: float,
    target_delta: float,
    *,
    frames: int,
    det: int = DEFAULT_DET,
    mon: int = DEFAULT_MON,
    model: FitMethod = Linear().fit(),
    periods: bool = True,
    save_run: bool = False,
    rel: bool = False,
):
    block = block_rw(float, block_name, write_config=BlockWriteConfig(use_global_moving_flag=True))
    dae = loq_dae(det_pixels=[det], frames=frames, periods=periods, save_run=save_run, monitor=mon)

    yield from ensure_connected(dae, block)

    yield from set_num_periods(dae, 100)

    yield from call_qt_aware(plt.close, "all")
    _, ax = yield from call_qt_aware(plt.subplots)

    livefit = LiveFit(
        model,
        y=dae.reducer.intensity.name,
        yerr=dae.reducer.intensity_stddev.name,
        x=block.name,  # type: ignore
    )

    fields = [block.name]
    if periods:
        fields.append(dae.period_num.name)  # type: ignore
    elif save_run:
        fields.append(dae.controller.run_number.name)  # type: ignore

    fields.extend(
        [
            dae.reducer.intensity.name,  # type: ignore
            dae.reducer.intensity_stddev.name,  # type: ignore
        ]
    )

    peak_stats = PeakStats(x=block.name, y=dae.reducer.intensity.name)  # type: ignore

    @bpp.subs_decorator(
        [
            HumanReadableFileCallback(output_dir=READABLE_FILE_OUTPUT_DIR, fields=fields),
            LivePlot(
                y=dae.reducer.intensity.name,  # type: ignore
                yerr=dae.reducer.intensity_stddev.name,  # type: ignore
                x=block.name,
                marker="x",
                linestyle="none",
                ax=ax,
            ),
            LiveFitPlot(livefit, ax=ax),
            LiveTable(fields),
            peak_stats,
        ]
    )
    def _inner():
        if rel:
            plan = bp.rel_adaptive_scan
        else:
            plan = bp.adaptive_scan
        yield from plan(
            [dae],
            dae.reducer.intensity.name,
            block,
            start,
            stop,
            min_step,
            max_step,
            target_delta,
            backstep=True,
        )  # type: ignore

    yield from _inner()

    print(f"Files written to {READABLE_FILE_OUTPUT_DIR}\n")
    print(f"Centre-of-mass from PeakStats: {peak_stats['com']}\n")

    if livefit.result is not None:
        print(livefit.result.fit_report())
        return livefit.result.params
    else:
        print("No LiveFit result, likely fit failed")
        return None


def sample_changer_scan(position: str, width: float = 22, time: float = 20, iterations: int = 1):
    changer_position = block_rw(
        str, "Changer", write_config=BlockWriteConfig(use_global_moving_flag=True)
    )
    motor = block_mot("sample_changer_scan_axis")
    offset = block_rw(float, "Offset")

    yield from ensure_connected(motor, offset, changer_position)
    yield from bps.mv(changer_position, position)
    current_position = yield from bps.rd(motor)

    result = yield from continuous_scan_plan(motor, current_position, width, time, iterations)

    print(result.fit_report())

    centre = result.params["cen"]

    print(f"Centre:  {centre}")

    current_offset = yield from bps.rd(offset)

    print(f"Current offset: {current_offset}")

    new_offset = current_offset + (centre - current_position)

    print(f"Suggested new offset: {new_offset}")
    print("Add this value in the Dynamic Offsets SAMPLE offset box on the TRANSLATION STAGE OPI")

    yield from bps.mv(changer_position, position)


def aperture_continuous_scan(
    position: str, width: float = 22, time: float = 30, iterations: int = 1
):
    changer_position = block_rw(
        str, "Aperture_2", write_config=BlockWriteConfig(use_global_moving_flag=True)
    )
    motor = block_mot("aperture_scan_axis")

    yield from ensure_connected(motor, changer_position)
    yield from bps.mv(changer_position, position)
    current_position = yield from bps.rd(motor)

    result = yield from continuous_scan_plan(motor, current_position, width, time, iterations)

    print(result.fit_report())

    centre = result.params["cen"]

    print(f"Centre:  {centre}")

    yield from bps.mv(changer_position, position)

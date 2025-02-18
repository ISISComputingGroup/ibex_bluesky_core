"""LOQ specific plans."""

from collections.abc import Generator
from pathlib import Path

import bluesky.plan_stubs as bps
import bluesky.plans as bp
from bluesky.plan_stubs import trigger_and_read
from bluesky.preprocessors import finalize_wrapper, run_decorator
from bluesky.utils import Msg
from ophyd_async.plan_stubs import ensure_connected

from ibex_bluesky_core.callbacks import ISISCallbacks
from ibex_bluesky_core.callbacks.fitting import FitMethod
from ibex_bluesky_core.callbacks.fitting.fitting_utils import Linear, Trapezoid
from ibex_bluesky_core.devices.block import BlockMot, BlockWriteConfig, block_mot, block_r, block_rw
from ibex_bluesky_core.devices.simpledae import SimpleDae
from ibex_bluesky_core.plans import common_dae, set_num_periods

LASER_INTENSITY_BLOCK_NAME = "changer_scan_intensity"

NUM_POINTS: int = 3
DEFAULT_DET = 3
DEFAULT_MON = 1
READABLE_FILE_OUTPUT_DIR = Path("C:\\") / "instrument" / "var" / "logs" / "bluesky" / "output_files"
DEFAULT_FIT_METHOD = Linear().fit()


def continuous_scan_plan(
    mot_block: BlockMot, centre: float, size: float, time: float, iterations: int
) -> Generator[Msg, None, None]:
    """Continuous scan plan for scanning a motor against a laser diode readback.

    Args:
        mot_block: The motor block to move.
        centre: The center of the scan.
        size: The size of the scan for one sweep.
        time: The time taken for one sweep.
        iterations: The number of iterations to run.

    """
    motor = mot_block

    laser_intensity = block_r(float, LASER_INTENSITY_BLOCK_NAME)

    initial_position = centre - 0.5 * size
    final_position = centre + 0.5 * size

    yield from ensure_connected(
        laser_intensity,
        motor,
    )
    initial_velocity = yield from bps.rd(motor.velocity)

    icc = ISISCallbacks(y=laser_intensity.name, x=motor.name, fit=Trapezoid.fit())

    @icc
    @run_decorator(md={})
    def _inner() -> Generator[Msg, None, None]:
        def polling_plan(destination: float):
            """This is a custom plan that essenitally drops updates if the motor position has
                not changed as that is our measurement's limiting factor.

            if we just used bp.scan() here we would have lots of laser intensity updates with
                the same motor position, which isn't really helpful.

            it also uses a finaliser to set the motor's velocity back to what it was initially,
                regardless of if the script fails halfway-through.

            Args:
                 destination: the destination position.

            """
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
    if icc.live_fit is not None and icc.live_fit:
        return icc.live_fit.result
    else:
        raise ValueError("No LiveFit result, likely fit failed")


def loq_dae(
    *,
    det_pixels: list[int],
    frames: int,
    periods: bool = True,
    monitor: int = DEFAULT_MON,
    save_run: bool = False,
) -> SimpleDae:
    """DAE instance for LOQ which can use periods or frames to count and normalise."""
    return common_dae(
        det_pixels=det_pixels, frames=frames, periods=periods, monitor=monitor, save_run=save_run
    )


def scan(  # noqa: PLR0913
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
) -> Generator[Msg, None, None]:
    block = block_rw(float, block_name, write_config=BlockWriteConfig(use_global_moving_flag=True))
    dae = loq_dae(det_pixels=[det], frames=frames, periods=periods, save_run=save_run, monitor=mon)

    yield from ensure_connected(dae, block)

    yield from set_num_periods(dae, count if periods else 1)

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

    icc = ISISCallbacks(
        y=dae.reducer.intensity.name,  # type: ignore
        yerr=dae.reducer.intensity_stddev.name,  # type: ignore
        x=block.name,
        measured_fields=fields,
        fit=model,
    )

    @icc
    def _inner() -> Generator[Msg, None, None]:
        if rel:
            plan = bp.rel_scan
        else:
            plan = bp.scan
        yield from plan([dae], block, start, stop, num=count)

    yield from _inner()

    print(f"Files written to {READABLE_FILE_OUTPUT_DIR}\n")
    print(f"Centre-of-mass from PeakStats: {icc.peak_stats['com']}\n")

    if icc.live_fit.result is not None:
        print(icc.live_fit.result.fit_report())
        return icc.live_fit.result.params
    else:
        print("No LiveFit result, likely fit failed")
        return None


def adaptive_scan(  # noqa: PLR0913
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
    model: FitMethod = DEFAULT_FIT_METHOD,
    periods: bool = True,
    save_run: bool = False,
    rel: bool = False,
) -> Generator[Msg, None, None]:
    block = block_rw(float, block_name, write_config=BlockWriteConfig(use_global_moving_flag=True))
    dae = loq_dae(det_pixels=[det], frames=frames, periods=periods, save_run=save_run, monitor=mon)

    yield from ensure_connected(dae, block)

    yield from set_num_periods(dae, 100)

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

    icc = ISISCallbacks(
        y=dae.reducer.intensity.name,  # type: ignore
        yerr=dae.reducer.intensity_stddev.name,  # type: ignore
        x=block.name,
        measured_fields=fields,
        fit=model,
    )

    @icc
    def _inner() -> Generator[Msg, None, None]:
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
    print(f"Centre-of-mass from PeakStats: {icc.peak_stats['com']}\n")

    if icc.live_fit.result is not None:
        print(icc.live_fit.result.fit_report())
        return icc.live_fit.result.params
    else:
        print("No LiveFit result, likely fit failed")
        return None


def sample_changer_scan(
    position: str, width: float = 22, time: float = 20, iterations: int = 1
) -> Generator[Msg, None, None]:
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
) -> Generator[Msg, None, None]:
    """Perform a continuous scan over an aperture to find its centre."""
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

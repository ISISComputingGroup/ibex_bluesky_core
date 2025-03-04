"""LOQ specific plans."""

from collections.abc import Generator

import bluesky.plan_stubs as bps
from bluesky.plan_stubs import trigger_and_read
from bluesky.preprocessors import finalize_wrapper, run_decorator
from bluesky.utils import Msg
from ophyd_async.plan_stubs import ensure_connected

from ibex_bluesky_core.callbacks import ISISCallbacks
from ibex_bluesky_core.callbacks.fitting.fitting_utils import Trapezoid
from ibex_bluesky_core.devices.block import BlockMot, BlockWriteConfig, block_mot, block_r, block_rw

LASER_INTENSITY_BLOCK_NAME = "changer_scan_intensity"

NUM_POINTS: int = 3
DEFAULT_MON = 1


def continuous_laser_scan(
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
        def polling_plan(destination: float) -> Generator[Msg, None, None]:
            """Drop updates if motor pos has not changed as we only care if it has changed.

            Args:
                 destination: the destination position.

            if we just used bp.scan() here we would have lots of laser intensity updates with
                the same motor position, which isn't really helpful.

            it also uses a finaliser to set the motor's velocity back to what it was initially,
                regardless of if the script fails halfway-through.

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

    def _set_motor_back_to_original_velocity() -> Generator[Msg, None, None]:
        yield from bps.mv(motor.velocity, initial_velocity)

    yield from finalize_wrapper(_inner(), _set_motor_back_to_original_velocity)
    if icc.live_fit is not None and icc.live_fit:
        return icc.live_fit.result
    else:
        raise ValueError("No LiveFit result, likely fit failed")


def sample_changer_scan(
    position: str, width: float = 22, time: float = 20, iterations: int = 1
) -> Generator[Msg, None, None]:
    """Perform a continuous scan over a sample changer holder, using a laser, to find its centre."""
    changer_position = block_rw(
        str, "Changer", write_config=BlockWriteConfig(use_global_moving_flag=True)
    )
    motor = block_mot("sample_changer_scan_axis")
    offset = block_rw(float, "Offset")

    yield from ensure_connected(motor, offset, changer_position)
    yield from bps.mv(changer_position, position)
    current_position = yield from bps.rd(motor)

    result = yield from continuous_laser_scan(motor, current_position, width, time, iterations)

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
    """Perform a continuous scan over an aperture, using a laser, to find its centre."""
    changer_position = block_rw(
        str, "Aperture_2", write_config=BlockWriteConfig(use_global_moving_flag=True)
    )
    motor = block_mot("aperture_scan_axis")

    yield from ensure_connected(motor, changer_position)
    yield from bps.mv(changer_position, position)
    current_position = yield from bps.rd(motor)

    result = yield from continuous_laser_scan(motor, current_position, width, time, iterations)

    print(result.fit_report())

    centre = result.params["cen"]

    print(f"Centre:  {centre}")

    yield from bps.mv(changer_position, position)

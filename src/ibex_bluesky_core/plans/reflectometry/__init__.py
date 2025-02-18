"""Reflectometry plans and helpers."""

from ibex_bluesky_core.devices import get_pv_prefix
from ibex_bluesky_core.devices.block import BlockWriteConfig, block_rw
from ibex_bluesky_core.devices.reflectometry.refl_param import ReflParameter


def centred_pixel(centre: int, pixel_range: int) -> list[int]:
    """Given a centre and range, return a contiguous range of pixels around the centre, inclusive.

    ie. a centre of 50 with a range of 3 will give [47, 48, 49, 50, 51, 52, 53]

    Args:
          centre (int): The centre pixel number.
          pixel_range (int): The range of pixels either side to surround the centre.

    Returns a list of pixel numbers.

    """
    return [s for s in range(centre - pixel_range, centre + pixel_range + 1)]


def motor_with_tolerance(name: str, tolerance: float) -> block_rw:
    """Create a motor block with a settle time and tolerance to wait for before motion is complete.

    Args:
        name (str): The motor PV.
        tolerance (float): The motor tolerance to get to before a move is considered complete.

    Returns A device pointing to a motor.

    """

    def check(setpoint: float, actual: float) -> bool:
        return setpoint - tolerance <= actual <= setpoint + tolerance

    return block_rw(
        float,
        name,
        write_config=BlockWriteConfig(
            set_success_func=check, set_timeout_s=30.0, settle_time_s=0.5
        ),
    )


def refl_parameter(name: str) -> ReflParameter:
    """Small wrapper around a reflectometry parameter device.

    This automatically applies the current instrument's PV prefix.

    Args:
        name: the reflectometry parameter name.

    Returns a device pointing to a reflectometry parameter.

    """
    prefix = get_pv_prefix()
    return ReflParameter(prefix=prefix, name=name)

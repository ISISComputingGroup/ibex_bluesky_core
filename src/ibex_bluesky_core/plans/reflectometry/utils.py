from bluesky import plan_stubs as bps

from ibex_bluesky_core.devices import get_pv_prefix
from ibex_bluesky_core.devices.block import BlockWriteConfig, block_rw
from ibex_bluesky_core.devices.reflectometry.refl_param import ReflParameter
from ibex_bluesky_core.devices.simpledae import SimpleDae


def centred_pixel(centre: int, pixel_range: int) -> list[int]:
    return [s for s in range(centre - pixel_range, centre + pixel_range + 1)]


def motor_with_tolerance(name: str, tolerance: float):
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
    prefix = get_pv_prefix()
    return ReflParameter(prefix=prefix, name=name)


def set_num_periods(dae: SimpleDae, nperiods: int):
    yield from bps.mv(dae.number_of_periods, nperiods)  # type: ignore
    actual = yield from bps.rd(dae.number_of_periods)
    if actual != nperiods:
        raise ValueError(
            f"Could not set {nperiods} periods on DAE (probably requesting too many points, or already running)"
        )

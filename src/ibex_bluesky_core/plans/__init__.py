from bluesky import plan_stubs as bps

from ibex_bluesky_core.devices.simpledae import SimpleDae


def set_num_periods(dae: SimpleDae, nperiods: int):
    yield from bps.mv(dae.number_of_periods, nperiods)  # type: ignore
    actual = yield from bps.rd(dae.number_of_periods)
    if actual != nperiods:
        raise ValueError(
            f"Could not set {nperiods} periods on DAE (probably requesting too many points, or already running)"
        )

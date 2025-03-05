"""Demonstration plan showing basic bluesky functionality."""

from collections.abc import Generator

import bluesky.plan_stubs as bps
import bluesky.plans as bp
import matplotlib.pyplot as plt
from bluesky.utils import Msg
from ophyd_async.core import Device
from ophyd_async.plan_stubs import ensure_connected

from ibex_bluesky_core.callbacks import ISISCallbacks
from ibex_bluesky_core.callbacks.fitting.fitting_utils import Gaussian
from ibex_bluesky_core.devices import get_pv_prefix
from ibex_bluesky_core.devices.simpledae import SimpleDae
from ibex_bluesky_core.devices.simpledae.controllers import (
    PeriodPerPointController,
    RunPerPointController,
)
from ibex_bluesky_core.devices.simpledae.reducers import PeriodGoodFramesNormalizer
from ibex_bluesky_core.devices.simpledae.waiters import GoodFramesWaiter, PeriodGoodFramesWaiter
from ibex_bluesky_core.plan_stubs import call_sync, set_num_periods

try:
    from itertools import batched
except ImportError:
    from itertools import islice

    def batched(iterable, n, *, strict=False):
        if n < 1:
            raise ValueError("n must be at least one")
        iterator = iter(iterable)
        while batch := tuple(islice(iterator, n)):
            if strict and len(batch) != n:
                raise ValueError("batched(): incomplete batch")
            yield batch


default_prefix = get_pv_prefix()


def dae_magnet_plan(
    *args,
    dae: SimpleDae,
    num,
    periods=True,
    frames=500,
    save_run=True,
    prefix=default_prefix,
    confident: bool = False,
) -> Generator[Msg, None, None]:
    """Scan a DAE against a magnet."""
    plt.close("all")
    plt.show()

    if periods:
        controller = PeriodPerPointController(save_run=save_run)
        waiter = PeriodGoodFramesWaiter(frames)
    else:
        controller = RunPerPointController(save_run=save_run)
        waiter = GoodFramesWaiter(frames)

    reducer = PeriodGoodFramesNormalizer(prefix, detector_spectra=[i for i in range(1, 32 + 1)])

    dae = SimpleDae(
        prefix=prefix,
        controller=controller,
        waiter=waiter,
        reducer=reducer,
    )

    to_connect = [dae]
    to_measure = []
    for item in args:
        if isinstance(item, Device):
            to_connect.append(item)
            to_measure.append(item.name)
    yield from ensure_connected(*to_connect, force_reconnect=True)

    if periods:
        yield from set_num_periods(dae, num)
    else:
        yield from set_num_periods(dae, 1)

    icc = ISISCallbacks(
        y=reducer.intensity.name,
        x=args[0].name,
        yerr=reducer.intensity_stddev.name,
        fit=Gaussian().fit(),
        measured_fields=to_measure[1:],
    )

    @icc
    def _inner() -> Generator[Msg, None, None]:
        yield from bp.scan([dae], *args, num=num)

    yield from _inner()
    print(icc.live_fit.result.fit_report())
    fitted_value = icc.live_fit.result.params["x0"].value
    if args[1] <= abs(fitted_value) <= args[2]:
        if not confident:
            ans = yield from call_sync(input, f"set {args[0].name} to {fitted_value}? y/n")
        else:
            ans = "y"
        if ans.lower().startswith("y"):
            fitted_fraction = (fitted_value - args[1]) / (args[2] - args[1])
            for device, start, stop in batched(args, n=3):
                value = start + fitted_fraction * (stop - start)
                print(f"Setting {device.name} to {value}")
                yield from bps.mv(device, abs(value))
    return icc.live_fit.result

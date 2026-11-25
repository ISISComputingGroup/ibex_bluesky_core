from typing import Generator

from bluesky import Msg
from lmfit.model import ModelResult

from ibex_bluesky_core.devices.simpledae import SimpleDae, PeriodPerPointController, Waiter
from ibex_bluesky_core.devices.simpledae import MultiRegionOfInterestReducer


def rocking_scan(
    dae: SimpleDae[PeriodPerPointController, Waiter, MultiRegionOfInterestReducer],
) -> Generator[Msg, None, ModelResult | None]:
    ...
    # typed as a wrapper
    # init reducer with 2 regions, A and B
    # livefit callback on both regions, fitting to gaussians
    # when stop- take average of gaussians and expose fitting params, namely centre (x0)
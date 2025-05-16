"""Base classes for DAE strategies."""

from ibex_bluesky_core.devices.dae import Dae
from ibex_bluesky_core.devices.dae.strategies._controllers import (
    Controller,
    PeriodPerPointController,
    RunPerPointController,
    _end_or_abort_run,
)
from ibex_bluesky_core.devices.dae.strategies._extra_readables import ProvidesExtraReadables
from ibex_bluesky_core.devices.dae.strategies._reducers import (
    INTENSITY_PRECISION,
    VARIANCE_ADDITION,
    GoodFramesNormalizer,
    MonitorNormalizer,
    PeriodGoodFramesNormalizer,
    PeriodSpecIntegralsReducer,
    Reducer,
    ScalarNormalizer,
    sum_spectra,
    tof_bounded_spectra,
    wavelength_bounded_spectra,
)
from ibex_bluesky_core.devices.dae.strategies._waiters import (
    GoodFramesWaiter,
    GoodUahWaiter,
    MEventsWaiter,
    PeriodGoodFramesWaiter,
    SimpleWaiter,
    TimeWaiter,
    Waiter,
)

__all__ = [
    "INTENSITY_PRECISION",
    "VARIANCE_ADDITION",
    "Controller",
    "Dae",
    "GoodFramesNormalizer",
    "GoodFramesWaiter",
    "GoodUahWaiter",
    "MEventsWaiter",
    "MonitorNormalizer",
    "PeriodGoodFramesNormalizer",
    "PeriodGoodFramesWaiter",
    "PeriodPerPointController",
    "PeriodSpecIntegralsReducer",
    "ProvidesExtraReadables",
    "Reducer",
    "RunPerPointController",
    "ScalarNormalizer",
    "SimpleWaiter",
    "TimeWaiter",
    "Waiter",
    "_end_or_abort_run",
    "sum_spectra",
    "tof_bounded_spectra",
    "wavelength_bounded_spectra",
]

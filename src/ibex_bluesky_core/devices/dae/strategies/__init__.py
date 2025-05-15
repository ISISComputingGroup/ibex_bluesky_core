"""Base classes for DAE strategies."""

from ibex_bluesky_core.devices.dae.strategies._base import (
    Controller,
    ProvidesExtraReadables,
    Reducer,
    Waiter,
)
from ibex_bluesky_core.devices.dae.strategies._controllers import (
    PeriodPerPointController,
    RunPerPointController,
    _end_or_abort_run,
)
from ibex_bluesky_core.devices.dae.strategies._reducers import (
    INTENSITY_PRECISION,
    VARIANCE_ADDITION,
    GoodFramesNormalizer,
    MonitorNormalizer,
    PeriodGoodFramesNormalizer,
    PeriodSpecIntegralsReducer,
    PolarisingReducer,
    ScalarNormalizer,
    WavelengthBoundedNormalizer,
    polarization,
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
)

__all__ = [
    "INTENSITY_PRECISION",
    "VARIANCE_ADDITION",
    "Controller",
    "GoodFramesNormalizer",
    "GoodFramesWaiter",
    "GoodUahWaiter",
    "MEventsWaiter",
    "MonitorNormalizer",
    "PeriodGoodFramesNormalizer",
    "PeriodGoodFramesWaiter",
    "PeriodPerPointController",
    "PeriodSpecIntegralsReducer",
    "PolarisingReducer",
    "ProvidesExtraReadables",
    "Reducer",
    "RunPerPointController",
    "ScalarNormalizer",
    "SimpleWaiter",
    "TimeWaiter",
    "Waiter",
    "WavelengthBoundedNormalizer",
    "_end_or_abort_run",
    "polarization",
    "sum_spectra",
    "tof_bounded_spectra",
    "wavelength_bounded_spectra",
]

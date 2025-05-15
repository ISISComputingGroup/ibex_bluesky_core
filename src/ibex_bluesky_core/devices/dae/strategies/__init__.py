"""Base classes for DAE strategies."""

from ibex_bluesky_core.devices.dae.strategies._base import (
    Controller,
    Waiter,
    Reducer,
    ProvidesExtraReadables,
)
from ibex_bluesky_core.devices.dae.strategies._controllers import (
    PeriodPerPointController,
    RunPerPointController,
    _end_or_abort_run
)
from ibex_bluesky_core.devices.dae.strategies._reducers import (
    INTENSITY_PRECISION,
    VARIANCE_ADDITION,
    sum_spectra,
    tof_bounded_spectra,
    wavelength_bounded_spectra,
    ScalarNormalizer,
    PeriodGoodFramesNormalizer,
    GoodFramesNormalizer,
    PeriodSpecIntegralsReducer,
    MonitorNormalizer,
    polarization,
    WavelengthBoundedNormalizer,
    PolarisingReducer,
)

from ibex_bluesky_core.devices.dae.strategies._waiters import (
    SimpleWaiter,
    PeriodGoodFramesWaiter,
    GoodFramesWaiter,
    GoodUahWaiter,
    MEventsWaiter,
    TimeWaiter,
)

__all__ = [
    "Controller",
    "Waiter",
    "Reducer",
    "ProvidesExtraReadables",
    "PeriodPerPointController",
    "RunPerPointController",
    "_end_or_abort_run",
    "INTENSITY_PRECISION",
    "VARIANCE_ADDITION",
    "sum_spectra",
    "tof_bounded_spectra",
    "wavelength_bounded_spectra",
    "ScalarNormalizer",
    "PeriodGoodFramesNormalizer",
    "GoodFramesNormalizer",
    "PeriodSpecIntegralsReducer",
    "MonitorNormalizer",
    "polarization",
    "WavelengthBoundedNormalizer",
    "PolarisingReducer",
    "SimpleWaiter",
    "PeriodGoodFramesWaiter",
    "GoodFramesWaiter",
    "GoodUahWaiter",
    "MEventsWaiter",
    "TimeWaiter",
]

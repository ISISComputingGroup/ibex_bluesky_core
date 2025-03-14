"""A simple interface to the DAE for bluesky."""

import logging
from typing import Generic

from bluesky.protocols import Triggerable
from ophyd_async.core import (
    AsyncStageable,
    AsyncStatus,
)
from typing_extensions import TypeVar

from ibex_bluesky_core.devices.dae.dae import Dae
from ibex_bluesky_core.devices.simpledae.controllers import (
    PeriodPerPointController,
    RunPerPointController,
)
from ibex_bluesky_core.devices.simpledae.reducers import MonitorNormalizer
from ibex_bluesky_core.devices.simpledae.strategies import Controller, Reducer, Waiter
from ibex_bluesky_core.devices.simpledae.waiters import (
    GoodFramesWaiter,
    PeriodGoodFramesWaiter,
)
from ibex_bluesky_core.utils import get_pv_prefix

logger = logging.getLogger(__name__)

__all__ = ["SimpleDae", "check_dae_strategies", "monitor_normalising_dae"]

TController_co = TypeVar("TController_co", bound="Controller", default="Controller", covariant=True)
TWaiter_co = TypeVar("TWaiter_co", bound="Waiter", default="Waiter", covariant=True)
TReducer_co = TypeVar("TReducer_co", bound="Reducer", default="Reducer", covariant=True)


class SimpleDae(Dae, Triggerable, AsyncStageable, Generic[TController_co, TWaiter_co, TReducer_co]):
    """Configurable DAE with pluggable strategies for data collection, waiting, and reduction.

    This class should cover many simple DAE use-cases, but for complex use-cases a custom Dae
    subclass may still be required to give maximum flexibility.
    """

    def __init__(
        self,
        *,
        prefix: str,
        name: str = "DAE",
        controller: TController_co,
        waiter: TWaiter_co,
        reducer: TReducer_co,
    ) -> None:
        """Initialize a simple DAE interface.

        Args:
            prefix: the PV prefix of the instrument being controlled.
            name: A friendly name for this DAE object.
            controller: A DAE control strategy, defines how the DAE begins and ends data acquisition
                Pre-defined strategies in the ibex_bluesky_core.devices.controllers module
            waiter: A waiting strategy, defines how the DAE waits for an acquisition to be complete
                Pre-defined strategies in the ibex_bluesky_core.devices.waiters module
            reducer: A data reduction strategy, defines the post-processing on raw DAE data, for
                example normalization or unit conversion.
                Pre-defined strategies in the ibex_bluesky_core.devices.reducers module

        """
        self.prefix = prefix
        self.controller: TController_co = controller
        self.waiter: TWaiter_co = waiter
        self.reducer: TReducer_co = reducer

        logger.info(
            "created simpledae with prefix=%s, controller=%s, waiter=%s, reducer=%s",
            prefix,
            controller,
            waiter,
            reducer,
        )

        # controller, waiter and reducer may be Devices (but don't necessarily have to be),
        # so can define their own signals. Do __init__ after defining those, so that the signals
        # are connected/named and usable.
        super().__init__(prefix=prefix, name=name)

        # Ask each defined strategy what it's interesting signals are, and ensure those signals are
        # published when the top-level SimpleDae object is read.
        extra_readables = set()
        for strategy in [self.controller, self.waiter, self.reducer]:
            extra_readables.update(strategy.additional_readable_signals(self))
        logger.info("extra readables: %s", list(extra_readables))
        self.add_readables(devices=list(extra_readables))

    @AsyncStatus.wrap
    async def stage(self) -> None:
        """Pre-scan setup. Delegate to the controller."""
        await self.controller.setup(self)

    @AsyncStatus.wrap
    async def trigger(self) -> None:
        """Take a single measurement and prepare it for subsequent reading.

        This waits for the acquisition and any defined reduction to be complete, such that
        after this coroutine completes all relevant data is available via read()
        """
        await self.controller.start_counting(self)
        await self.waiter.wait(self)
        await self.controller.stop_counting(self)
        await self.reducer.reduce_data(self)

    @AsyncStatus.wrap
    async def unstage(self) -> None:
        """Post-scan teardown, delegate to the controller."""
        await self.controller.teardown(self)


def monitor_normalising_dae(
    *,
    det_pixels: list[int],
    frames: int,
    periods: bool = True,
    monitor: int = 1,
    save_run: bool = False,
) -> SimpleDae:
    """Create a simple DAE which normalises using a monitor and waits for frames.

    This is really a shortcut to reduce code in plans used on the majority of instruments that
    normalise using a monitor, wait for a number of frames and optionally use software periods.

    Args:
        det_pixels: list of detector pixel to use for scanning.
        frames: number of frames to wait for.
        periods: whether or not to use software periods.
        monitor: the monitor spectra number.
        save_run: whether or not to save the run of the DAE.

    """
    prefix = get_pv_prefix()

    if periods:
        controller = PeriodPerPointController(save_run=save_run)
        waiter = PeriodGoodFramesWaiter(frames)
    else:
        controller = RunPerPointController(save_run=save_run)
        waiter = GoodFramesWaiter(frames)

    reducer = MonitorNormalizer(
        prefix=prefix,
        detector_spectra=det_pixels,
        monitor_spectra=[monitor],
    )

    dae = SimpleDae(
        prefix=prefix,
        controller=controller,
        waiter=waiter,
        reducer=reducer,
    )

    dae.reducer.intensity.set_name("intensity")  # type: ignore
    dae.reducer.intensity_stddev.set_name("intensity_stddev")  # type: ignore
    return dae


def check_dae_strategies(
    dae: SimpleDae,
    *,
    expected_controller: type[Controller] | None = None,
    expected_waiter: type[Waiter] | None = None,
    expected_reducer: type[Reducer] | None = None,
) -> None:
    """Check that the provided dae instance has appropriate controller/reducer/waiter configured.

    Args:
        dae: The simpledae instance to check.
        expected_controller: The expected controller type, on None to not check.
        expected_waiter: The expected controller type, on None to not check.
        expected_reducer: The expected controller type, on None to not check.

    """
    if expected_controller is not None:
        if not isinstance(dae.controller, expected_controller):
            raise TypeError(
                f"DAE controller must be of type {expected_controller.__name__}, "
                f"got {dae.controller.__class__.__name__}"
            )

    if expected_waiter is not None:
        if not isinstance(dae.waiter, expected_waiter):
            raise TypeError(
                f"DAE waiter must be of type {expected_waiter.__name__}, "
                f"got {dae.waiter.__class__.__name__}"
            )

    if expected_reducer is not None:
        if not isinstance(dae.reducer, expected_reducer):
            raise TypeError(
                f"DAE reducer must be of type {expected_reducer.__name__}, "
                f"got {dae.reducer.__class__.__name__}"
            )

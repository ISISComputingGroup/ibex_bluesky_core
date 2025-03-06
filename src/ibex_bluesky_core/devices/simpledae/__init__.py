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
from ibex_bluesky_core.devices.simpledae.strategies import Controller, Reducer, Waiter

logger = logging.getLogger(__name__)


__all__ = ["SimpleDae", "TController_co", "TReducer_co", "TWaiter_co"]

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

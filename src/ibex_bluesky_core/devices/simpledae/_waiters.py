"""DAE waiting strategies."""

import asyncio
import logging
from abc import ABC, abstractmethod
from typing import Generic, TypeVar

from ophyd_async.core import (
    Device,
    SignalR,
    soft_signal_rw,
    wait_for_value,
)

from ibex_bluesky_core.devices.dae import Dae
from ibex_bluesky_core.devices.simpledae._strategies import Waiter

logger = logging.getLogger(__name__)

T = TypeVar("T", int, float)


class SimpleWaiter(Waiter, Generic[T], ABC):
    """Wait for a single DAE variable to be greater or equal to a specified numeric value."""

    def __init__(self, value: T) -> None:
        """Wait for a value to be at least equal to the specified value.

        Args:
            value: the value to wait for

        """
        self.finish_wait_at = soft_signal_rw(float, value)

    async def wait(self, dae: Dae) -> None:
        """Wait for signal to reach the user-specified value."""
        signal = self.get_signal(dae)
        logger.info("starting wait for signal %s", signal.source)
        value = await self.finish_wait_at.get_value()
        await wait_for_value(signal, lambda v: v >= value, timeout=None)
        logger.info("completed wait for signal %s", signal.source)

    def additional_readable_signals(self, dae: Dae) -> list[Device]:
        """Publish the signal we're waiting on as an interesting signal."""
        return [self.get_signal(dae)]

    @abstractmethod
    def get_signal(self, dae: Dae) -> SignalR[T]:
        """Get the numeric signal to wait for."""


class PeriodGoodFramesWaiter(SimpleWaiter[int]):
    """Wait for period good frames to reach a user-specified value."""

    def get_signal(self, dae: Dae) -> SignalR[int]:
        """Wait for period good frames."""
        return dae.period.good_frames

class GoodUahWaiter(SimpleWaiter[float]):
    """Wait for good microamp-hours to reach a user-specified value."""

    def get_signal(self, dae: Dae) -> SignalR[float]:
        """Wait for good uah."""
        return dae.good_uah


class MEventsWaiter(SimpleWaiter[float]):
    """Wait for a user-specified number of millions of events."""

    def get_signal(self, dae: Dae) -> SignalR[float]:
        """Wait for mevents."""
        return dae.m_events


class TimeWaiter(Waiter):
    """Wait for a user-specified time duration."""

    def __init__(self, *, seconds: float) -> None:
        """Init.

        Args:
            seconds: number of seconds to wait for.

        """
        self._secs = seconds

    async def wait(self, dae: Dae) -> None:
        """Wait for the specified time duration."""
        logger.info("starting wait for %f seconds", self._secs)
        await asyncio.sleep(self._secs)
        logger.info("completed wait")

"""DAE waiting strategies."""

import asyncio
import logging
from abc import ABCMeta, abstractmethod
from typing import TYPE_CHECKING, Generic, TypeVar

from ophyd_async.core import (
    Device,
    SignalR,
    wait_for_value,
)

from ibex_bluesky_core.devices.simpledae.strategies import Waiter

logger = logging.getLogger(__name__)

if TYPE_CHECKING:
    from ibex_bluesky_core.devices.simpledae import SimpleDae


T = TypeVar("T", int, float)


class SimpleWaiter(Waiter, Generic[T], metaclass=ABCMeta):
    """Wait for a single DAE variable to be greater or equal to a specified numeric value."""

    def __init__(self, value: T) -> None:
        """Wait for a value to be at least equal to the specified value.

        Args:
            value: the value to wait for

        """
        self._value: T = value

    async def wait(self, dae: "SimpleDae") -> None:
        """Wait for signal to reach the user-specified value."""
        signal = self.get_signal(dae)
        logger.info("starting wait for signal %s", signal.source)
        await wait_for_value(signal, lambda v: v >= self._value, timeout=None)
        logger.info("completed wait for signal %s", signal.source)

    def additional_readable_signals(self, dae: "SimpleDae") -> list[Device]:
        """Publish the signal we're waiting on as an interesting signal."""
        return [self.get_signal(dae)]

    @abstractmethod
    def get_signal(self, dae: "SimpleDae") -> SignalR[T]:
        """Get the numeric signal to wait for."""


class PeriodGoodFramesWaiter(SimpleWaiter[int]):
    """Wait for period good frames to reach a user-specified value."""

    def get_signal(self, dae: "SimpleDae") -> SignalR[int]:
        """Wait for period good frames."""
        return dae.period.good_frames


class GoodFramesWaiter(SimpleWaiter[int]):
    """Wait for good frames to reach a user-specified value."""

    def get_signal(self, dae: "SimpleDae") -> SignalR[int]:
        """Wait for good frames."""
        return dae.good_frames


class GoodUahWaiter(SimpleWaiter[float]):
    """Wait for good microamp-hours to reach a user-specified value."""

    def get_signal(self, dae: "SimpleDae") -> SignalR[float]:
        """Wait for good uah."""
        return dae.good_uah


class MEventsWaiter(SimpleWaiter[float]):
    """Wait for a user-specified number of millions of events."""

    def get_signal(self, dae: "SimpleDae") -> SignalR[float]:
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

    async def wait(self, dae: "SimpleDae") -> None:
        """Wait for the specified time duration."""
        logger.info("starting wait for %f seconds", self._secs)
        await asyncio.sleep(self._secs)
        logger.info("completed wait")

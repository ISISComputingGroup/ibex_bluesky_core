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
        """Wait for a single DAE variable to be greater or equal to the specified value.

        .. note::

            This is a generic base class. Implementations such as :py:obj:`PeriodGoodFramesWaiter`
            should generally be used rather than this class directly.

        Args:
            value: the value to wait for

        """
        self.finish_wait_at = soft_signal_rw(float, value)
        """
        Value at which to finish waiting.

        It is possible to change this signal dynamically at runtime, using:

        .. code-block:: python

            yield from bps.mv(waiter.finish_wait_at, new_finish_value)
        """

    async def wait(self, dae: Dae) -> None:
        """Wait for signal to reach the user-specified value."""
        signal = self.get_signal(dae)
        logger.info("starting wait for signal %s", signal.source)
        value = await self.finish_wait_at.get_value()
        await wait_for_value(signal, lambda v: v >= value, timeout=None)
        logger.info("completed wait for signal %s", signal.source)

    def additional_readable_signals(self, dae: Dae) -> list[Device]:
        """Publish the signal we're waiting on as an interesting signal.

        :meta private:
        """
        return [self.get_signal(dae)]

    @abstractmethod
    def get_signal(self, dae: Dae) -> SignalR[T]:
        """Get the numeric signal to wait for."""


class PeriodGoodFramesWaiter(SimpleWaiter[int]):
    """Wait for period good frames to reach a user-specified value."""

    def __init__(self, value: int) -> None:
        """Wait for a specified number of good frames in the current period.

        Args:
            value: the number of good frames to wait for

        """
        super().__init__(value)

    def get_signal(self, dae: Dae) -> SignalR[int]:
        """Wait for period good frames.

        :meta private:
        """
        return dae.period.good_frames


class GoodUahWaiter(SimpleWaiter[float]):
    """Wait for good microamp-hours to reach a user-specified value."""

    def __init__(self, value: float) -> None:
        """Wait for a specified number of good uAh in the current period.

        Args:
            value: the number of good uAh to wait for

        """
        super().__init__(value)

    def get_signal(self, dae: Dae) -> SignalR[float]:
        """Wait for good uah.

        :meta private:
        """
        return dae.good_uah


class MEventsWaiter(SimpleWaiter[float]):
    """Wait for a user-specified number of millions of events."""

    def __init__(self, value: float) -> None:
        """Wait for a specified number of events (in millions) in the current period.

        Args:
            value: the number of events (in millions) to wait for

        """
        super().__init__(value)

    def get_signal(self, dae: Dae) -> SignalR[float]:
        """Wait for mevents.

        :meta private:
        """
        return dae.m_events


class TimeWaiter(Waiter):
    """Wait for a user-specified time duration."""

    def __init__(self, *, seconds: float) -> None:
        """Wait for a user-specified time duration.

        Args:
            seconds: number of seconds to wait for.

        """
        self._secs = seconds

    async def wait(self, dae: Dae) -> None:
        """Wait for the specified time duration.

        :meta private:
        """
        logger.info("starting wait for %f seconds", self._secs)
        await asyncio.sleep(self._secs)
        logger.info("completed wait")

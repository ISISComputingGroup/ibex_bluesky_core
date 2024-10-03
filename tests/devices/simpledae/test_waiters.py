import asyncio

import pytest
from ophyd_async.core import set_mock_value

from ibex_bluesky_core.devices.simpledae import SimpleDae
from ibex_bluesky_core.devices.simpledae.waiters import (
    GoodFramesWaiter,
    GoodUahWaiter,
    MEventsWaiter,
    PeriodGoodFramesWaiter,
    TimeWaiter,
)

SHORT_TIMEOUT = 0.01


async def test_good_uah_waiter(simpledae: "SimpleDae"):
    waiter = GoodUahWaiter(5000)

    set_mock_value(simpledae.good_uah, 4999.9)

    with pytest.raises(asyncio.TimeoutError):
        await asyncio.wait_for(waiter.wait(simpledae), timeout=SHORT_TIMEOUT)

    set_mock_value(simpledae.good_uah, 5000.1)

    # Check this returns - will raise a timeout error if not.
    await asyncio.wait_for(waiter.wait(simpledae), timeout=SHORT_TIMEOUT)

    assert waiter.additional_readable_signals(simpledae) == [simpledae.good_uah]
    assert waiter.get_signal(simpledae) == simpledae.good_uah


async def test_period_good_frames_waiter(simpledae: "SimpleDae"):
    waiter = PeriodGoodFramesWaiter(5000)

    set_mock_value(simpledae.period.good_frames, 4999)

    with pytest.raises(asyncio.TimeoutError):
        await asyncio.wait_for(waiter.wait(simpledae), timeout=SHORT_TIMEOUT)

    set_mock_value(simpledae.period.good_frames, 5000)

    # Check this returns - will raise a timeout error if not.
    await asyncio.wait_for(waiter.wait(simpledae), timeout=SHORT_TIMEOUT)

    assert waiter.additional_readable_signals(simpledae) == [simpledae.period.good_frames]
    assert waiter.get_signal(simpledae) == simpledae.period.good_frames


async def test_good_frames_waiter(simpledae: "SimpleDae"):
    waiter = GoodFramesWaiter(5000)

    set_mock_value(simpledae.good_frames, 4999)

    with pytest.raises(asyncio.TimeoutError):
        await asyncio.wait_for(waiter.wait(simpledae), timeout=SHORT_TIMEOUT)

    set_mock_value(simpledae.good_frames, 5000)

    # Check this returns - will raise a timeout error if not.
    await asyncio.wait_for(waiter.wait(simpledae), timeout=SHORT_TIMEOUT)

    assert waiter.additional_readable_signals(simpledae) == [simpledae.good_frames]
    assert waiter.get_signal(simpledae) == simpledae.good_frames


async def test_mevents_waiter(simpledae: "SimpleDae"):
    waiter = MEventsWaiter(5000)

    set_mock_value(simpledae.m_events, 4999)

    with pytest.raises(asyncio.TimeoutError):
        await asyncio.wait_for(waiter.wait(simpledae), timeout=SHORT_TIMEOUT)

    set_mock_value(simpledae.m_events, 5000)

    # Check this returns - will raise a timeout error if not.
    await asyncio.wait_for(waiter.wait(simpledae), timeout=SHORT_TIMEOUT)

    assert waiter.additional_readable_signals(simpledae) == [simpledae.m_events]
    assert waiter.get_signal(simpledae) == simpledae.m_events


async def test_time_waiter(simpledae: "SimpleDae"):
    waiter = TimeWaiter(seconds=0.01)
    await waiter.wait(simpledae)
    assert waiter.additional_readable_signals(simpledae) == []

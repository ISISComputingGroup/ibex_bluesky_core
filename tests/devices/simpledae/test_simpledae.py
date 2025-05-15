from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from ophyd_async.core import Device, StandardReadable, soft_signal_rw
from ophyd_async.testing import set_mock_value

from ibex_bluesky_core.devices.dae import DaeCheckingSignal
from ibex_bluesky_core.devices.simpledae import (
    Controller,
    GoodFramesNormalizer,
    GoodFramesWaiter,
    PeriodGoodFramesNormalizer,
    PeriodGoodFramesWaiter,
    PeriodPerPointController,
    Reducer,
    RunPerPointController,
    SimpleDae,
    Waiter,
    check_dae_strategies,
    monitor_normalising_dae,
)


@pytest.fixture
def mock_controller() -> Controller:
    return MagicMock(spec=Controller)


@pytest.fixture
def mock_waiter() -> Waiter:
    return MagicMock(spec=Waiter)


@pytest.fixture
def mock_reducer() -> Reducer:
    return MagicMock(spec=Reducer)


@pytest.fixture
async def simpledae(
    mock_controller: Controller, mock_waiter: Waiter, mock_reducer: Reducer
) -> SimpleDae:
    simpledae = SimpleDae(
        prefix="unittest:mock:",
        name="simpledae",
        controller=mock_controller,
        waiter=mock_waiter,
        reducer=mock_reducer,
    )
    await simpledae.connect(mock=True)
    return simpledae


async def test_simpledae_calls_controller_on_stage_and_unstage(
    simpledae: SimpleDae, mock_controller: MagicMock
):
    await simpledae.stage()
    mock_controller.setup.assert_called_once_with(simpledae)
    await simpledae.unstage()
    mock_controller.teardown.assert_called_once_with(simpledae)


async def test_simpledae_calls_controller_on_trigger(
    simpledae: SimpleDae, mock_controller: MagicMock
):
    await simpledae.trigger()
    mock_controller.start_counting.assert_called_once_with(simpledae)
    mock_controller.stop_counting.assert_called_once_with(simpledae)


async def test_simpledae_calls_waiter_on_trigger(simpledae: SimpleDae, mock_waiter: MagicMock):
    await simpledae.trigger()
    mock_waiter.wait.assert_called_once_with(simpledae)


async def test_simpledae_calls_reducer_on_trigger(simpledae: SimpleDae, mock_reducer: MagicMock):
    await simpledae.trigger()
    mock_reducer.reduce_data.assert_called_once_with(simpledae)


async def test_simpledae_publishes_interesting_signals_in_read():
    class TestReducer(Reducer, StandardReadable):
        def __init__(self):
            self.soft_signal = soft_signal_rw(float, 0.0)
            super().__init__(name="reducer")

        def additional_readable_signals(self, dae: "SimpleDae") -> list[Device]:
            # Signal explicitly published by this reducer rather than the DAE itself
            return [self.soft_signal]

    class TestController(Controller):
        def additional_readable_signals(self, dae: "SimpleDae") -> list[Device]:
            return [dae.good_uah]

    class TestWaiter(Waiter):
        def additional_readable_signals(self, dae: "SimpleDae") -> list[Device]:
            # Same signal as controller, should only be added once.
            return [dae.good_uah]

    reducer = TestReducer()

    dae = SimpleDae(
        prefix="",
        name="dae",
        controller=TestController(),
        waiter=TestWaiter(),
        reducer=reducer,
    )
    await dae.connect(mock=True)
    reading = await dae.read()

    assert reducer.soft_signal.name in reading
    assert dae.good_uah.name in reading

    # Check that non-interesting signals are *not* read by default
    assert dae.good_frames not in reading
    assert len(reading) == 2


def test_monitor_normalising_dae_sets_up_periods_correctly():
    det_pixels = [1, 2, 3]
    frames = 200
    monitor = 20
    save_run = False
    with patch("ibex_bluesky_core.devices.simpledae.get_pv_prefix"):
        dae = monitor_normalising_dae(
            det_pixels=det_pixels, frames=frames, periods=True, monitor=monitor, save_run=save_run
        )

    assert isinstance(dae.waiter, PeriodGoodFramesWaiter)
    assert dae.waiter._value == frames
    assert isinstance(dae.controller, PeriodPerPointController)


def test_monitor_normalising_dae_sets_up_single_period_correctly():
    det_pixels = [2, 3, 4]
    frames = 400
    monitor = 20
    save_run = False
    with patch("ibex_bluesky_core.devices.simpledae.get_pv_prefix"):
        dae = monitor_normalising_dae(
            det_pixels=det_pixels, frames=frames, periods=False, monitor=monitor, save_run=save_run
        )

    assert isinstance(dae.waiter, GoodFramesWaiter)
    assert dae.waiter._value == frames
    assert isinstance(dae.controller, RunPerPointController)


async def test_dae_checking_signal_raises_if_readback_differs():
    device = DaeCheckingSignal(int, "UNITTEST:")
    await device.connect(mock=True)
    initial_value = 0
    set_mock_value(device.signal, initial_value)
    device.signal.get_value = AsyncMock(return_value=initial_value)
    with pytest.raises(IOError, match="Signal UNITTEST: could not be set to 1, actual value was 0"):
        await device.set(1)


async def test_dae_checking_signal_correctly_sets_value():
    device = DaeCheckingSignal(int, "UNITTEST:")
    await device.connect(mock=True)
    initial_value = 0
    set_mock_value(device.signal, initial_value)
    await device.set(1)
    assert await device.signal.get_value() == 1


def test_check_dae():
    dae = SimpleDae(
        prefix="",
        controller=PeriodPerPointController(save_run=False),
        waiter=PeriodGoodFramesWaiter(50),
        reducer=PeriodGoodFramesNormalizer(prefix="", detector_spectra=[1]),
    )

    with pytest.raises(
        TypeError,
        match=r"DAE controller must be of type RunPerPointController, got PeriodPerPointController",
    ):
        check_dae_strategies(dae, expected_controller=RunPerPointController)

    with pytest.raises(
        TypeError, match=r"DAE waiter must be of type GoodFramesWaiter, got PeriodGoodFramesWaiter"
    ):
        check_dae_strategies(dae, expected_waiter=GoodFramesWaiter)

    with pytest.raises(
        TypeError,
        match=r"DAE reducer must be of type GoodFramesNormalizer, got PeriodGoodFramesNormalizer",
    ):
        check_dae_strategies(dae, expected_reducer=GoodFramesNormalizer)

    # Should not raise
    check_dae_strategies(
        dae,
        expected_controller=PeriodPerPointController,
        expected_waiter=PeriodGoodFramesWaiter,
        expected_reducer=PeriodGoodFramesNormalizer,
    )

    # Should not raise
    check_dae_strategies(dae)

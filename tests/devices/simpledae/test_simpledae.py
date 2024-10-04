from unittest.mock import MagicMock

import pytest
from ophyd_async.core import Device, StandardReadable, soft_signal_rw

from ibex_bluesky_core.devices.simpledae import SimpleDae
from ibex_bluesky_core.devices.simpledae.strategies import Controller, Reducer, Waiter


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

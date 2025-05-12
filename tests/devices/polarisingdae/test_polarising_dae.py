from unittest.mock import MagicMock, patch, call

import pytest
from ophyd_async.core import soft_signal_rw, SignalRW
import scipp as sc
from ibex_bluesky_core.devices.polarisingdae import (
    PolarisingDae,
    polarising_dae
)
from ibex_bluesky_core.devices.simpledae import (
    Controller,
    GoodFramesWaiter,
    PeriodGoodFramesWaiter,
    PeriodPerPointController,
    Reducer,
    RunPerPointController,
    Waiter,
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
def mock_reducer_up() -> Reducer:
    return MagicMock(spec=Reducer)


@pytest.fixture
def mock_reducer_down() -> Reducer:
    return MagicMock(spec=Reducer)


@pytest.fixture
def flipper() -> SignalRW[float]:
    return soft_signal_rw(float, 0.0)


@pytest.fixture
async def mock_dae(
    mock_controller: Controller, mock_waiter: Waiter, mock_reducer: Reducer, mock_reducer_up: Reducer, mock_reducer_down: Reducer, flipper: SignalRW,
) -> PolarisingDae:

    mock_dae = PolarisingDae(
        prefix="unittest:mock:",
        name="polarisingdae",
        controller=mock_controller,
        waiter=mock_waiter,
        reducer=mock_reducer,
        reducer_up=mock_reducer_up,
        reducer_down=mock_reducer_down,
        flipper=flipper,
        flipper_states=(0.0, 1.0),
    )

    await mock_dae.connect(mock=True)
    return mock_dae


async def test_polarisingdae_calls_controller_twice_on_trigger(
    mock_dae: PolarisingDae, mock_controller: MagicMock
):
    """Test that the DAE controller is called twice on trigger."""
    await mock_dae.trigger()
    assert mock_controller.start_counting.call_count == 2
    mock_controller.start_counting.assert_has_calls([call(mock_dae), call(mock_dae)])


async def test_polarisingdae_calls_waiter_twice_on_trigger(
    mock_dae: PolarisingDae, mock_waiter: MagicMock
):
    """Test that the DAE waiter is called twice on trigger."""
    await mock_dae.trigger()
    assert mock_waiter.wait.call_count == 2
    mock_waiter.wait.assert_has_calls([call(mock_dae), call(mock_dae)])


async def test_polarisingdae_calls_reducer_on_trigger(
    mock_dae: PolarisingDae, 
    mock_reducer: MagicMock, 
    mock_reducer_up: MagicMock, 
    mock_reducer_down: MagicMock
):
    """Test that all reducers are called appropriately on trigger."""

    await mock_dae.trigger()
    mock_reducer.reduce_data.assert_called_once_with(mock_dae)
    mock_reducer_up.reduce_data.assert_called_once_with(mock_dae)
    mock_reducer_down.reduce_data.assert_called_once_with(mock_dae)


def test_polarising_dae_sets_up_periods_correctly(flipper: SignalRW):
    """Test that the DAE is correctly configured for period-per-point operation."""
    det_pixels = [1, 2, 3]
    frames = 200
    monitor = 20
    intervals = [sc.array(dims=["tof"], values=[0, 9999999999.0], unit=sc.units.angstrom, dtype="float64")]
    flipper_states=(0.0, 1.0)
    total_flight_path_length = sc.scalar(value=10, unit=sc.units.m)
    save_run = False
    
    with patch("ibex_bluesky_core.devices.polarisingdae.get_pv_prefix"):
        dae = polarising_dae(
            det_pixels=det_pixels, frames=frames, periods=True, monitor=monitor, save_run=save_run, 
            intervals=intervals, total_flight_path_length=total_flight_path_length, 
            flipper=flipper, flipper_states=flipper_states
        )

    assert isinstance(dae.waiter, PeriodGoodFramesWaiter)
    assert dae.waiter._value == frames
    assert isinstance(dae.controller, PeriodPerPointController)


def test_polarising_dae_sets_up_single_period_correctly(flipper: SignalRW):
    """Test that the DAE is correctly configured for run-per-point operation."""
    det_pixels = [1, 2, 3]
    frames = 200
    monitor = 20
    intervals = [sc.array(dims=["tof"], values=[0, 9999999999.0], unit=sc.units.angstrom, dtype="float64")]
    flipper_states = (0.0, 1.0)
    total_flight_path_length = sc.scalar(value=10, unit=sc.units.m)
    save_run = False
    
    with patch("ibex_bluesky_core.devices.polarisingdae.get_pv_prefix"):
        dae = polarising_dae(
            det_pixels=det_pixels, frames=frames, periods=False, monitor=monitor, save_run=save_run,
            intervals=intervals, total_flight_path_length=total_flight_path_length,
            flipper=flipper, flipper_states=flipper_states
        )

    assert isinstance(dae.waiter, GoodFramesWaiter)
    assert dae.waiter._value == frames
    assert isinstance(dae.controller, RunPerPointController)
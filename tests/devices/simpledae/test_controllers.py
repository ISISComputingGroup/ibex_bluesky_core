import pytest
from ophyd_async.core import get_mock_put, set_mock_value

from ibex_bluesky_core.devices.dae.dae import RunstateEnum
from ibex_bluesky_core.devices.dae.dae_controls import BeginRunExBits
from ibex_bluesky_core.devices.simpledae import SimpleDae
from ibex_bluesky_core.devices.simpledae.controllers import (
    PeriodPerPointController,
    RunPerPointController,
)


@pytest.fixture
def period_per_point_controller() -> PeriodPerPointController:
    return PeriodPerPointController(save_run=True)


@pytest.fixture
def aborting_period_per_point_controller() -> PeriodPerPointController:
    return PeriodPerPointController(save_run=False)


@pytest.fixture
def run_per_point_controller() -> RunPerPointController:
    return RunPerPointController(save_run=True)


@pytest.fixture
def aborting_run_per_point_controller() -> RunPerPointController:
    return RunPerPointController(save_run=False)


async def test_period_per_point_controller_publishes_current_period(
    simpledae: SimpleDae, period_per_point_controller: PeriodPerPointController
):
    assert period_per_point_controller.additional_readable_signals(simpledae) == [
        simpledae.period_num
    ]


async def test_period_per_point_controller_begins_run_in_setup_and_ends_in_teardown(
    simpledae: SimpleDae, period_per_point_controller: PeriodPerPointController
):
    set_mock_value(simpledae.run_state, RunstateEnum.PAUSED)
    await period_per_point_controller.setup(simpledae)
    get_mock_put(simpledae.controls.begin_run_ex._raw_begin_run_ex).assert_called_once_with(
        BeginRunExBits.BEGIN_PAUSED, wait=True, timeout=None
    )
    set_mock_value(simpledae.run_state, RunstateEnum.SETUP)
    await period_per_point_controller.teardown(simpledae)
    get_mock_put(simpledae.controls.end_run).assert_called_once_with(None, wait=True, timeout=None)


async def test_aborting_period_per_point_controller_aborts_in_teardown(
    simpledae: SimpleDae, aborting_period_per_point_controller: PeriodPerPointController
):
    set_mock_value(simpledae.run_state, RunstateEnum.SETUP)
    await aborting_period_per_point_controller.teardown(simpledae)
    get_mock_put(simpledae.controls.abort_run).assert_called_once_with(
        None, wait=True, timeout=None
    )


async def test_period_per_point_controller_changes_periods_and_counts(
    simpledae: SimpleDae, period_per_point_controller: PeriodPerPointController
):
    set_mock_value(simpledae.run_state, RunstateEnum.RUNNING)
    await period_per_point_controller.start_counting(simpledae)
    get_mock_put(simpledae.controls.resume_run).assert_called_once_with(
        None, wait=True, timeout=None
    )
    get_mock_put(simpledae.period_num).assert_called_once_with(1, wait=True, timeout=None)

    set_mock_value(simpledae.run_state, RunstateEnum.PAUSED)
    await period_per_point_controller.stop_counting(simpledae)
    get_mock_put(simpledae.controls.pause_run).assert_called_once_with(
        None, wait=True, timeout=None
    )


async def test_run_per_point_controller_starts_and_ends_runs(
    simpledae: SimpleDae, run_per_point_controller: RunPerPointController
):
    set_mock_value(simpledae.run_state, RunstateEnum.RUNNING)
    await run_per_point_controller.start_counting(simpledae)
    get_mock_put(simpledae.controls.begin_run).assert_called_once_with(
        None, wait=True, timeout=None
    )

    await run_per_point_controller.stop_counting(simpledae)
    get_mock_put(simpledae.controls.end_run).assert_called_once_with(None, wait=True, timeout=None)


async def test_run_per_point_controller_publishes_run(
    simpledae: SimpleDae, run_per_point_controller: RunPerPointController
):
    assert run_per_point_controller.additional_readable_signals(simpledae) == [
        run_per_point_controller.run_number
    ]


async def test_aborting_run_per_point_controller_doesnt_publish_run(
    simpledae: SimpleDae, aborting_run_per_point_controller: RunPerPointController
):
    assert aborting_run_per_point_controller.additional_readable_signals(simpledae) == []

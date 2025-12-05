# pyright: reportMissingParameterType=false
import functools
from typing import Any
from unittest.mock import patch

import bluesky.utils
import pytest
from bluesky.preprocessors import run_decorator
from ophyd_async.plan_stubs import ensure_connected
from ophyd_async.sim import SimMotor
from ophyd_async.testing import callback_on_mock_put, get_mock_put, set_mock_value

from ibex_bluesky_core.devices.block import BlockMot, BlockR, BlockRw
from ibex_bluesky_core.devices.simpledae import (
    Controller,
    MonitorNormalizer,
    PeriodPerPointController,
    RunPerPointController,
    SimpleDae,
    Waiter,
)
from ibex_bluesky_core.fitting import Gaussian
from ibex_bluesky_core.plan_stubs import polling_plan
from ibex_bluesky_core.plans import (
    adaptive_scan,
    motor_adaptive_scan,
    motor_scan,
    scan,
)


def test_scan_motor_creates_block_device_and_dae(RE):
    prefix = "UNITTEST:"
    block_name = "some_block"
    with (
        patch("ibex_bluesky_core.devices.block.get_pv_prefix", return_value=prefix),
        patch("ibex_bluesky_core.devices.simpledae.get_pv_prefix", return_value=prefix),
        patch("ibex_bluesky_core.plans.scan") as scan,
    ):
        RE(
            motor_scan(
                block_name=block_name,
                start=0,
                stop=2,
                num=3,
                frames=200,
                det=1,
                mon=3,
                model=Gaussian().fit(),
            )
        )
        scan.assert_called_once()
        assert isinstance(scan.call_args[1]["dae"], SimpleDae)
        assert isinstance(scan.call_args[1]["block"], BlockRw)
        assert scan.call_args[1]["block"].name == block_name


def test_adaptive_scan_motor_creates_block_device_and_dae(RE):
    prefix = "UNITTEST:"
    block_name = "some_block"
    with (
        patch("ibex_bluesky_core.devices.block.get_pv_prefix", return_value=prefix),
        patch("ibex_bluesky_core.devices.simpledae.get_pv_prefix", return_value=prefix),
        patch("ibex_bluesky_core.plans.adaptive_scan") as scan,
    ):
        RE(
            motor_adaptive_scan(
                block_name=block_name,
                start=0,
                stop=2,
                min_step=0.01,
                max_step=0.1,
                target_delta=0.5,
                frames=200,
                det=1,
                mon=3,
                model=Gaussian().fit(),
            )
        )
        scan.assert_called_once()
        assert isinstance(scan.call_args[1]["dae"], SimpleDae)
        assert isinstance(scan.call_args[1]["block"], BlockRw)
        assert scan.call_args[1]["block"].name == block_name


@pytest.fixture
async def dae():
    noop_controller = Controller()
    noop_waiter = Waiter()
    reducer = MonitorNormalizer(prefix="UNITTEST:", detector_spectra=[1, 2, 3], monitor_spectra=[4])

    dae = SimpleDae(
        prefix="UNITTEST:",
        name="dae",
        controller=noop_controller,
        waiter=noop_waiter,
        reducer=reducer,
    )
    await dae.connect(mock=True)
    return dae


@pytest.fixture
async def block():
    block = BlockMot(prefix="UNITTEST:", block_name="SOME_BLOCK")
    await block.connect(mock=True)
    return block


def test_scan_does_normal_scan_when_relative_false(RE, dae, block):
    start = 0
    stop = 2
    count = 3
    with (
        patch("ibex_bluesky_core.plans.bp.scan") as bp_scan,
        patch("ibex_bluesky_core.plans.ensure_connected"),
    ):
        RE(scan(dae, block, start, stop, count, rel=False, model=Gaussian().fit()))
    bp_scan.assert_called_once()
    assert dae in bp_scan.call_args[0][0]
    assert block == bp_scan.call_args[0][1]
    assert start == bp_scan.call_args[0][2]
    assert stop == bp_scan.call_args[0][3]
    assert count == bp_scan.call_args[1]["num"]


@pytest.mark.parametrize(
    "scan_func",
    [
        functools.partial(scan, start=1, stop=2, num=2),
        functools.partial(adaptive_scan, start=1, stop=2, min_step=1, max_step=2, target_delta=1),
    ],
)
def test_if_in_periods_mode_and_run_saved_then_scan_start_doc_contains_run_number(
    RE, dae, block, scan_func
):
    set_mock_value(dae.current_or_next_run_number_str, "12345678")

    start_doc: dict[str, Any] | None = None

    def _cb(typ, doc):
        if typ == "start":
            nonlocal start_doc
            start_doc = doc

    with (
        patch("ibex_bluesky_core.plans.ensure_connected"),
    ):
        # Scan fails because DAE isn't set up right... but it still emits a start doc so that's fine
        with pytest.raises(bluesky.utils.FailedStatus):
            RE(scan_func(dae, block, rel=False, periods=True, save_run=True), _cb)

    assert start_doc is not None
    assert start_doc.get("run_number") == "12345678"


def test_scan_does_relative_scan_when_relative_true(RE, dae, block):
    start = 0
    stop = 2
    count = 3
    with (
        patch("ibex_bluesky_core.plans.bp.rel_scan") as bp_scan,
        patch("ibex_bluesky_core.plans.ensure_connected"),
    ):
        RE(scan(dae, block, start, stop, count, rel=True, model=Gaussian().fit()))
    bp_scan.assert_called_once()
    assert dae in bp_scan.call_args[0][0]
    assert block == bp_scan.call_args[0][1]
    assert start == bp_scan.call_args[0][2]
    assert stop == bp_scan.call_args[0][3]
    assert count == bp_scan.call_args[1]["num"]


def test_adaptive_scan_with_periods_sets_max_periods(RE, dae, block):
    expected = 50
    set_mock_value(dae.max_periods, expected)
    with (
        patch("ibex_bluesky_core.plans.bp.adaptive_scan"),
        patch("ibex_bluesky_core.plans.ensure_connected"),
    ):
        RE(
            adaptive_scan(
                dae,
                block,
                1,
                2,
                3,
                4,
                5,
                periods=True,
                model=Gaussian().fit(),
            )
        )
    get_mock_put(dae.number_of_periods.signal).assert_called_with(expected, wait=True)


def test_adaptive_scan_does_normal_scan_when_relative_false(RE, dae, block):
    start = 0
    stop = 2
    min_step = 0.01
    max_step = 0.1
    target_delta = 0.5
    with (
        patch("ibex_bluesky_core.plans.bp.adaptive_scan") as bp_scan,
        patch("ibex_bluesky_core.plans.ensure_connected"),
    ):
        RE(
            adaptive_scan(
                dae,
                block,
                start,
                stop,
                min_step,
                max_step,
                target_delta,
                rel=False,
                model=Gaussian().fit(),
            )
        )
    bp_scan.assert_called_once()
    assert dae in bp_scan.call_args[1]["detectors"]
    assert block == bp_scan.call_args[1]["motor"]
    assert start == bp_scan.call_args[1]["start"]
    assert stop == bp_scan.call_args[1]["stop"]
    assert min_step == bp_scan.call_args[1]["min_step"]
    assert max_step == bp_scan.call_args[1]["max_step"]
    assert target_delta == bp_scan.call_args[1]["target_delta"]


def test_adaptive_scan_does_relative_scan_when_relative_true(RE, dae, block):
    start = 0
    stop = 2
    min_step = 0.01
    max_step = 0.1
    target_delta = 0.5
    with (
        patch("ibex_bluesky_core.plans.bp.rel_adaptive_scan") as bp_scan,
        patch("ibex_bluesky_core.plans.ensure_connected"),
    ):
        RE(
            adaptive_scan(
                dae,
                block,
                start,
                stop,
                min_step,
                max_step,
                target_delta,
                rel=True,
                model=Gaussian().fit(),
            )
        )
    bp_scan.assert_called_once()
    assert dae in bp_scan.call_args[1]["detectors"]
    assert block == bp_scan.call_args[1]["motor"]
    assert start == bp_scan.call_args[1]["start"]
    assert stop == bp_scan.call_args[1]["stop"]
    assert min_step == bp_scan.call_args[1]["min_step"]
    assert max_step == bp_scan.call_args[1]["max_step"]
    assert target_delta == bp_scan.call_args[1]["target_delta"]


def test_save_run_adds_run_number_to_fields_in_scan(RE, dae, block):
    with (
        patch("ibex_bluesky_core.plans.ensure_connected"),
        patch("ibex_bluesky_core.plans.ISISCallbacks") as icc,
    ):
        dae.controller = RunPerPointController(save_run=True)
        _ = RE(scan(dae, block, 1, 2, 3, save_run=True, periods=False, model=Gaussian().fit()))
        assert dae.controller.run_number.name in icc.call_args[1]["measured_fields"]


def test_save_run_adds_run_number_to_fields_in_adaptive_scan(RE, dae, block):
    with (
        patch("ibex_bluesky_core.plans.ensure_connected"),
        patch("ibex_bluesky_core.plans.ISISCallbacks") as icc,
    ):
        dae.controller = RunPerPointController(save_run=True)
        _ = RE(
            adaptive_scan(
                dae, block, 1, 2, 3, 4, 5, save_run=True, periods=False, model=Gaussian().fit()
            )
        )
        assert dae.controller.run_number.name in icc.call_args[1]["measured_fields"]


def test_periods_adds_period_number_to_fields_in_scan(RE, dae, block):
    with (
        patch("ibex_bluesky_core.plans.ensure_connected"),
        patch("ibex_bluesky_core.plans.ISISCallbacks") as icc,
    ):
        dae.controller = PeriodPerPointController(save_run=False)
        _ = RE(scan(dae, block, 1, 2, 3, save_run=False, periods=True, model=Gaussian().fit()))
        assert dae.period_num.name in icc.call_args[1]["measured_fields"]


def test_periods_adds_period_number_to_fields_in_adaptive_scan(RE, dae, block):
    with (
        patch("ibex_bluesky_core.plans.ensure_connected"),
        patch("ibex_bluesky_core.plans.ISISCallbacks") as icc,
    ):
        dae.controller = PeriodPerPointController(save_run=False)
        _ = RE(
            adaptive_scan(
                dae, block, 1, 2, 3, 4, 5, save_run=False, periods=True, model=Gaussian().fit()
            )
        )
        assert dae.period_num.name in icc.call_args[1]["measured_fields"]


def test_no_periods_and_no_save_run_does_not_add_fields(RE, dae, block):
    with (
        patch("ibex_bluesky_core.plans.ensure_connected"),
        patch("ibex_bluesky_core.plans.ISISCallbacks") as icc,
    ):
        dae.controller = RunPerPointController(save_run=False)
        _ = RE(
            adaptive_scan(
                dae, block, 1, 2, 3, 4, 5, save_run=False, periods=False, model=Gaussian().fit()
            )
        )
        assert dae.period_num.name not in icc.call_args[1]["measured_fields"]
        assert dae.controller.run_number.name not in icc.call_args[1]["measured_fields"]


async def test_polling_plan_drops_readable_updates_if_no_new_motor_position(RE):
    motor = SimMotor(name="motor1", instant=False)
    motor.user_readback.set_name("motor1")
    await motor.velocity.set(2)
    block_readable = BlockR(prefix="UNITTEST:", block_name="READABLE", datatype=int)
    initial_pos = 0.1
    destination = 2
    initial_reading = 10
    RE(ensure_connected(motor, block_readable, mock=True))
    set_mock_value(block_readable.readback, initial_reading)
    await motor.set(initial_pos)

    def lots_of_updates_between_set(*args, **kwargs):
        # this will be called on a motor update, we will then make lots of readings for
        # the readable which will be dropped
        set_mock_value(block_readable.readback, initial_reading + 10)
        set_mock_value(block_readable.readback, initial_reading + 20)
        set_mock_value(block_readable.readback, initial_reading + 30)

    callback_on_mock_put(motor.user_readback, lots_of_updates_between_set)
    captured_events = []

    @run_decorator(md={})
    def p():
        return (
            yield from polling_plan(motor=motor, readable=block_readable, destination=destination)
        )  # pyright: ignore[reportArgumentType])

    RE(
        p(),
        {"event": lambda x, y: captured_events.append(y["data"])},
    )

    assert all([readable == 10 for motor, readable in [x.values() for x in captured_events]])

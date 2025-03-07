# pyright: reportMissingParameterType=false

from unittest.mock import patch

import pytest

from ibex_bluesky_core.devices.block import BlockMot
from ibex_bluesky_core.devices.simpledae import SimpleDae
from ibex_bluesky_core.devices.simpledae.reducers import MonitorNormalizer
from ibex_bluesky_core.devices.simpledae.strategies import Controller, Waiter
from ibex_bluesky_core.plans import adaptive_scan, motor_adaptive_scan, motor_scan, scan


def test_scan_motor_creates_block_device_and_dae(RE):
    prefix = "UNITTEST:"
    block_name = "some_block"
    with (
        patch("ibex_bluesky_core.plans.get_pv_prefix", return_value=prefix),
        patch("ibex_bluesky_core.devices.simpledae.get_pv_prefix", return_value=prefix),
        patch("ibex_bluesky_core.plans.scan") as scan,
    ):
        RE(motor_scan(block_name=block_name, start=0, stop=2, count=3, frames=200))
        scan.assert_called_once()
        assert isinstance(scan.call_args[1]["dae"], SimpleDae)
        assert isinstance(scan.call_args[1]["block"], BlockMot)
        assert scan.call_args[1]["block"].name == block_name


def test_adaptive_scan_motor_creates_block_device_and_dae(RE):
    prefix = "UNITTEST:"
    block_name = "some_block"
    with (
        patch("ibex_bluesky_core.plans.get_pv_prefix", return_value=prefix),
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
            )
        )
        scan.assert_called_once()
        assert isinstance(scan.call_args[1]["dae"], SimpleDae)
        assert isinstance(scan.call_args[1]["block"], BlockMot)
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
        RE(scan(dae, block, start, stop, count, rel=False))
    bp_scan.assert_called_once()
    assert dae in bp_scan.call_args[0][0]
    assert block == bp_scan.call_args[0][1]
    assert start == bp_scan.call_args[0][2]
    assert stop == bp_scan.call_args[0][3]
    assert count == bp_scan.call_args[1]["num"]


def test_scan_does_relative_scan_when_relative_true(RE, dae, block):
    start = 0
    stop = 2
    count = 3
    with (
        patch("ibex_bluesky_core.plans.bp.rel_scan") as bp_scan,
        patch("ibex_bluesky_core.plans.ensure_connected"),
    ):
        RE(scan(dae, block, start, stop, count, rel=True))
    bp_scan.assert_called_once()
    assert dae in bp_scan.call_args[0][0]
    assert block == bp_scan.call_args[0][1]
    assert start == bp_scan.call_args[0][2]
    assert stop == bp_scan.call_args[0][3]
    assert count == bp_scan.call_args[1]["num"]


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
        RE(adaptive_scan(dae, block, start, stop, min_step, max_step, target_delta, rel=False))
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
        RE(adaptive_scan(dae, block, start, stop, min_step, max_step, target_delta, rel=True))
    bp_scan.assert_called_once()
    assert dae in bp_scan.call_args[1]["detectors"]
    assert block == bp_scan.call_args[1]["motor"]
    assert start == bp_scan.call_args[1]["start"]
    assert stop == bp_scan.call_args[1]["stop"]
    assert min_step == bp_scan.call_args[1]["min_step"]
    assert max_step == bp_scan.call_args[1]["max_step"]
    assert target_delta == bp_scan.call_args[1]["target_delta"]


# test scan summarise
# test adaptive_scan summarise

# test save_run for scan
# test save_run for adaptive_scan

# test periods for scan
# test periods for adaptive_scan

# test polling plan

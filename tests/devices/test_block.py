# pyright: reportMissingParameterType=false

import asyncio
import sys
from unittest.mock import ANY, MagicMock, patch

import bluesky.plan_stubs as bps
import bluesky.plans as bp
import pytest
from ophyd_async.core import get_mock_put, set_mock_value

from ibex_bluesky_core.devices.block import (
    BlockMot,
    BlockR,
    BlockRw,
    BlockRwRbv,
    BlockWriteConfig,
    block_mot,
    block_r,
    block_rw,
    block_rw_rbv,
)
from tests.conftest import MOCK_PREFIX

if sys.version_info < (3, 11):
    aio_timeout_error = asyncio.exceptions.TimeoutError
else:
    aio_timeout_error = TimeoutError


async def _make_block(clazz):
    block = clazz(float, MOCK_PREFIX, "float_block")
    await block.connect(mock=True)
    return block


@pytest.fixture
async def rw_rbv_block() -> BlockRwRbv[float]:
    return await _make_block(BlockRwRbv)


@pytest.fixture(params=[BlockRw, BlockRwRbv])
async def writable_block(request) -> BlockRw[float]:
    return await _make_block(request.param)


@pytest.fixture(params=[BlockR, BlockRw, BlockRwRbv])
async def readable_block(request) -> BlockR[float]:
    return await _make_block(request.param)


@pytest.fixture
async def mot_block():
    block = BlockMot(MOCK_PREFIX, "mot_block")
    await block.connect(mock=True)
    return block


async def _block_with_write_config(write_config: BlockWriteConfig[float]) -> BlockRwRbv[float]:
    block = BlockRwRbv(float, MOCK_PREFIX, "block", write_config=write_config)
    await block.connect(mock=True)
    return block


def test_block_naming(rw_rbv_block):
    assert rw_rbv_block.name == "float_block"
    assert rw_rbv_block.setpoint.name == "float_block-setpoint"
    assert rw_rbv_block.setpoint_readback.name == "float_block-setpoint_readback"
    assert rw_rbv_block.readback.name == "float_block"


def test_mot_block_naming(mot_block):
    assert mot_block.name == "mot_block"
    assert mot_block.user_readback.name == "mot_block"
    assert mot_block.user_setpoint.name == ("mot_block-user_setpoint" "")


def test_block_signal_monitors_correct_pv(rw_rbv_block):
    assert rw_rbv_block.readback.source.endswith("UNITTEST:MOCK:CS:SB:float_block")
    assert rw_rbv_block.setpoint.source.endswith("UNITTEST:MOCK:CS:SB:float_block:SP")
    assert rw_rbv_block.setpoint_readback.source.endswith("UNITTEST:MOCK:CS:SB:float_block:SP:RBV")


def test_mot_block_monitors_correct_pv(mot_block):
    # The SP:RBV here is intentional - GWBLOCK mangles mot_block by "swapping" .RBV and .VAL,
    # but doesn't mangle the :SP:RBV motor record alias, so we use that instead.
    assert mot_block.user_setpoint.source.endswith("UNITTEST:MOCK:CS:SB:mot_block:SP:RBV.VAL")
    assert mot_block.user_readback.source.endswith("UNITTEST:MOCK:CS:SB:mot_block:SP:RBV.RBV")


async def test_locate(rw_rbv_block):
    set_mock_value(rw_rbv_block.readback, 10)
    set_mock_value(rw_rbv_block.setpoint, 20)
    set_mock_value(rw_rbv_block.setpoint_readback, 30)
    location = await rw_rbv_block.locate()

    assert location == {
        "readback": 10,
        "setpoint": 30,  # Should use SP:RBV not SP
    }


async def test_hints(readable_block):
    # The primary readback should be the only "hinted" signal on a block
    assert readable_block.hints == {"fields": ["float_block"]}


async def test_mot_hints(mot_block):
    assert mot_block.hints == {"fields": ["mot_block"]}


async def test_read(rw_rbv_block):
    set_mock_value(rw_rbv_block.readback, 10.0)
    set_mock_value(rw_rbv_block.setpoint, 20.0)
    set_mock_value(rw_rbv_block.setpoint_readback, 30.0)
    reading = await rw_rbv_block.read()

    assert reading == {
        "float_block": {
            "alarm_severity": 0,
            "timestamp": ANY,
            "value": 10.0,
        },
        "float_block-setpoint_readback": {
            "alarm_severity": 0,
            "timestamp": ANY,
            "value": 30.0,
        },
    }


async def test_describe(rw_rbv_block):
    set_mock_value(rw_rbv_block.readback, 10.0)
    set_mock_value(rw_rbv_block.setpoint, 20.0)
    set_mock_value(rw_rbv_block.setpoint_readback, 30.0)
    reading = await rw_rbv_block.read()
    descriptor = await rw_rbv_block.describe()

    assert reading.keys() == descriptor.keys()

    assert descriptor["float_block"]["dtype"] == "number"
    assert descriptor["float_block-setpoint_readback"]["dtype"] == "number"


async def test_read_and_describe_configuration(readable_block):
    # Blocks don't have any configuration signals at the moment so these should be empty
    configuration_reading = await readable_block.read_configuration()
    configuration_descriptor = await readable_block.describe_configuration()
    assert configuration_reading == {}
    assert configuration_descriptor == {}


async def test_block_set(writable_block):
    set_mock_value(writable_block.setpoint, 10)
    await writable_block.set(20)
    get_mock_put(writable_block.setpoint).assert_called_once_with(20, wait=True, timeout=None)


async def test_block_set_without_epics_completion_callback():
    block = await _block_with_write_config(BlockWriteConfig(use_completion_callback=False))
    await block.set(20)
    get_mock_put(block.setpoint).assert_called_once_with(20, wait=False, timeout=None)


async def test_block_set_with_arbitrary_completion_function():
    func = MagicMock(return_value=True)
    block = await _block_with_write_config(BlockWriteConfig(set_success_func=func))

    set_mock_value(block.readback, 10)
    set_mock_value(block.setpoint_readback, 30)

    await block.set(20)

    func.assert_called_once_with(20, 10)


async def test_block_set_with_timeout():
    func = MagicMock(return_value=False)  # Never completes
    block = await _block_with_write_config(
        BlockWriteConfig(set_success_func=func, set_timeout_s=0.1)
    )

    set_mock_value(block.readback, 10)

    with pytest.raises(aio_timeout_error):
        await block.set(20)

    func.assert_called_once_with(20, 10)


async def test_block_set_which_completes_before_timeout():
    block = await _block_with_write_config(
        BlockWriteConfig(use_completion_callback=False, set_timeout_s=1)
    )
    await block.set(20)


async def test_block_set_with_settle_time_longer_than_timeout():
    block = await _block_with_write_config(
        BlockWriteConfig(use_completion_callback=False, set_timeout_s=1, settle_time_s=30)
    )

    with patch("ibex_bluesky_core.devices.block.asyncio.sleep") as mock_aio_sleep:
        await block.set(20)
        mock_aio_sleep.assert_called_once_with(30)


@pytest.mark.parametrize(
    "func,args",
    [
        (block_r, (float, "some_block")),
        (block_rw, (float, "some_block")),
        (block_rw_rbv, (float, "some_block")),
        (block_mot, ("some_block",)),
    ],
)
def test_block_utility_function(func, args):
    with patch("ibex_bluesky_core.devices.block.get_pv_prefix") as mock_get_prefix:
        mock_get_prefix.return_value = MOCK_PREFIX
        block = func(*args)
        assert block.name == "some_block"


async def test_runcontrol_read_and_describe(readable_block):
    reading = await readable_block.run_control.read()
    descriptor = await readable_block.run_control.describe()

    assert reading.keys() == descriptor.keys()

    assert reading.keys() == {
        "float_block-run_control-in_range",
    }

    assert reading["float_block-run_control-in_range"] == {
        "alarm_severity": 0,
        "timestamp": ANY,
        "value": False,
    }
    assert descriptor["float_block-run_control-in_range"]["dtype"] == "boolean"


async def test_runcontrol_hints(readable_block):
    # Hinted field for explicitly reading run-control: is the reading in range?
    hints = readable_block.run_control.hints
    assert hints == {"fields": ["float_block-run_control-in_range"]}


async def test_runcontrol_monitors_correct_pv(readable_block):
    source = readable_block.run_control.in_range.source
    assert source.endswith("UNITTEST:MOCK:CS:SB:float_block:RC:INRANGE")


async def test_mot_block_runcontrol_monitors_correct_pv(mot_block):
    source = mot_block.run_control.in_range.source
    # The main "motor" uses mot_block:SP:RBV, but run control should not.
    assert source.endswith("UNITTEST:MOCK:CS:SB:mot_block:RC:INRANGE")


def test_plan_count_block(RE, readable_block):
    set_mock_value(readable_block.readback, 123.0)

    docs = []
    result = RE(bp.count([readable_block]), lambda typ, doc: docs.append((typ, doc)))
    assert result.exit_status == "success"

    # Should have one event document
    assert len([doc for (typ, doc) in docs if typ == "event"]) == 1

    for typ, doc in docs:
        if typ == "event":
            assert doc["data"]["float_block"] == 123.0


def test_plan_rd_block(RE, readable_block):
    set_mock_value(readable_block.readback, 123.0)
    result = RE(bps.rd(readable_block))
    assert result.plan_result == 123.0


def test_plan_trigger_block(RE, readable_block):
    # A block must be able to be triggered for use in adaptive scans.
    result = RE(bps.trigger(readable_block))
    assert result.exit_status == "success"


def test_plan_mv_block(RE, writable_block):
    set_mock_value(writable_block.setpoint, 123.0)
    RE(bps.mv(writable_block, 456.0))
    get_mock_put(writable_block.setpoint).assert_called_once_with(456.0, wait=True, timeout=None)


def test_block_reprs():
    assert repr(BlockR(float, block_name="foo", prefix="")) == "BlockR(name=foo)"
    assert repr(BlockRw(float, block_name="bar", prefix="")) == "BlockRw(name=bar)"
    assert repr(BlockRwRbv(float, block_name="baz", prefix="")) == "BlockRwRbv(name=baz)"
    assert repr(BlockMot(block_name="qux", prefix="")) == "BlockMot(name=qux)"

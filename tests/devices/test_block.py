import asyncio
import sys
from unittest.mock import MagicMock, patch

import pytest
from ibex_bluesky_core.devices.block import (
    BlockRwRbv,
    BlockWriteConfiguration,
    block_r,
    block_rw,
    block_rw_rbv,
)
from ophyd_async.core import get_mock_put, set_mock_value

MOCK_PREFIX = "UNITTEST:MOCK:"


if sys.version_info < (3, 11):
    aio_timeout_error = asyncio.exceptions.TimeoutError
else:
    aio_timeout_error = TimeoutError


@pytest.fixture
async def simple_block() -> BlockRwRbv[float]:
    block = BlockRwRbv(float, MOCK_PREFIX, "float_block")
    await block.connect(mock=True)
    return block


async def _block_with_write_config(write_config: BlockWriteConfiguration) -> BlockRwRbv[float]:
    block = BlockRwRbv(float, MOCK_PREFIX, "block", write_config=write_config)
    await block.connect(mock=True)
    return block


def test_block_naming(simple_block):
    assert simple_block.name == "float_block"
    assert simple_block.setpoint.name == "float_block-setpoint"
    assert simple_block.setpoint_readback.name == "float_block-setpoint_readback"
    assert simple_block.readback.name == "float_block"


def test_block_signal_monitors_correct_pv(simple_block):
    assert simple_block.readback.source.endswith("UNITTEST:MOCK:CS:SB:float_block")
    assert simple_block.setpoint.source.endswith("UNITTEST:MOCK:CS:SB:float_block:SP")
    assert simple_block.setpoint_readback.source.endswith("UNITTEST:MOCK:CS:SB:float_block:SP:RBV")


async def test_locate(simple_block):
    set_mock_value(simple_block.readback, 10)
    set_mock_value(simple_block.setpoint, 20)
    set_mock_value(simple_block.setpoint_readback, 30)
    location = await simple_block.locate()

    assert location == {
        "readback": 10,
        "setpoint": 30,  # Should use SP:RBV not SP
    }


async def test_block_set(simple_block):
    set_mock_value(simple_block.setpoint, 10)
    await simple_block.set(20)
    get_mock_put(simple_block.setpoint).assert_called_once_with(20, wait=True, timeout=None)


async def test_block_set_without_epics_completion_callback():
    block = await _block_with_write_config(BlockWriteConfiguration(use_completion_callback=False))
    await block.set(20)
    get_mock_put(block.setpoint).assert_called_once_with(20, wait=False, timeout=None)


async def test_block_set_with_arbitrary_completion_function():
    func = MagicMock(return_value=True)
    block = await _block_with_write_config(BlockWriteConfiguration(set_success_func=func))

    set_mock_value(block.readback, 10)
    set_mock_value(block.setpoint_readback, 30)

    await block.set(20)

    func.assert_called_once_with(20, 10)


async def test_block_set_with_timeout():
    func = MagicMock(return_value=False)  # Never completes
    block = await _block_with_write_config(
        BlockWriteConfiguration(set_success_func=func, set_timeout_s=0.1)
    )

    set_mock_value(block.readback, 10)

    with pytest.raises(aio_timeout_error):
        await block.set(20)

    func.assert_called_once_with(20, 10)


async def test_block_set_which_completes_before_timeout():
    block = await _block_with_write_config(
        BlockWriteConfiguration(use_completion_callback=False, set_timeout_s=1)
    )

    await block.set(20)


async def test_block_set_with_settle_time_longer_than_timeout():
    block = await _block_with_write_config(
        BlockWriteConfiguration(use_completion_callback=False, set_timeout_s=1, settle_time_s=30)
    )

    with patch("ibex_bluesky_core.devices.block.asyncio.sleep") as mock_aio_sleep:
        await block.set(20)

        mock_aio_sleep.assert_called_once_with(30)


@pytest.mark.parametrize("func", [block_r, block_rw, block_rw_rbv])
def test_block_utility_function(func):
    with patch("ibex_bluesky_core.devices.block.get_pv_prefix") as mock_get_prefix:
        mock_get_prefix.return_value = MOCK_PREFIX
        block = func(float, "some_block")
        assert block.readback.source.endswith("UNITTEST:MOCK:CS:SB:some_block")

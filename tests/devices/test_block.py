import pytest
from ophyd_async.core import get_mock_put, set_mock_value

from ibex_bluesky_core.devices.block import Block


@pytest.fixture
async def float_block() -> Block[float]:
    block = Block("UNITTEST:MOCK:", "float_block", float)
    await block.connect(mock=True)
    return block


def test_block_naming(float_block):
    assert float_block.name == "float_block"
    assert float_block.setpoint.name == "float_block-setpoint"
    assert float_block.readback.name == "float_block"


def test_block_signal_monitors_correct_pv(float_block):
    assert float_block.readback.source.endswith("UNITTEST:MOCK:CS:SB:float_block")
    assert float_block.setpoint.source.endswith("UNITTEST:MOCK:CS:SB:float_block:SP")


async def test_locate(float_block):
    set_mock_value(float_block.readback, 10)
    set_mock_value(float_block.setpoint, 20)
    location = await float_block.locate()

    assert location == {
        "readback": 10,
        "setpoint": 20,
    }


async def test_block_set(float_block):
    set_mock_value(float_block.setpoint, 10)
    await float_block.set(20)
    get_mock_put(float_block.setpoint).assert_called_once_with(20, wait=True, timeout=10)

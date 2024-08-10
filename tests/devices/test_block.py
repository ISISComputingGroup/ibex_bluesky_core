import pytest
from ibex_bluesky_core.devices.block import BlockRwRbv
from ophyd_async.core import get_mock_put, set_mock_value


@pytest.fixture
async def float_block() -> BlockRwRbv[float]:
    block = BlockRwRbv(float, "UNITTEST:MOCK:", "float_block")
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
    set_mock_value(float_block.setpoint_readback, 30)
    location = await float_block.locate()

    assert location == {
        "readback": 10,
        "setpoint": 30,  # Should use SP:RBV not SP
    }


async def test_block_set(float_block):
    set_mock_value(float_block.setpoint, 10)
    await float_block.set(20)
    get_mock_put(float_block.setpoint).assert_called_once_with(20, wait=True, timeout=None)

from unittest.mock import patch

from ibex_bluesky_core.devices.block import Block


def test_block_naming():
    block = Block("dummy_name", float)

    assert block.name == "dummy_name"


def test_block_signal_monitors_correct_pv():
    with patch("ibex_bluesky_core.devices.block.get_pv_prefix") as mock_prefix:
        mock_prefix.return_value = "UNITTEST:MOCK:"

        block = Block("block_name", float)
        assert block.value.source == "ca://UNITTEST:MOCK:CS:SB:block_name"

# pyright: reportMissingParameterType=false

from unittest.mock import patch

from ibex_bluesky_core.devices.block import BlockMot
from ibex_bluesky_core.devices.simpledae import SimpleDae
from ibex_bluesky_core.plans import motor_adaptive_scan, motor_scan


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


# test scan does normal scan with mock
# test scan does relative scan with mock

# test adaptive_scan does normal adaptive scan with mock
# test adaptive_scan does relative adaptive scan with mock

# test scan summarise

# test adaptive_scan summarise

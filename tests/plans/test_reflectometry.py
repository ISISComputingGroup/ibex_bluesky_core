# pyright: reportMissingParameterType=false

from unittest.mock import patch

from ibex_bluesky_core.devices.reflectometry import ReflParameter
from ibex_bluesky_core.devices.simpledae import SimpleDae
from ibex_bluesky_core.plans.reflectometry import refl_adaptive_scan, refl_scan


def test_refl_scan_creates_refl_param_device_and_dae(RE):
    prefix = "UNITTEST:"
    param_name = "theta"
    with (
        patch("ibex_bluesky_core.devices.reflectometry.get_pv_prefix", return_value=prefix),
        patch("ibex_bluesky_core.devices.simpledae.get_pv_prefix", return_value=prefix),
        patch("ibex_bluesky_core.plans.reflectometry.scan") as scan,
    ):
        RE(refl_scan(param=param_name, start=0, stop=2, count=3, frames=200))
        scan.assert_called_once()
        assert isinstance(scan.call_args[1]["dae"], SimpleDae)
        assert isinstance(scan.call_args[1]["block"], ReflParameter)
        assert scan.call_args[1]["block"].name == param_name


def test_refl_adaptive_scan_creates_refl_param_device_and_dae(RE):
    prefix = "UNITTEST:"
    param_name = "S1VG"
    with (
        patch("ibex_bluesky_core.devices.reflectometry.get_pv_prefix", return_value=prefix),
        patch("ibex_bluesky_core.devices.simpledae.get_pv_prefix", return_value=prefix),
        patch("ibex_bluesky_core.plans.reflectometry.adaptive_scan") as scan,
    ):
        RE(
            refl_adaptive_scan(
                param=param_name,
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
        assert isinstance(scan.call_args[1]["block"], ReflParameter)
        assert scan.call_args[1]["block"].name == param_name

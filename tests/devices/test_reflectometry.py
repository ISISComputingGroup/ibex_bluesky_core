# pyright: reportMissingParameterType=false
import asyncio
from unittest.mock import patch

import bluesky.plan_stubs as bps
import pytest
from ophyd_async.plan_stubs import ensure_connected
from ophyd_async.testing import callback_on_mock_put, get_mock_put, set_mock_value

from ibex_bluesky_core.devices.reflectometry import (
    ReflParameter,
    ReflParameterRedefine,
    refl_parameter,
)


def test_refl_parameter_wrapper_returns_refl_parameter():
    prefix = "UNITTEST:"
    name = "S2VG"
    with patch("ibex_bluesky_core.devices.reflectometry.get_pv_prefix", return_value=prefix):
        param: ReflParameter = refl_parameter(name=name)

    assert param.name == name
    assert param.readback.source == f"ca://{prefix}REFL_01:PARAM:{name}"


def test_set_waits_for_changed_on_reflectometry_parameter(RE):
    param = ReflParameter(prefix="UNITTEST:", name="S1VG", changing_timeout_s=0.01)
    RE(ensure_connected(param, mock=True))
    initial = 123.0
    set_mock_value(param.setpoint, initial)
    set_mock_value(param.changing, False)
    callback_on_mock_put(param.setpoint, lambda *a, **k: set_mock_value(param.changing, False))
    new_value = 456.0
    RE(bps.mv(param, new_value))
    get_mock_put(param.setpoint).assert_called_once_with(new_value, wait=True)


async def test_times_out_if_changing_never_finishes_on_reflectometry_parameter(RE):
    param = ReflParameter(prefix="UNITTEST:", name="S1VG", changing_timeout_s=0.01)
    RE(ensure_connected(param, mock=True))
    initial = 123.0
    set_mock_value(param.setpoint, initial)
    set_mock_value(param.changing, True)
    new_value = 456.0
    with pytest.raises(asyncio.TimeoutError):
        await param.set(new_value)


def test_set_waits_for_changed_on_reflectometry_parameter_redefine(RE):
    param = ReflParameterRedefine(prefix="UNITTEST:S1VG", name="redefine", changed_timeout_s=0.01)
    RE(ensure_connected(param, mock=True))
    initial = 123.0
    set_mock_value(param.define_pos_sp, initial)
    set_mock_value(param.changed, False)
    callback_on_mock_put(param.define_pos_sp, lambda *a, **k: set_mock_value(param.changed, True))
    new_value = 456.0
    RE(bps.mv(param, new_value))
    get_mock_put(param.define_pos_sp).assert_called_once_with(new_value, wait=True)


async def test_times_out_if_changed_never_finishes_on_reflectometery_parameter_redefine(RE):
    param = ReflParameterRedefine(prefix="UNITTEST:S1VG", name="redefine", changed_timeout_s=0.01)
    RE(ensure_connected(param, mock=True))
    initial = 123.0
    set_mock_value(param.define_pos_sp, initial)
    set_mock_value(param.changed, False)
    new_value = 456.0
    with pytest.raises(asyncio.TimeoutError):
        await param.set(new_value)

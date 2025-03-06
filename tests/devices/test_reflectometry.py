import bluesky.plan_stubs as bps
from ophyd_async.testing import get_mock_put, set_mock_value

from ibex_bluesky_core.devices.reflectometry import ReflParameter


def test_set_waits_for_changed_on_reflectometry_parameter(RE):
    param = ReflParameter(prefix="UNITTEST:", name="S1VG")
    set_mock_value(param.setpoint, 123.0)
    set_mock_value(param.changing, False)

    RE(bps.mv(param, 456.0))  # TODO probably set param.changing to 0 here?

    get_mock_put(param.setpoint).assert_called_once_with(456.0, wait=True)


def test_set_waits_for_changed_on_reflectometry_parameter_redefine():
    pass


def test_times_out_if_changing_never_finishes_on_reflectometry_parameter(RE):
    pass


def test_times_out_if_changed_never_finishes_on_reflectometery_parameter_redefine():
    pass

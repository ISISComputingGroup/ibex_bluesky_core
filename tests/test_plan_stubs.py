# pyright: reportMissingParameterType=false
import time
from asyncio import CancelledError
from unittest.mock import MagicMock, call, patch
from xml.etree import ElementTree as ET

import matplotlib.pyplot as plt
import pytest
from bluesky import RunEngine
from bluesky import plan_stubs as bps
from bluesky.utils import Msg
from ophyd_async.epics.motor import UseSetMode
from ophyd_async.plan_stubs import ensure_connected
from ophyd_async.testing import get_mock_put, set_mock_value

from ibex_bluesky_core.devices import NoYesChoice, compress_and_hex, dehex_and_decompress
from ibex_bluesky_core.devices.block import BlockMot
from ibex_bluesky_core.devices.dae import (
    Dae,
    DaeSettingsData,
    DaeTCBSettingsData,
    TCBCalculationMethod,
    TCBTimeUnit,
)
from ibex_bluesky_core.devices.dae._tcb_settings import _convert_xml_to_tcb_settings
from ibex_bluesky_core.devices.reflectometry import ReflParameter
from ibex_bluesky_core.plan_stubs import (
    CALL_QT_AWARE_MSG_KEY,
    call_qt_aware,
    call_sync,
    prompt_user_for_choice,
    redefine_motor,
    redefine_refl_parameter,
    with_dae_tables,
    with_num_periods,
    with_time_channels,
)
from ibex_bluesky_core.run_engine._msg_handlers import call_sync_handler
from tests.devices.dae_testing_data import dae_settings_template, tcb_settings_template


def test_call_sync_returns_result(RE):
    def f(arg, keyword_arg):
        assert arg == "foo"
        assert keyword_arg == "bar"
        return 123

    result = RE(call_sync(f, "foo", keyword_arg="bar"))

    assert result.plan_result == 123


@pytest.mark.filterwarnings("ignore::pytest.PytestUnhandledThreadExceptionWarning")
def test_call_sync_throws_exception(RE):
    def f():
        raise ValueError("broke it")

    with pytest.raises(ValueError, match="broke it"):
        RE(call_sync(f))


@pytest.mark.parametrize("err", [(KeyboardInterrupt,), (CancelledError,)])
async def test_call_sync_handler_blocking_python(err: type[BaseException]):
    def f():
        while True:
            pass

    with patch("ibex_bluesky_core.run_engine._msg_handlers.Event") as evt:
        evt.return_value.wait.side_effect = err
        msg = Msg("", f)
        with pytest.raises(err):
            await call_sync_handler(msg)


@pytest.mark.parametrize("err", [(KeyboardInterrupt,), (CancelledError,)])
async def test_call_sync_handler_blocking_native(err: type[BaseException]):
    def f():
        while True:
            time.sleep(1)

    with patch("ibex_bluesky_core.run_engine._msg_handlers.Event") as evt:
        evt.return_value.wait.side_effect = err
        msg = Msg("", f)
        with pytest.raises(err):
            await call_sync_handler(msg)


def test_call_sync_waits_for_completion(RE):
    def f():
        time.sleep(1)

    start = time.monotonic()
    RE(call_sync(f))
    end = time.monotonic()

    assert end - start == pytest.approx(1, abs=0.2)


def test_call_qt_aware_returns_result(RE):
    def f(arg, keyword_arg):
        assert arg == "foo"
        assert keyword_arg == "bar"
        return 123

    def plan():
        return (yield Msg(CALL_QT_AWARE_MSG_KEY, f, "foo", keyword_arg="bar"))

    result = RE(plan())

    assert result.plan_result == 123


def test_call_qt_aware_throws_exception(RE):
    def f():
        raise ValueError("broke it")

    def plan():
        return (yield Msg(CALL_QT_AWARE_MSG_KEY, f))

    with pytest.raises(ValueError, match="broke it"):
        RE(plan())


def test_call_qt_aware_matplotlib_function(RE):
    mock = MagicMock(spec=plt.close)
    mock.__module__ = "matplotlib.pyplot"
    mock.return_value = 123

    def plan():
        return (yield from call_qt_aware(mock, "all"))

    result = RE(plan())
    assert result.plan_result == 123
    mock.assert_called_once_with("all")


def test_call_qt_aware_non_matplotlib_function(RE):
    mock = MagicMock()
    mock.__module__ = "some_random_module"

    def plan():
        return (yield from call_qt_aware(mock, "arg", keyword_arg="kwarg"))

    with pytest.raises(
        ValueError, match="Only matplotlib functions should be passed to call_qt_aware"
    ):
        RE(plan())

    mock.assert_not_called()


def test_redefine_motor(RE):
    motor = BlockMot(prefix="", block_name="some_motor")

    def plan():
        yield from ensure_connected(motor, mock=True)
        yield from redefine_motor(motor, 42.0)

    RE(plan())

    get_mock_put(motor.set_use_switch).assert_has_calls(
        [call(UseSetMode.SET, wait=True), call(UseSetMode.USE, wait=True)]
    )

    get_mock_put(motor.user_setpoint).assert_called_once_with(42.0, wait=True)


async def test_redefine_refl_parameter(RE):
    param = ReflParameter(prefix="", name="some_refl_parameter", changing_timeout_s=60)
    await param.connect(mock=True)
    set_mock_value(param.redefine.manager_mode, NoYesChoice.YES)  # pyright: ignore [reportOptionalMemberAccess]

    RE(redefine_refl_parameter(param, 42.0))

    get_mock_put(param.redefine.define_pos_sp).assert_called_once_with(42.0, wait=True)  # pyright: ignore [reportOptionalMemberAccess]


async def test_raises_when_attempting_to_redefine_refl_parameter_with_no_redefine(RE):
    param = ReflParameter(
        prefix="", name="some_refl_parameter_no_redefine", changing_timeout_s=1, has_redefine=False
    )
    await param.connect(mock=True)
    with pytest.raises(
        ValueError,
        match=r"Parameter some_refl_parameter_no_redefine"
        r" cannot be redefined.",
    ):
        RE(redefine_refl_parameter(param, 42.0))


def test_get_user_input(RE):
    with patch("ibex_bluesky_core.plan_stubs.input") as mock_input:
        mock_input.__name__ = "mock"
        mock_input.side_effect = ["foo", "bar", "baz"]

        result = RE(prompt_user_for_choice(prompt="choice?", choices=["bar", "baz"]))
        assert result.plan_result == "bar"


def test_num_periods_wrapper(dae: Dae, RE: RunEngine):
    original_settings = 4

    set_mock_value(dae.number_of_periods.signal, original_settings)

    with patch("ibex_bluesky_core.plan_stubs._num_periods_wrapper.ensure_connected"):
        RE(
            with_num_periods(
                bps.null(),
                dae=dae,
                number_of_periods=80,
            )
        )

    mock_set_calls = get_mock_put(dae.number_of_periods.signal).call_args_list

    assert mock_set_calls[0].args[0] == 80
    assert mock_set_calls[1].args[0] == original_settings


def test_time_channels_wrapper(dae: Dae, RE: RunEngine):
    expected_tcb_file = "C:\\tcb.dat"
    expected_calc_method = TCBCalculationMethod.SPECIFY_PARAMETERS
    expected_time_unit = TCBTimeUnit.MICROSECONDS

    modified_settings = DaeTCBSettingsData(time_unit=TCBTimeUnit.NANOSECONDS)

    original_tcb_settings = tcb_settings_template.format(
        tcb_file=expected_tcb_file,
        time_units=expected_time_unit.value,
        calc_method=expected_calc_method.value,
        tr1_mode_1=1,
        tr1_from_1=1,
        tr1_to_1=1,
        tr1_steps_1=1,
        tr1_mode_2=1,
        tr1_from_2=1,
        tr1_to_2=1,
        tr1_steps_2=1,
        tr1_mode_3=1,
        tr1_from_3=1,
        tr1_to_3=1,
        tr1_steps_3=1,
        tr1_mode_4=1,
        tr1_from_4=1,
        tr1_to_4=1,
        tr1_steps_4=1,
        tr1_mode_5=1,
        tr1_from_5=1,
        tr1_to_5=1,
        tr1_steps_5=1,
        tr2_mode_1=1,
        tr2_from_1=1,
        tr2_to_1=1,
        tr2_steps_1=1,
        tr2_mode_2=1,
        tr2_from_2=1,
        tr2_to_2=1,
        tr2_steps_2=1,
        tr2_mode_3=1,
        tr2_from_3=1,
        tr2_to_3=1,
        tr2_steps_3=1,
        tr2_mode_4=1,
        tr2_from_4=1,
        tr2_to_4=1,
        tr2_steps_4=1,
        tr2_mode_5=1,
        tr2_from_5=1,
        tr2_to_5=1,
        tr2_steps_5=1,
        tr3_mode_1=1,
        tr3_from_1=1,
        tr3_to_1=1,
        tr3_steps_1=1,
        tr3_mode_2=1,
        tr3_from_2=1,
        tr3_to_2=1,
        tr3_steps_2=1,
        tr3_mode_3=1,
        tr3_from_3=1,
        tr3_to_3=1,
        tr3_steps_3=1,
        tr3_mode_4=1,
        tr3_from_4=1,
        tr3_to_4=1,
        tr3_steps_4=1,
        tr3_mode_5=1,
        tr3_from_5=1,
        tr3_to_5=1,
        tr3_steps_5=1,
        tr4_mode_1=1,
        tr4_from_1=1,
        tr4_to_1=1,
        tr4_steps_1=1,
        tr4_mode_2=1,
        tr4_from_2=1,
        tr4_to_2=1,
        tr4_steps_2=1,
        tr4_mode_3=1,
        tr4_from_3=1,
        tr4_to_3=1,
        tr4_steps_3=1,
        tr4_mode_4=1,
        tr4_from_4=1,
        tr4_to_4=1,
        tr4_steps_4=1,
        tr4_mode_5=1,
        tr4_from_5=1,
        tr4_to_5=1,
        tr4_steps_5=1,
        tr5_mode_1=1,
        tr5_from_1=1,
        tr5_to_1=1,
        tr5_steps_1=1,
        tr5_mode_2=1,
        tr5_from_2=1,
        tr5_to_2=1,
        tr5_steps_2=1,
        tr5_mode_3=1,
        tr5_from_3=1,
        tr5_to_3=1,
        tr5_steps_3=1,
        tr5_mode_4=1,
        tr5_from_4=1,
        tr5_to_4=1,
        tr5_steps_4=1,
        tr5_mode_5=1,
        tr5_from_5=1,
        tr5_to_5=1,
        tr5_steps_5=1,
        tr6_mode_1=1,
        tr6_from_1=1,
        tr6_to_1=1,
        tr6_steps_1=1,
        tr6_mode_2=1,
        tr6_from_2=1,
        tr6_to_2=1,
        tr6_steps_2=1,
        tr6_mode_3=1,
        tr6_from_3=1,
        tr6_to_3=1,
        tr6_steps_3=1,
        tr6_mode_4=1,
        tr6_from_4=1,
        tr6_to_4=1,
        tr6_steps_4=1,
        tr6_mode_5=1,
        tr6_from_5=1,
        tr6_to_5=1,
        tr6_steps_5=1,
    )

    modified_raw_tcb_settings = tcb_settings_template.format(
        tcb_file=expected_tcb_file,
        time_units=TCBTimeUnit.NANOSECONDS.value,
        calc_method=expected_calc_method.value,
        tr1_mode_1=1,
        tr1_from_1=1,
        tr1_to_1=1,
        tr1_steps_1=1,
        tr1_mode_2=1,
        tr1_from_2=1,
        tr1_to_2=1,
        tr1_steps_2=1,
        tr1_mode_3=1,
        tr1_from_3=1,
        tr1_to_3=1,
        tr1_steps_3=1,
        tr1_mode_4=1,
        tr1_from_4=1,
        tr1_to_4=1,
        tr1_steps_4=1,
        tr1_mode_5=1,
        tr1_from_5=1,
        tr1_to_5=1,
        tr1_steps_5=1,
        tr2_mode_1=1,
        tr2_from_1=1,
        tr2_to_1=1,
        tr2_steps_1=1,
        tr2_mode_2=1,
        tr2_from_2=1,
        tr2_to_2=1,
        tr2_steps_2=1,
        tr2_mode_3=1,
        tr2_from_3=1,
        tr2_to_3=1,
        tr2_steps_3=1,
        tr2_mode_4=1,
        tr2_from_4=1,
        tr2_to_4=1,
        tr2_steps_4=1,
        tr2_mode_5=1,
        tr2_from_5=1,
        tr2_to_5=1,
        tr2_steps_5=1,
        tr3_mode_1=1,
        tr3_from_1=1,
        tr3_to_1=1,
        tr3_steps_1=1,
        tr3_mode_2=1,
        tr3_from_2=1,
        tr3_to_2=1,
        tr3_steps_2=1,
        tr3_mode_3=1,
        tr3_from_3=1,
        tr3_to_3=1,
        tr3_steps_3=1,
        tr3_mode_4=1,
        tr3_from_4=1,
        tr3_to_4=1,
        tr3_steps_4=1,
        tr3_mode_5=1,
        tr3_from_5=1,
        tr3_to_5=1,
        tr3_steps_5=1,
        tr4_mode_1=1,
        tr4_from_1=1,
        tr4_to_1=1,
        tr4_steps_1=1,
        tr4_mode_2=1,
        tr4_from_2=1,
        tr4_to_2=1,
        tr4_steps_2=1,
        tr4_mode_3=1,
        tr4_from_3=1,
        tr4_to_3=1,
        tr4_steps_3=1,
        tr4_mode_4=1,
        tr4_from_4=1,
        tr4_to_4=1,
        tr4_steps_4=1,
        tr4_mode_5=1,
        tr4_from_5=1,
        tr4_to_5=1,
        tr4_steps_5=1,
        tr5_mode_1=1,
        tr5_from_1=1,
        tr5_to_1=1,
        tr5_steps_1=1,
        tr5_mode_2=1,
        tr5_from_2=1,
        tr5_to_2=1,
        tr5_steps_2=1,
        tr5_mode_3=1,
        tr5_from_3=1,
        tr5_to_3=1,
        tr5_steps_3=1,
        tr5_mode_4=1,
        tr5_from_4=1,
        tr5_to_4=1,
        tr5_steps_4=1,
        tr5_mode_5=1,
        tr5_from_5=1,
        tr5_to_5=1,
        tr5_steps_5=1,
        tr6_mode_1=1,
        tr6_from_1=1,
        tr6_to_1=1,
        tr6_steps_1=1,
        tr6_mode_2=1,
        tr6_from_2=1,
        tr6_to_2=1,
        tr6_steps_2=1,
        tr6_mode_3=1,
        tr6_from_3=1,
        tr6_to_3=1,
        tr6_steps_3=1,
        tr6_mode_4=1,
        tr6_from_4=1,
        tr6_to_4=1,
        tr6_steps_4=1,
        tr6_mode_5=1,
        tr6_from_5=1,
        tr6_to_5=1,
        tr6_steps_5=1,
    )

    set_mock_value(
        dae.tcb_settings._raw_tcb_settings, compress_and_hex(original_tcb_settings).decode()
    )

    with patch("ibex_bluesky_core.plan_stubs._time_channels_wrapper.ensure_connected"):
        RE(with_time_channels(bps.null(), dae=dae, new_tcb_settings=modified_settings))

    mock_set_calls = get_mock_put(dae.tcb_settings._raw_tcb_settings).call_args_list

    # Note for these two assertions that you can't compare XML directly as order isn't guaranteed,
    # so convert to the dataclass instead.

    # assert that modified settings are set
    assert _convert_xml_to_tcb_settings(modified_raw_tcb_settings) == _convert_xml_to_tcb_settings(
        dehex_and_decompress(mock_set_calls[0].args[0]).decode()
    )

    # assert that the original settings are restored
    assert _convert_xml_to_tcb_settings(original_tcb_settings) == _convert_xml_to_tcb_settings(
        dehex_and_decompress(mock_set_calls[1].args[0]).decode()
    )


def test_dae_table_wrapper(dae: Dae, RE: RunEngine):
    modified_settings = DaeSettingsData(
        wiring_filepath="C:\\somefile.dat",
        spectra_filepath="C:\\anotherfile.dat",
        detector_filepath="C:\\anotherfile123.dat",
    )

    original_settings = dae_settings_template.format(
        wiring_table="C:\\originalfile.dat",
        detector_table="C:\\anotheroriginalfile.dat",
        spectra_table="C:\\originalspectrafile.dat",
        mon_spec=1,
        from_=1,
        to=1,
        timing_src=1,
        smp_veto=1,
        ts2_veto=1,
        hz50_veto=1,
        veto_0=1,
        veto_1=1,
        veto_2=1,
        veto_3=1,
        fermi_veto=1,
        fc_delay=1,
        fc_width=1,
        muon_ms_mode=1,
        muon_cherenkov_pulse=1,
        veto_0_name="test",
        veto_1_name="test1",
    )

    modified_settings_xml = dae_settings_template.format(
        wiring_table=modified_settings.wiring_filepath,
        detector_table=modified_settings.detector_filepath,
        spectra_table=modified_settings.spectra_filepath,
        mon_spec=1,
        from_=1,
        to=1,
        timing_src=1,
        smp_veto=1,
        ts2_veto=1,
        hz50_veto=1,
        veto_0=1,
        veto_1=1,
        veto_2=1,
        veto_3=1,
        fermi_veto=1,
        fc_delay=1,
        fc_width=1,
        muon_ms_mode=1,
        muon_cherenkov_pulse=1,
        veto_0_name="test",
        veto_1_name="test1",
    )

    set_mock_value(dae.dae_settings._raw_dae_settings, original_settings)

    with patch("ibex_bluesky_core.plan_stubs._dae_table_wrapper.ensure_connected"):
        RE(with_dae_tables(bps.null(), dae=dae, new_settings=modified_settings))

    mock_set_calls = get_mock_put(dae.dae_settings._raw_dae_settings).call_args_list

    assert ET.canonicalize(modified_settings_xml) == ET.canonicalize(mock_set_calls[0].args[0])
    assert ET.canonicalize(original_settings) == ET.canonicalize(mock_set_calls[1].args[0])

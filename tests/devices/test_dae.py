# pyright: reportMissingParameterType=false
from enum import Enum
from unittest.mock import AsyncMock
from xml.etree import ElementTree as ET

import bluesky.plan_stubs as bps
import numpy as np
import pytest
import scipp as sc
import scipp.testing
from bluesky.run_engine import RunEngine
from ophyd_async.core import get_mock_put, set_mock_value

from ibex_bluesky_core.devices import compress_and_hex, dehex_and_decompress
from ibex_bluesky_core.devices.dae.dae import Dae, RunstateEnum
from ibex_bluesky_core.devices.dae.dae_period_settings import (
    DaePeriodSettings,
    DaePeriodSettingsData,
    PeriodSource,
    PeriodType,
    SinglePeriodSettings,
)
from ibex_bluesky_core.devices.dae.dae_settings import (
    DaeSettings,
    DaeSettingsData,
    TimingSource,
)
from ibex_bluesky_core.devices.dae.dae_spectra import VARIANCE_ADDITION, DaeSpectra
from ibex_bluesky_core.devices.dae.dae_tcb_settings import (
    CalculationMethod,
    DaeTCBSettings,
    DaeTCBSettingsData,
    TimeRegime,
    TimeRegimeMode,
    TimeRegimeRow,
    TimeUnit,
)
from src.ibex_bluesky_core.devices.dae import convert_xml_to_names_and_values, set_value_in_dae_xml
from src.ibex_bluesky_core.devices.dae.dae_controls import BeginRunExBits
from src.ibex_bluesky_core.devices.dae.dae_period_settings import _convert_period_settings_to_xml
from src.ibex_bluesky_core.devices.dae.dae_tcb_settings import _convert_tcb_settings_to_xml
from tests.conftest import MOCK_PREFIX
from tests.devices.dae_testing_data import (
    dae_settings_template,
    initial_dae_settings,
    initial_period_settings,
    initial_tcb_settings,
    period_settings_template,
    tcb_settings_template,
)


@pytest.fixture
async def dae() -> Dae:
    dae = Dae("UNITTEST:MOCK:")
    await dae.connect(mock=True)
    return dae


@pytest.fixture
async def spectrum() -> DaeSpectra:
    spectrum = DaeSpectra(dae_prefix="UNITTEST:MOCK:", spectra=1, period=1)
    await spectrum.connect(mock=True)
    return spectrum


def test_dae_naming(dae: Dae):
    assert dae.name == "DAE"
    assert dae.good_uah.name == "DAE-good_uah"


def test_dae_runstate_string_repr(dae: Dae):
    expected = "PROCESSING"
    assert str(RunstateEnum.PROCESSING) == expected


def test_explicit_dae_naming():
    dae_explicitly_named = Dae("UNITTEST:MOCK:", name="my_special_dae")
    assert dae_explicitly_named.name == "my_special_dae"
    assert dae_explicitly_named.good_uah.name == "my_special_dae-good_uah"


def test_dae_monitors_correct_pvs(dae: Dae):
    assert dae.good_uah.source.endswith("UNITTEST:MOCK:DAE:GOODUAH")
    assert dae.controls.begin_run.source.endswith("UNITTEST:MOCK:DAE:BEGINRUN")
    assert dae.controls.end_run.source.endswith("UNITTEST:MOCK:DAE:ENDRUN")


async def test_dae_descriptor_contains_same_keys_as_reading(dae: Dae):
    reading = await dae.read()
    descriptor = await dae.describe()

    assert reading.keys() == descriptor.keys()


async def test_begin_run_sets_begin_run_ex(dae: Dae):
    get_mock_put(dae.controls.begin_run_ex._raw_begin_run_ex).assert_not_called()
    await dae.controls.begin_run_ex.set(BeginRunExBits.NONE)
    assert get_mock_put(dae.controls.begin_run_ex._raw_begin_run_ex).call_args.args == (0,)


async def test_begin_run_ex_with_options_sets_begin_run_ex_correctly(dae: Dae):
    get_mock_put(dae.controls.begin_run_ex._raw_begin_run_ex).assert_not_called()
    await dae.controls.begin_run_ex.set(
        BeginRunExBits.NONE | BeginRunExBits.BEGIN_PAUSED | BeginRunExBits.BEGIN_DELAYED
    )
    get_mock_put(dae.controls.begin_run_ex._raw_begin_run_ex).assert_called_once()
    assert get_mock_put(dae.controls.begin_run_ex._raw_begin_run_ex).call_args.args == (3,)


INITIAL_XML = """
    <element>
        <child>
            <Name>{name}</Name>
            <Val>{initial_val}</Val>
        </child>
    </element>
    """


def test_set_value_in_xml_sets_a_value():
    name = "test"
    initial_val = "123"

    root = ET.fromstring(INITIAL_XML.format(name=name, initial_val=initial_val))
    value_to_set = "234"
    set_value_in_dae_xml(root.findall(".//child"), name, value_to_set)

    assert root[0][1].text == value_to_set


def test_set_value_with_enum_in_xml_sets_a_value():
    name = "test"
    initial_val = "456"

    class SomeEnum(Enum):
        TEST = "789"

    root = ET.fromstring(INITIAL_XML.format(name=name, initial_val=initial_val))
    value_to_set = SomeEnum.TEST
    set_value_in_dae_xml(root.findall(".//child"), name, value_to_set)

    assert root[0][1].text == value_to_set.value


def test_set_value_with_none_in_xml_doesnt_set_a_value():
    name = "test"
    initial_val = "456"

    root = ET.fromstring(INITIAL_XML.format(name=name, initial_val=initial_val))
    set_value_in_dae_xml(root.findall(".//child"), name, None)

    assert root[0][1].text == initial_val


def test_set_value_with_no_valid_children_in_xml_doesnt_set_a_value():
    name = "test"
    initial_val = "456"

    root = ET.fromstring(INITIAL_XML.format(name=name, initial_val=initial_val))
    set_value_in_dae_xml(root.findall(".//child"), name + "thisisnowinvalid", "789")

    assert root[0][1].text == initial_val


def test_get_names_and_values_from_xml():
    name = "test"
    initial_val = "456"
    test_xml = f"""
        <element>
            <child>
                <Name>Cluster</Name>
                <Val>2</Val>
            </child>
            <child>
                <Name>{name}</Name>
                <Val>{initial_val}</Val>
            </child>
        </element>
        """
    root = ET.fromstring(test_xml)
    ret = convert_xml_to_names_and_values(root)
    assert ret[name] == initial_val


def test_get_names_and_values_without_name_does_not_get_parsed():
    test_xml = """
        <Cluster>
            <Name>Cluster</Name>
            <child>
                <Name/>
                <Val/>
            </child>
        </Cluster>
        """
    root = ET.fromstring(test_xml)
    ret = convert_xml_to_names_and_values(root)
    assert not ret


def test_get_names_and_values_without_value_does_not_get_parsed():
    test_xml = """
        <Cluster>
        <Name>Some cluster name</Name>
            <child>
                <Name>test</Name>
                <Val/>
            </child>
        </Cluster>
        """
    root = ET.fromstring(test_xml)
    ret = convert_xml_to_names_and_values(root)
    assert ret == {"test": None}


async def test_dae_settings_get_parsed_correctly():
    expected_50hz_veto = True
    expected_ts2_veto = False
    expected_veto_0 = True
    expected_veto_1 = True
    expected_veto_2 = False
    expected_veto_3 = False
    expected_smp_veto = True
    expected_fc_veto = True
    expected_veto_0_name = "veto 0"
    expected_veto_1_name = "veto 1"
    expected_veto_2_name = None
    expected_veto_3_name = None
    expected_muon_ms_mode = False
    expected_muon_ck_pulse = 3
    expected_fc_delay = 1
    expected_fc_width = 2
    expected_timing_source = TimingSource.ISIS
    expected_from = 0
    expected_to = 1000
    expected_mon_spec = 555
    expected_wiring_table = "C:\\somefile.dat"
    expected_spectra_table = "C:\\anotherfile.dat"
    expected_detector_table = "C:\\anotherfile123.dat"
    data = DaeSettingsData(
        wiring_filepath=expected_wiring_table,
        detector_filepath=expected_detector_table,
        spectra_filepath=expected_spectra_table,
        mon_spect=expected_mon_spec,
        mon_from=expected_from,
        mon_to=expected_to,
        timing_source=expected_timing_source,
        smp_veto=expected_smp_veto,
        ts2_veto=expected_ts2_veto,
        hz50_veto=expected_50hz_veto,
        ext0_veto=expected_veto_0,
        ext1_veto=expected_veto_1,
        ext2_veto=expected_veto_2,
        ext3_veto=expected_veto_3,
        fermi_veto=expected_fc_veto,
        fermi_delay=expected_fc_delay,
        fermi_width=expected_fc_width,
        muon_ms_mode=expected_muon_ms_mode,
        muon_cherenkov_pulse=expected_muon_ck_pulse,
        veto_0_name=expected_veto_0_name,
        veto_1_name=expected_veto_1_name,
        veto_2_name=expected_veto_2_name,
        veto_3_name=expected_veto_3_name,
    )

    daesettings = DaeSettings(MOCK_PREFIX)
    await daesettings._raw_dae_settings.connect(mock=True)
    await daesettings._raw_dae_settings.set(initial_dae_settings)

    xml_filled_in = dae_settings_template.format(
        wiring_table=expected_wiring_table,
        detector_table=expected_detector_table,
        spectra_table=expected_spectra_table,
        mon_spec=expected_mon_spec,
        from_=expected_from,
        to=expected_to,
        timing_src=expected_timing_source.value,
        smp_veto=int(expected_smp_veto),
        ts2_veto=int(expected_ts2_veto),
        hz50_veto=int(expected_50hz_veto),
        veto_0=int(expected_veto_0),
        veto_1=int(expected_veto_1),
        veto_2=int(expected_veto_2),
        veto_3=int(expected_veto_3),
        fermi_veto=int(expected_fc_veto),
        fc_delay=expected_fc_delay,
        fc_width=expected_fc_width,
        muon_ms_mode=int(expected_muon_ms_mode),
        muon_cherenkov_pulse=expected_muon_ck_pulse,
        veto_0_name=expected_veto_0_name,
        veto_1_name=expected_veto_1_name,
    )
    await daesettings.set(data)
    location = await daesettings.locate()
    assert location == {"setpoint": data, "readback": data}
    xml = await daesettings._raw_dae_settings.get_value()
    assert ET.canonicalize(xml) == ET.canonicalize(xml_filled_in)


async def test_period_settings_get_parsed_correctly():
    expected_setup_source = PeriodSource.FILE
    expected_period_type = PeriodType.SOFTWARE
    expected_periods_file = "C:\\someperiodfile.txt"
    expected_soft_periods_num = 42
    expected_hardware_period_sequences = 52
    expected_output_delay = 123
    expected_type_1 = 0
    expected_frames_1 = 1
    expected_output_1 = 2
    expected_type_2 = 0
    expected_frames_2 = 1
    expected_output_2 = 2
    expected_type_3 = 1
    expected_frames_3 = 2
    expected_output_3 = 3
    expected_type_4 = 2
    expected_frames_4 = 3
    expected_output_4 = 4
    expected_type_5 = 0
    expected_frames_5 = 1
    expected_output_5 = 2
    expected_type_6 = 1
    expected_frames_6 = 1
    expected_output_6 = 2
    expected_type_7 = 1
    expected_frames_7 = 4
    expected_output_7 = 2
    expected_type_8 = 2
    expected_frames_8 = 2
    expected_output_8 = 2

    periods_settings = [
        SinglePeriodSettings(
            type=expected_type_1, frames=expected_frames_1, output=expected_output_1
        ),
        SinglePeriodSettings(
            type=expected_type_2, frames=expected_frames_2, output=expected_output_2
        ),
        SinglePeriodSettings(
            type=expected_type_3, frames=expected_frames_3, output=expected_output_3
        ),
        SinglePeriodSettings(
            type=expected_type_4, frames=expected_frames_4, output=expected_output_4
        ),
        SinglePeriodSettings(
            type=expected_type_5, frames=expected_frames_5, output=expected_output_5
        ),
        SinglePeriodSettings(
            type=expected_type_6, frames=expected_frames_6, output=expected_output_6
        ),
        SinglePeriodSettings(
            type=expected_type_7, frames=expected_frames_7, output=expected_output_7
        ),
        SinglePeriodSettings(
            type=expected_type_8, frames=expected_frames_8, output=expected_output_8
        ),
    ]

    data = DaePeriodSettingsData(
        periods_soft_num=expected_soft_periods_num,
        periods_type=expected_period_type,
        periods_src=expected_setup_source,
        periods_file=expected_periods_file,
        periods_seq=expected_hardware_period_sequences,
        periods_delay=expected_output_delay,
        periods_settings=periods_settings,
    )
    xml_filled_in = period_settings_template.format(
        period_src=expected_setup_source.value,
        period_type=expected_period_type.value,
        period_file=expected_periods_file,
        num_soft_periods=expected_soft_periods_num,
        period_seq=expected_hardware_period_sequences,
        period_delay=expected_output_delay,
        type_1=expected_type_1,
        frames_1=expected_frames_1,
        output_1=expected_output_1,
        type_2=expected_type_2,
        frames_2=expected_frames_2,
        output_2=expected_output_2,
        type_3=expected_type_3,
        frames_3=expected_frames_3,
        output_3=expected_output_3,
        type_4=expected_type_4,
        frames_4=expected_frames_4,
        output_4=expected_output_4,
        type_5=expected_type_5,
        frames_5=expected_frames_5,
        output_5=expected_output_5,
        type_6=expected_type_6,
        frames_6=expected_frames_6,
        output_6=expected_output_6,
        type_7=expected_type_7,
        frames_7=expected_frames_7,
        output_7=expected_output_7,
        type_8=expected_type_8,
        frames_8=expected_frames_8,
        output_8=expected_output_8,
    )
    periodsettings = DaePeriodSettings(MOCK_PREFIX)
    await periodsettings._raw_period_settings.connect(mock=True)
    await periodsettings._raw_period_settings.set(initial_period_settings)
    await periodsettings.set(data)
    location = await periodsettings.locate()
    assert location == {"setpoint": data, "readback": data}
    xml = await periodsettings._raw_period_settings.get_value()
    assert ET.canonicalize(xml) == ET.canonicalize(xml_filled_in)


async def test_tcb_settings_get_parsed_correctly():
    expected_tcb_file = "C:\\tcb.dat"
    expected_calc_method = CalculationMethod.SPECIFY_PARAMETERS
    expected_time_unit = TimeUnit.MICROSECONDS

    expected_tr1_from_1 = 0
    expected_tr1_to_1 = 10
    expected_tr1_steps_1 = 1
    expected_tr1_mode_1 = TimeRegimeMode.BLANK

    expected_tr1_from_2 = 11
    expected_tr1_to_2 = 20
    expected_tr1_steps_2 = 2
    expected_tr1_mode_2 = TimeRegimeMode.DT

    expected_tr1_from_3 = 21
    expected_tr1_to_3 = 30
    expected_tr1_steps_3 = 3
    expected_tr1_mode_3 = TimeRegimeMode.DTDIVT
    expected_tr1_from_4 = 31
    expected_tr1_to_4 = 40
    expected_tr1_steps_4 = 4
    expected_tr1_mode_4 = TimeRegimeMode.DTDIVT2

    expected_tr1_from_5 = 41
    expected_tr1_to_5 = 50
    expected_tr1_steps_5 = 5
    expected_tr1_mode_5 = TimeRegimeMode.SHIFTED

    expected_tr2_from_1 = 51
    expected_tr2_to_1 = 60
    expected_tr2_steps_1 = 1
    expected_tr2_mode_1 = TimeRegimeMode.BLANK

    expected_tr2_from_2 = 61
    expected_tr2_to_2 = 70
    expected_tr2_steps_2 = 2
    expected_tr2_mode_2 = TimeRegimeMode.DT

    expected_tr2_from_3 = 71
    expected_tr2_to_3 = 80
    expected_tr2_steps_3 = 3
    expected_tr2_mode_3 = TimeRegimeMode.DTDIVT

    expected_tr2_from_4 = 81
    expected_tr2_to_4 = 90
    expected_tr2_steps_4 = 4
    expected_tr2_mode_4 = TimeRegimeMode.DTDIVT2

    expected_tr2_from_5 = 91
    expected_tr2_to_5 = 100
    expected_tr2_steps_5 = 5
    expected_tr2_mode_5 = TimeRegimeMode.SHIFTED

    expected_tr3_from_1 = 101
    expected_tr3_to_1 = 110
    expected_tr3_steps_1 = 1
    expected_tr3_mode_1 = TimeRegimeMode.BLANK

    expected_tr3_from_2 = 111
    expected_tr3_to_2 = 120
    expected_tr3_steps_2 = 2
    expected_tr3_mode_2 = TimeRegimeMode.DT

    expected_tr3_from_3 = 121
    expected_tr3_to_3 = 130
    expected_tr3_steps_3 = 3
    expected_tr3_mode_3 = TimeRegimeMode.DTDIVT

    expected_tr3_from_4 = 131
    expected_tr3_to_4 = 140
    expected_tr3_steps_4 = 4
    expected_tr3_mode_4 = TimeRegimeMode.DTDIVT2

    expected_tr3_from_5 = 141
    expected_tr3_to_5 = 150
    expected_tr3_steps_5 = 5
    expected_tr3_mode_5 = TimeRegimeMode.SHIFTED

    expected_tr4_from_1 = 151
    expected_tr4_to_1 = 160
    expected_tr4_steps_1 = 1
    expected_tr4_mode_1 = TimeRegimeMode.BLANK

    expected_tr4_from_2 = 161
    expected_tr4_to_2 = 170
    expected_tr4_steps_2 = 2
    expected_tr4_mode_2 = TimeRegimeMode.DT

    expected_tr4_from_3 = 171
    expected_tr4_to_3 = 180
    expected_tr4_steps_3 = 3
    expected_tr4_mode_3 = TimeRegimeMode.DTDIVT

    expected_tr4_from_4 = 181
    expected_tr4_to_4 = 190
    expected_tr4_steps_4 = 4
    expected_tr4_mode_4 = TimeRegimeMode.DTDIVT2

    expected_tr4_from_5 = 191
    expected_tr4_to_5 = 200
    expected_tr4_steps_5 = 5
    expected_tr4_mode_5 = TimeRegimeMode.SHIFTED

    expected_tr5_from_1 = 201
    expected_tr5_to_1 = 210
    expected_tr5_steps_1 = 1
    expected_tr5_mode_1 = TimeRegimeMode.BLANK

    expected_tr5_from_2 = 211
    expected_tr5_to_2 = 220
    expected_tr5_steps_2 = 2
    expected_tr5_mode_2 = TimeRegimeMode.DT

    expected_tr5_from_3 = 221
    expected_tr5_to_3 = 230
    expected_tr5_steps_3 = 3
    expected_tr5_mode_3 = TimeRegimeMode.DTDIVT

    expected_tr5_from_4 = 231
    expected_tr5_to_4 = 240
    expected_tr5_steps_4 = 4
    expected_tr5_mode_4 = TimeRegimeMode.DTDIVT2

    expected_tr5_from_5 = 241
    expected_tr5_to_5 = 250
    expected_tr5_steps_5 = 5
    expected_tr5_mode_5 = TimeRegimeMode.SHIFTED

    expected_tr6_from_1 = 251
    expected_tr6_to_1 = 260
    expected_tr6_steps_1 = 1
    expected_tr6_mode_1 = TimeRegimeMode.BLANK

    expected_tr6_from_2 = 261
    expected_tr6_to_2 = 270
    expected_tr6_steps_2 = 2
    expected_tr6_mode_2 = TimeRegimeMode.DT

    expected_tr6_from_3 = 271
    expected_tr6_to_3 = 280
    expected_tr6_steps_3 = 3
    expected_tr6_mode_3 = TimeRegimeMode.DTDIVT

    expected_tr6_from_4 = 281
    expected_tr6_to_4 = 290
    expected_tr6_steps_4 = 4
    expected_tr6_mode_4 = TimeRegimeMode.DTDIVT2

    expected_tr6_from_5 = 291
    expected_tr6_to_5 = 300
    expected_tr6_steps_5 = 5
    expected_tr6_mode_5 = TimeRegimeMode.SHIFTED

    tcb_tables = {
        1: TimeRegime(
            {
                1: TimeRegimeRow(
                    from_=expected_tr1_from_1,
                    to=expected_tr1_to_1,
                    steps=expected_tr1_steps_1,
                    mode=expected_tr1_mode_1,
                ),
                2: TimeRegimeRow(
                    from_=expected_tr1_from_2,
                    to=expected_tr1_to_2,
                    steps=expected_tr1_steps_2,
                    mode=expected_tr1_mode_2,
                ),
                3: TimeRegimeRow(
                    from_=expected_tr1_from_3,
                    to=expected_tr1_to_3,
                    steps=expected_tr1_steps_3,
                    mode=expected_tr1_mode_3,
                ),
                4: TimeRegimeRow(
                    from_=expected_tr1_from_4,
                    to=expected_tr1_to_4,
                    steps=expected_tr1_steps_4,
                    mode=expected_tr1_mode_4,
                ),
                5: TimeRegimeRow(
                    from_=expected_tr1_from_5,
                    to=expected_tr1_to_5,
                    steps=expected_tr1_steps_5,
                    mode=expected_tr1_mode_5,
                ),
            }
        ),
        2: TimeRegime(
            {
                1: TimeRegimeRow(
                    from_=expected_tr2_from_1,
                    to=expected_tr2_to_1,
                    steps=expected_tr2_steps_1,
                    mode=expected_tr2_mode_1,
                ),
                2: TimeRegimeRow(
                    from_=expected_tr2_from_2,
                    to=expected_tr2_to_2,
                    steps=expected_tr2_steps_2,
                    mode=expected_tr2_mode_2,
                ),
                3: TimeRegimeRow(
                    from_=expected_tr2_from_3,
                    to=expected_tr2_to_3,
                    steps=expected_tr2_steps_3,
                    mode=expected_tr2_mode_3,
                ),
                4: TimeRegimeRow(
                    from_=expected_tr2_from_4,
                    to=expected_tr2_to_4,
                    steps=expected_tr2_steps_4,
                    mode=expected_tr2_mode_4,
                ),
                5: TimeRegimeRow(
                    from_=expected_tr2_from_5,
                    to=expected_tr2_to_5,
                    steps=expected_tr2_steps_5,
                    mode=expected_tr2_mode_5,
                ),
            }
        ),
        3: TimeRegime(
            {
                1: TimeRegimeRow(
                    from_=expected_tr3_from_1,
                    to=expected_tr3_to_1,
                    steps=expected_tr3_steps_1,
                    mode=expected_tr3_mode_1,
                ),
                2: TimeRegimeRow(
                    from_=expected_tr3_from_2,
                    to=expected_tr3_to_2,
                    steps=expected_tr3_steps_2,
                    mode=expected_tr3_mode_2,
                ),
                3: TimeRegimeRow(
                    from_=expected_tr3_from_3,
                    to=expected_tr3_to_3,
                    steps=expected_tr3_steps_3,
                    mode=expected_tr3_mode_3,
                ),
                4: TimeRegimeRow(
                    from_=expected_tr3_from_4,
                    to=expected_tr3_to_4,
                    steps=expected_tr3_steps_4,
                    mode=expected_tr3_mode_4,
                ),
                5: TimeRegimeRow(
                    from_=expected_tr3_from_5,
                    to=expected_tr3_to_5,
                    steps=expected_tr3_steps_5,
                    mode=expected_tr3_mode_5,
                ),
            }
        ),
        4: TimeRegime(
            {
                1: TimeRegimeRow(
                    from_=expected_tr4_from_1,
                    to=expected_tr4_to_1,
                    steps=expected_tr4_steps_1,
                    mode=expected_tr4_mode_1,
                ),
                2: TimeRegimeRow(
                    from_=expected_tr4_from_2,
                    to=expected_tr4_to_2,
                    steps=expected_tr4_steps_2,
                    mode=expected_tr4_mode_2,
                ),
                3: TimeRegimeRow(
                    from_=expected_tr4_from_3,
                    to=expected_tr4_to_3,
                    steps=expected_tr4_steps_3,
                    mode=expected_tr4_mode_3,
                ),
                4: TimeRegimeRow(
                    from_=expected_tr4_from_4,
                    to=expected_tr4_to_4,
                    steps=expected_tr4_steps_4,
                    mode=expected_tr4_mode_4,
                ),
                5: TimeRegimeRow(
                    from_=expected_tr4_from_5,
                    to=expected_tr4_to_5,
                    steps=expected_tr4_steps_5,
                    mode=expected_tr4_mode_5,
                ),
            }
        ),
        5: TimeRegime(
            {
                1: TimeRegimeRow(
                    from_=expected_tr5_from_1,
                    to=expected_tr5_to_1,
                    steps=expected_tr5_steps_1,
                    mode=expected_tr5_mode_1,
                ),
                2: TimeRegimeRow(
                    from_=expected_tr5_from_2,
                    to=expected_tr5_to_2,
                    steps=expected_tr5_steps_2,
                    mode=expected_tr5_mode_2,
                ),
                3: TimeRegimeRow(
                    from_=expected_tr5_from_3,
                    to=expected_tr5_to_3,
                    steps=expected_tr5_steps_3,
                    mode=expected_tr5_mode_3,
                ),
                4: TimeRegimeRow(
                    from_=expected_tr5_from_4,
                    to=expected_tr5_to_4,
                    steps=expected_tr5_steps_4,
                    mode=expected_tr5_mode_4,
                ),
                5: TimeRegimeRow(
                    from_=expected_tr5_from_5,
                    to=expected_tr5_to_5,
                    steps=expected_tr5_steps_5,
                    mode=expected_tr5_mode_5,
                ),
            }
        ),
        6: TimeRegime(
            {
                1: TimeRegimeRow(
                    from_=expected_tr6_from_1,
                    to=expected_tr6_to_1,
                    steps=expected_tr6_steps_1,
                    mode=expected_tr6_mode_1,
                ),
                2: TimeRegimeRow(
                    from_=expected_tr6_from_2,
                    to=expected_tr6_to_2,
                    steps=expected_tr6_steps_2,
                    mode=expected_tr6_mode_2,
                ),
                3: TimeRegimeRow(
                    from_=expected_tr6_from_3,
                    to=expected_tr6_to_3,
                    steps=expected_tr6_steps_3,
                    mode=expected_tr6_mode_3,
                ),
                4: TimeRegimeRow(
                    from_=expected_tr6_from_4,
                    to=expected_tr6_to_4,
                    steps=expected_tr6_steps_4,
                    mode=expected_tr6_mode_4,
                ),
                5: TimeRegimeRow(
                    from_=expected_tr6_from_5,
                    to=expected_tr6_to_5,
                    steps=expected_tr6_steps_5,
                    mode=expected_tr6_mode_5,
                ),
            }
        ),
    }

    data = DaeTCBSettingsData(
        tcb_file=expected_tcb_file,
        time_unit=expected_time_unit,
        tcb_tables=tcb_tables,
        tcb_calculation_method=expected_calc_method,
    )

    tcbsettings = DaeTCBSettings(MOCK_PREFIX)
    await tcbsettings._raw_tcb_settings.connect(mock=True)
    await tcbsettings._raw_tcb_settings.set(compress_and_hex(initial_tcb_settings).decode())

    await tcbsettings.set(data)
    location = await tcbsettings.locate()
    assert location == {"setpoint": data, "readback": data}

    xml_filled_in = tcb_settings_template.format(
        tcb_file=expected_tcb_file,
        time_units=expected_time_unit.value,
        calc_method=expected_calc_method.value,
        tr1_mode_1=expected_tr1_mode_1.value,
        tr1_from_1=expected_tr1_from_1,
        tr1_to_1=expected_tr1_to_1,
        tr1_steps_1=expected_tr1_steps_1,
        tr1_mode_2=expected_tr1_mode_2.value,
        tr1_from_2=expected_tr1_from_2,
        tr1_to_2=expected_tr1_to_2,
        tr1_steps_2=expected_tr1_steps_2,
        tr1_mode_3=expected_tr1_mode_3.value,
        tr1_from_3=expected_tr1_from_3,
        tr1_to_3=expected_tr1_to_3,
        tr1_steps_3=expected_tr1_steps_3,
        tr1_mode_4=expected_tr1_mode_4.value,
        tr1_from_4=expected_tr1_from_4,
        tr1_to_4=expected_tr1_to_4,
        tr1_steps_4=expected_tr1_steps_4,
        tr1_mode_5=expected_tr1_mode_5.value,
        tr1_from_5=expected_tr1_from_5,
        tr1_to_5=expected_tr1_to_5,
        tr1_steps_5=expected_tr1_steps_5,
        tr2_mode_1=expected_tr2_mode_1.value,
        tr2_from_1=expected_tr2_from_1,
        tr2_to_1=expected_tr2_to_1,
        tr2_steps_1=expected_tr2_steps_1,
        tr2_mode_2=expected_tr2_mode_2.value,
        tr2_from_2=expected_tr2_from_2,
        tr2_to_2=expected_tr2_to_2,
        tr2_steps_2=expected_tr2_steps_2,
        tr2_mode_3=expected_tr2_mode_3.value,
        tr2_from_3=expected_tr2_from_3,
        tr2_to_3=expected_tr2_to_3,
        tr2_steps_3=expected_tr2_steps_3,
        tr2_mode_4=expected_tr2_mode_4.value,
        tr2_from_4=expected_tr2_from_4,
        tr2_to_4=expected_tr2_to_4,
        tr2_steps_4=expected_tr2_steps_4,
        tr2_mode_5=expected_tr2_mode_5.value,
        tr2_from_5=expected_tr2_from_5,
        tr2_to_5=expected_tr2_to_5,
        tr2_steps_5=expected_tr2_steps_5,
        tr3_mode_1=expected_tr3_mode_1.value,
        tr3_from_1=expected_tr3_from_1,
        tr3_to_1=expected_tr3_to_1,
        tr3_steps_1=expected_tr3_steps_1,
        tr3_mode_2=expected_tr3_mode_2.value,
        tr3_from_2=expected_tr3_from_2,
        tr3_to_2=expected_tr3_to_2,
        tr3_steps_2=expected_tr3_steps_2,
        tr3_mode_3=expected_tr3_mode_3.value,
        tr3_from_3=expected_tr3_from_3,
        tr3_to_3=expected_tr3_to_3,
        tr3_steps_3=expected_tr3_steps_3,
        tr3_mode_4=expected_tr3_mode_4.value,
        tr3_from_4=expected_tr3_from_4,
        tr3_to_4=expected_tr3_to_4,
        tr3_steps_4=expected_tr3_steps_4,
        tr3_mode_5=expected_tr3_mode_5.value,
        tr3_from_5=expected_tr3_from_5,
        tr3_to_5=expected_tr3_to_5,
        tr3_steps_5=expected_tr3_steps_5,
        tr4_mode_1=expected_tr4_mode_1.value,
        tr4_from_1=expected_tr4_from_1,
        tr4_to_1=expected_tr4_to_1,
        tr4_steps_1=expected_tr4_steps_1,
        tr4_mode_2=expected_tr4_mode_2.value,
        tr4_from_2=expected_tr4_from_2,
        tr4_to_2=expected_tr4_to_2,
        tr4_steps_2=expected_tr4_steps_2,
        tr4_mode_3=expected_tr4_mode_3.value,
        tr4_from_3=expected_tr4_from_3,
        tr4_to_3=expected_tr4_to_3,
        tr4_steps_3=expected_tr4_steps_3,
        tr4_mode_4=expected_tr4_mode_4.value,
        tr4_from_4=expected_tr4_from_4,
        tr4_to_4=expected_tr4_to_4,
        tr4_steps_4=expected_tr4_steps_4,
        tr4_mode_5=expected_tr4_mode_5.value,
        tr4_from_5=expected_tr4_from_5,
        tr4_to_5=expected_tr4_to_5,
        tr4_steps_5=expected_tr4_steps_5,
        tr5_mode_1=expected_tr5_mode_1.value,
        tr5_from_1=expected_tr5_from_1,
        tr5_to_1=expected_tr5_to_1,
        tr5_steps_1=expected_tr5_steps_1,
        tr5_mode_2=expected_tr5_mode_2.value,
        tr5_from_2=expected_tr5_from_2,
        tr5_to_2=expected_tr5_to_2,
        tr5_steps_2=expected_tr5_steps_2,
        tr5_mode_3=expected_tr5_mode_3.value,
        tr5_from_3=expected_tr5_from_3,
        tr5_to_3=expected_tr5_to_3,
        tr5_steps_3=expected_tr5_steps_3,
        tr5_mode_4=expected_tr5_mode_4.value,
        tr5_from_4=expected_tr5_from_4,
        tr5_to_4=expected_tr5_to_4,
        tr5_steps_4=expected_tr5_steps_4,
        tr5_mode_5=expected_tr5_mode_5.value,
        tr5_from_5=expected_tr5_from_5,
        tr5_to_5=expected_tr5_to_5,
        tr5_steps_5=expected_tr5_steps_5,
        tr6_mode_1=expected_tr6_mode_1.value,
        tr6_from_1=expected_tr6_from_1,
        tr6_to_1=expected_tr6_to_1,
        tr6_steps_1=expected_tr6_steps_1,
        tr6_mode_2=expected_tr6_mode_2.value,
        tr6_from_2=expected_tr6_from_2,
        tr6_to_2=expected_tr6_to_2,
        tr6_steps_2=expected_tr6_steps_2,
        tr6_mode_3=expected_tr6_mode_3.value,
        tr6_from_3=expected_tr6_from_3,
        tr6_to_3=expected_tr6_to_3,
        tr6_steps_3=expected_tr6_steps_3,
        tr6_mode_4=expected_tr6_mode_4.value,
        tr6_from_4=expected_tr6_from_4,
        tr6_to_4=expected_tr6_to_4,
        tr6_steps_4=expected_tr6_steps_4,
        tr6_mode_5=expected_tr6_mode_5.value,
        tr6_from_5=expected_tr6_from_5,
        tr6_to_5=expected_tr6_to_5,
        tr6_steps_5=expected_tr6_steps_5,
    )

    xml_hexed = await tcbsettings._raw_tcb_settings.get_value()
    xml = dehex_and_decompress(xml_hexed.encode()).decode()
    assert ET.canonicalize(xml) == ET.canonicalize(xml_filled_in)


def test_tcb_settings_does_not_set_anything_if_all_none_provided():
    data = DaeTCBSettingsData()
    output = _convert_tcb_settings_to_xml(initial_tcb_settings, data)
    assert ET.canonicalize(initial_tcb_settings) == ET.canonicalize(output)


def test_period_settings_does_not_set_anything_if_all_none_provided():
    data = DaePeriodSettingsData()
    output = _convert_period_settings_to_xml(initial_period_settings, data)
    assert ET.canonicalize(initial_period_settings) == ET.canonicalize(output)


def test_table_can_be_read_from_plan_using_run_engine(dae: Dae, RE: RunEngine):
    set_mock_value(dae.dae_settings._raw_dae_settings, initial_dae_settings)

    result = RE(bps.rd(dae.dae_settings))

    assert result.plan_result.wiring_filepath.endswith(  # type: ignore
        "NIMROD84modules+9monitors+LAB5Oct2012Wiring.dat"
    )


def test_empty_dae_settings_dataclass_does_not_change_any_settings(dae: Dae, RE: RunEngine):
    set_mock_value(dae.dae_settings._raw_dae_settings, initial_dae_settings)

    before: DaeSettingsData = RE(bps.rd(dae.dae_settings)).plan_result  # type: ignore
    RE(bps.mv(dae.dae_settings, DaeSettingsData()))
    after: DaeSettingsData = RE(bps.rd(dae.dae_settings)).plan_result  # type: ignore

    assert before == after
    assert after.wiring_filepath is not None
    assert after.wiring_filepath.endswith("NIMROD84modules+9monitors+LAB5Oct2012Wiring.dat")


async def test_read_spectra_correctly_sizes_arrays(spectrum: DaeSpectra):
    set_mock_value(spectrum.tof, np.zeros(dtype=np.float32, shape=(1000,)))
    set_mock_value(spectrum.tof_size, 100)
    set_mock_value(spectrum.counts, np.zeros(dtype=np.float32, shape=(2000,)))
    set_mock_value(spectrum.counts_size, 200)
    set_mock_value(spectrum.counts_per_time, np.zeros(dtype=np.float32, shape=(3000,)))
    set_mock_value(spectrum.counts_per_time_size, 300)
    set_mock_value(spectrum.tof_edges, np.zeros(dtype=np.float32, shape=(4000,)))
    set_mock_value(spectrum.tof_edges_size, 400)

    assert (await spectrum.read_tof()).shape == (100,)
    assert (await spectrum.read_counts()).shape == (200,)
    assert (await spectrum.read_counts_per_time()).shape == (300,)
    assert (await spectrum.read_tof_edges()).shape == (400,)


async def test_read_spectrum_dataarray(spectrum: DaeSpectra):
    set_mock_value(spectrum.counts, np.array([1000, 2000, 3000], dtype=np.float32))
    set_mock_value(spectrum.counts_size, 3)
    set_mock_value(spectrum.tof_edges, np.array([0, 1, 2, 3], dtype=np.float32))
    set_mock_value(spectrum.tof_edges_size, 4)

    spectrum.tof_edges.describe = AsyncMock(return_value={spectrum.tof_edges.name: {"units": "us"}})
    da = await spectrum.read_spectrum_dataarray()

    scipp.testing.assert_identical(
        da,
        sc.DataArray(
            data=sc.Variable(
                dims=["tof"],
                values=[1000, 2000, 3000],
                variances=[
                    1000 + VARIANCE_ADDITION,
                    2000 + VARIANCE_ADDITION,
                    3000 + VARIANCE_ADDITION,
                ],
                unit=sc.units.counts,
                dtype="float32",
            ),
            coords={
                "tof": sc.Variable(
                    dims=["tof"], values=[0, 1, 2, 3], dtype="float32", unit=sc.units.us
                )
            },
        ),
    )


async def test_if_tof_edges_doesnt_have_enough_points_then_read_spec_dataarray_gives_error(
    spectrum: DaeSpectra,
):
    set_mock_value(spectrum.counts, np.array([0]))
    set_mock_value(spectrum.counts_size, 1)
    set_mock_value(spectrum.tof_edges, np.array([0]))
    set_mock_value(spectrum.tof_edges_size, 1)

    with pytest.raises(ValueError, match="Time-of-flight edges must have size"):
        await spectrum.read_spectrum_dataarray()


async def test_if_tof_edges_has_no_units_then_read_spec_dataarray_gives_error(
    spectrum: DaeSpectra,
):
    set_mock_value(spectrum.counts, np.array([0]))
    set_mock_value(spectrum.counts_size, 1)
    set_mock_value(spectrum.tof_edges, np.array([0, 0]))
    set_mock_value(spectrum.tof_edges_size, 2)
    spectrum.tof_edges.describe = AsyncMock(return_value={spectrum.tof_edges.name: {"units": None}})

    with pytest.raises(ValueError, match="Could not determine engineering units"):
        await spectrum.read_spectrum_dataarray()


def test_dae_repr():
    assert repr(Dae(prefix="foo", name="bar")) == "Dae(name=bar, prefix=foo)"

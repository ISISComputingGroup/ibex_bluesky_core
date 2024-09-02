# pyright: reportMissingParameterType=false
from enum import Enum
from xml.etree import ElementTree as ET

import pytest
from ibex_bluesky_core.devices.dae.dae import Dae, RunstateEnum
from ophyd_async.core import get_mock_put

from ibex_bluesky_core.devices.dae.dae_period_settings import DaePeriodSettingsData, DaePeriodSettings
from ibex_bluesky_core.devices.dae.dae_settings import (
    DaeSettings,
    TimingSource,
    DaeSettingsData,
    convert_xml_to_dae_settings,
)
from ibex_bluesky_core.devices.dae.dae_tcb_settings import DaeTCBSettings, DaeTCBSettingsData
from src.ibex_bluesky_core.devices.dae import set_value_in_dae_xml, convert_xml_to_names_and_values
from src.ibex_bluesky_core.devices.dae.dae_controls import BeginRunExBits
from ophyd_async.core import get_mock_put, set_mock_value

MOCK_PREFIX = "UNITTEST:MOCK:"


@pytest.fixture
async def dae() -> Dae:
    dae = Dae("UNITTEST:MOCK:")
    await dae.connect(mock=True)
    return dae


def test_dae_naming(dae: Dae):
    assert dae.name == "DAE"
    assert dae.good_uah.name == "DAE-good_uah"


def test_dae_runstate_string_repr(dae: Dae):
    expected = "PROCESSING"
    dae.run_state = RunstateEnum(expected)
    assert str(dae.run_state) == expected


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


async def test_trigger_calls_triggers_begin_and_end(dae: Dae):
    get_mock_put(dae.controls.begin_run).assert_not_called()
    get_mock_put(dae.controls.end_run).assert_not_called()

    await dae.trigger()

    get_mock_put(dae.controls.begin_run).assert_called_once()
    get_mock_put(dae.controls.end_run).assert_called_once()


async def test_begin_run_sets_begin_run_ex(dae: Dae):
    get_mock_put(dae.controls.begin_run_ex.begin_run_ex).assert_not_called()
    await dae.controls.begin_run_ex.set(BeginRunExBits.NONE)
    get_mock_put(dae.controls.begin_run_ex.begin_run_ex).assert_called_once()


async def test_begin_run_ex_with_options_sets_begin_run_ex_correctly(dae: Dae):
    get_mock_put(dae.controls.begin_run_ex.begin_run_ex).assert_not_called()
    await dae.controls.begin_run_ex.set(
        BeginRunExBits.NONE + BeginRunExBits.BEGINIFPAUSED + BeginRunExBits.BEGINIFDELAYED
    )
    get_mock_put(dae.controls.begin_run_ex.begin_run_ex).assert_called_once()
    assert get_mock_put(dae.controls.begin_run_ex.begin_run_ex).call_args.args == (3,)


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
    test_xml = f"""
        <element>
            <child>
                <Name>Cluster</Name>
                <Val>2</Val>
            </child>
            <child>
                <Name/>
                <Val/>
            </child>
        </element>
        """
    root = ET.fromstring(test_xml)
    ret = convert_xml_to_names_and_values(root)
    assert not ret


def test_get_names_and_values_without_value_does_not_get_parsed():
    test_xml = f"""
        <element>
            <child>
                <Name>Cluster</Name>
                <Val>2</Val>
            </child>
            <child>
                <Name>test</Name>
                <Val/>
            </child>
        </element>
        """
    root = ET.fromstring(test_xml)
    ret = convert_xml_to_names_and_values(root)
    assert ret == {"test": None}


period_settings_template = """
<?xml version="1.0"?>
<Cluster>
  <Name>Hardware Periods</Name>
  <NumElts>38</NumElts>
  <EW>
    <Name>Period Setup Source</Name>
    <Choice>Use Parameters Below</Choice>
    <Choice>Read from file</Choice>
    <Val>{period_src}</Val>
  </EW>
  <EW>
    <Name>Period Type</Name>
    <Choice>Software (PC controlled)</Choice>
    <Choice>Hardware (DAE internal control)</Choice>
    <Choice>Hardware (External signal control)</Choice>
    <Val>{period_type}</Val>
  </EW>
  <String>
    <Name>Period File</Name>
    <Val>{period_file}</Val>
  </String>
  <I32>
    <Name>Number Of Software Periods</Name>
    <Val>{num_soft_periods}</Val>
  </I32>
  <DBL>
    <Name>Hardware Period Sequences</Name>
    <Val>{period_seq}</Val>
  </DBL>
  <DBL>
    <Name>Output Delay (us)</Name>
    <Val>{period_delay}</Val>
  </DBL>
  <EW>
    <Name>Type 1</Name>
    <Choice>UNUSED</Choice>
    <Choice>DAQ</Choice>
    <Choice>DWELL</Choice>
    <Val>{type_1}</Val>
  </EW>
  <I32>
    <Name>Frames 1</Name>
    <Val>{frames_1}</Val>
  </I32>
  <U16>
    <Name>Output 1</Name>
    <Val>{output_1}</Val>
  </U16>
  <String>
    <Name>Label 1</Name>
    <Val/>
  </String>
  <EW>
    <Name>Type 2</Name>
    <Choice>UNUSED</Choice>
    <Choice>DAQ</Choice>
    <Choice>DWELL</Choice>
    <Val>{type_2}</Val>
  </EW>
  <I32>
    <Name>Frames 2</Name>
    <Val>{frames_2}</Val>
  </I32>
  <U16>
    <Name>Output 2</Name>
    <Val>{output_2}</Val>
  </U16>
  <String>
    <Name>Label 2</Name>
    <Val/>
  </String>
  <EW>
    <Name>Type 3</Name>
    <Choice>UNUSED</Choice>
    <Choice>DAQ</Choice>
    <Choice>DWELL</Choice>
    <Val>{type_3}</Val>
  </EW>
  <I32>
    <Name>Frames 3</Name>
    <Val>{frames_3}</Val>
  </I32>
  <U16>
    <Name>Output 3</Name>
    <Val>{output_3}</Val>
  </U16>
  <String>
    <Name>Label 3</Name>
    <Val/>
  </String>
  <EW>
    <Name>Type 4</Name>
    <Choice>UNUSED</Choice>
    <Choice>DAQ</Choice>
    <Choice>DWELL</Choice>
    <Val>{type_4}</Val>
  </EW>
  <I32>
    <Name>Frames 4</Name>
    <Val>{frames_4}</Val>
  </I32>
  <U16>
    <Name>Output 4</Name>
    <Val>{output_4}</Val>
  </U16>
  <String>
    <Name>Label 4</Name>
    <Val/>
  </String>
  <EW>
    <Name>Type 5</Name>
    <Choice>UNUSED</Choice>
    <Choice>DAQ</Choice>
    <Choice>DWELL</Choice>
    <Val>{type_5}</Val>
  </EW>
  <I32>
    <Name>Frames 5</Name>
    <Val>{frames_5}</Val>
  </I32>
  <U16>
    <Name>Output 5</Name>
    <Val>{output_5}</Val>
  </U16>
  <String>
    <Name>Label 5</Name>
    <Val/>
  </String>
  <EW>
    <Name>Type 6</Name>
    <Choice>UNUSED</Choice>
    <Choice>DAQ</Choice>
    <Choice>DWELL</Choice>
    <Val>{type_6}</Val>
  </EW>
  <I32>
    <Name>Frames 6</Name>
    <Val>{frames_6}</Val>
  </I32>
  <U16>
    <Name>Output 6</Name>
    <Val>{output_6}</Val>
  </U16>
  <String>
    <Name>Label 6</Name>
    <Val/>
  </String>
  <EW>
    <Name>Type 7</Name>
    <Choice>UNUSED</Choice>
    <Choice>DAQ</Choice>
    <Choice>DWELL</Choice>
    <Val>{type_7}</Val>
  </EW>
  <I32>
    <Name>Frames 7</Name>
    <Val>{frames_7}</Val>
  </I32>
  <U16>
    <Name>Output 7</Name>
    <Val>{output_7}</Val>
  </U16>
  <String>
    <Name>Label 7</Name>
    <Val/>
  </String>
  <EW>
    <Name>Type 8</Name>
    <Choice>UNUSED</Choice>
    <Choice>DAQ</Choice>
    <Choice>DWELL</Choice>
    <Val>{type_8}</Val>
  </EW>
  <I32>
    <Name>Frames 8</Name>
    <Val>{frames_8}</Val>
  </I32>
  <U16>
    <Name>Output 8</Name>
    <Val>{output_8}</Val>
  </U16>
  <String>
    <Name>Label 8</Name>
    <Val/>
  </String>
</Cluster>
"""
initial_period_settings = """<?xml version="1.0"?>
<Cluster>
  <Name>Hardware Periods</Name>
  <NumElts>38</NumElts>
  <EW>
    <Name>Period Setup Source</Name>
    <Choice>Use Parameters Below</Choice>
    <Choice>Read from file</Choice>
    <Val>0</Val>
  </EW>
  <EW>
    <Name>Period Type</Name>
    <Choice>Software (PC controlled)</Choice>
    <Choice>Hardware (DAE internal control)</Choice>
    <Choice>Hardware (External signal control)</Choice>
    <Val>0</Val>
  </EW>
  <String>
    <Name>Period File</Name>
    <Val/>
  </String>
  <I32>
    <Name>Number Of Software Periods</Name>
    <Val>1</Val>
  </I32>
  <DBL>
    <Name>Hardware Period Sequences</Name>
    <Val>0</Val>
  </DBL>
  <DBL>
    <Name>Output Delay (us)</Name>
    <Val>0</Val>
  </DBL>
  <EW>
    <Name>Type 1</Name>
    <Choice>UNUSED</Choice>
    <Choice>DAQ</Choice>
    <Choice>DWELL</Choice>
    <Val>0</Val>
  </EW>
  <I32>
    <Name>Frames 1</Name>
    <Val>0</Val>
  </I32>
  <U16>
    <Name>Output 1</Name>
    <Val>0</Val>
  </U16>
  <String>
    <Name>Label 1</Name>
    <Val/>
  </String>
  <EW>
    <Name>Type 2</Name>
    <Choice>UNUSED</Choice>
    <Choice>DAQ</Choice>
    <Choice>DWELL</Choice>
    <Val>0</Val>
  </EW>
  <I32>
    <Name>Frames 2</Name>
    <Val>0</Val>
  </I32>
  <U16>
    <Name>Output 2</Name>
    <Val>0</Val>
  </U16>
  <String>
    <Name>Label 2</Name>
    <Val/>
  </String>
  <EW>
    <Name>Type 3</Name>
    <Choice>UNUSED</Choice>
    <Choice>DAQ</Choice>
    <Choice>DWELL</Choice>
    <Val>0</Val>
  </EW>
  <I32>
    <Name>Frames 3</Name>
    <Val>0</Val>
  </I32>
  <U16>
    <Name>Output 3</Name>
    <Val>0</Val>
  </U16>
  <String>
    <Name>Label 3</Name>
    <Val/>
  </String>
  <EW>
    <Name>Type 4</Name>
    <Choice>UNUSED</Choice>
    <Choice>DAQ</Choice>
    <Choice>DWELL</Choice>
    <Val>0</Val>
  </EW>
  <I32>
    <Name>Frames 4</Name>
    <Val>0</Val>
  </I32>
  <U16>
    <Name>Output 4</Name>
    <Val>0</Val>
  </U16>
  <String>
    <Name>Label 4</Name>
    <Val/>
  </String>
  <EW>
    <Name>Type 5</Name>
    <Choice>UNUSED</Choice>
    <Choice>DAQ</Choice>
    <Choice>DWELL</Choice>
    <Val>0</Val>
  </EW>
  <I32>
    <Name>Frames 5</Name>
    <Val>0</Val>
  </I32>
  <U16>
    <Name>Output 5</Name>
    <Val>0</Val>
  </U16>
  <String>
    <Name>Label 5</Name>
    <Val/>
  </String>
  <EW>
    <Name>Type 6</Name>
    <Choice>UNUSED</Choice>
    <Choice>DAQ</Choice>
    <Choice>DWELL</Choice>
    <Val>0</Val>
  </EW>
  <I32>
    <Name>Frames 6</Name>
    <Val>0</Val>
  </I32>
  <U16>
    <Name>Output 6</Name>
    <Val>0</Val>
  </U16>
  <String>
    <Name>Label 6</Name>
    <Val/>
  </String>
  <EW>
    <Name>Type 7</Name>
    <Choice>UNUSED</Choice>
    <Choice>DAQ</Choice>
    <Choice>DWELL</Choice>
    <Val>0</Val>
  </EW>
  <I32>
    <Name>Frames 7</Name>
    <Val>0</Val>
  </I32>
  <U16>
    <Name>Output 7</Name>
    <Val>0</Val>
  </U16>
  <String>
    <Name>Label 7</Name>
    <Val/>
  </String>
  <EW>
    <Name>Type 8</Name>
    <Choice>UNUSED</Choice>
    <Choice>DAQ</Choice>
    <Choice>DWELL</Choice>
    <Val>0</Val>
  </EW>
  <I32>
    <Name>Frames 8</Name>
    <Val>0</Val>
  </I32>
  <U16>
    <Name>Output 8</Name>
    <Val>0</Val>
  </U16>
  <String>
    <Name>Label 8</Name>
    <Val/>
  </String>
</Cluster>
"""

tcb_settings_template = """
<Cluster>
	<Name>Time Channels</Name>
	<NumElts>123</NumElts>
	<DBL>
		<Name>TR1 From 1</Name>
		<Val>150</Val>
	</DBL>
	<DBL>
		<Name>TR1 To 1</Name>
		<Val>95000</Val>
	</DBL>
	<DBL>
		<Name>TR1 Steps 1</Name>
		<Val>0.002</Val>
	</DBL>
	<U16>
		<Name>TR1 In Mode 1</Name>
		<Val>2</Val>
	</U16>
	<DBL>
		<Name>TR1 From 2</Name>
		<Val>0</Val>
	</DBL>
	<DBL>
		<Name>TR1 To 2</Name>
		<Val>0</Val>
	</DBL>
	<DBL>
		<Name>TR1 Steps 2</Name>
		<Val>0</Val>
	</DBL>
	<U16>
		<Name>TR1 In Mode 2</Name>
		<Val>0</Val>
	</U16>
	<DBL>
		<Name>TR1 From 3</Name>
		<Val>0</Val>
	</DBL>
	<DBL>
		<Name>TR1 To 3</Name>
		<Val>0</Val>
	</DBL>
	<DBL>
		<Name>TR1 Steps 3</Name>
		<Val>0</Val>
	</DBL>
	<U16>
		<Name>TR1 In Mode 3</Name>
		<Val>0</Val>
	</U16>
	<DBL>
		<Name>TR1 From 4</Name>
		<Val>0</Val>
	</DBL>
	<DBL>
		<Name>TR1 To 4</Name>
		<Val>0</Val>
	</DBL>
	<DBL>
		<Name>TR1 Steps 4</Name>
		<Val>0</Val>
	</DBL>
	<U16>
		<Name>TR1 In Mode 4</Name>
		<Val>0</Val>
	</U16>
	<DBL>
		<Name>TR1 From 5</Name>
		<Val>0</Val>
	</DBL>
	<DBL>
		<Name>TR1 To 5</Name>
		<Val>0</Val>
	</DBL>
	<DBL>
		<Name>TR1 Steps 5</Name>
		<Val>0</Val>
	</DBL>
	<U16>
		<Name>TR1 In Mode 5</Name>
		<Val>0</Val>
	</U16>
	<U16>
		<Name>Time Unit</Name>
		<Val>0</Val>
	</U16>
	<String>
		<Name>Time Channel File</Name>
		<Val></Val>
	</String>
	<U16>
		<Name>Calculation Method</Name>
		<Val>0</Val>
	</U16>
	<DBL>
		<Name>TR2 From 1</Name>
		<Val>150</Val>
	</DBL>
	<DBL>
		<Name>TR2 To 1</Name>
		<Val>95000</Val>
	</DBL>
	<DBL>
		<Name>TR2 Steps 1</Name>
		<Val>1.5</Val>
	</DBL>
	<U16>
		<Name>TR2 In Mode 1</Name>
		<Val>1</Val>
	</U16>
	<DBL>
		<Name>TR2 From 2</Name>
		<Val>0</Val>
	</DBL>
	<DBL>
		<Name>TR2 To 2</Name>
		<Val>0</Val>
	</DBL>
	<DBL>
		<Name>TR2 Steps 2</Name>
		<Val>0</Val>
	</DBL>
	<U16>
		<Name>TR2 In Mode 2</Name>
		<Val>0</Val>
	</U16>
	<DBL>
		<Name>TR2 From 3</Name>
		<Val>0</Val>
	</DBL>
	<DBL>
		<Name>TR2 To 3</Name>
		<Val>0</Val>
	</DBL>
	<DBL>
		<Name>TR2 Steps 3</Name>
		<Val>0</Val>
	</DBL>
	<U16>
		<Name>TR2 In Mode 3</Name>
		<Val>0</Val>
	</U16>
	<DBL>
		<Name>TR2 From 4</Name>
		<Val>0</Val>
	</DBL>
	<DBL>
		<Name>TR2 To 4</Name>
		<Val>0</Val>
	</DBL>
	<DBL>
		<Name>TR2 Steps 4</Name>
		<Val>0</Val>
	</DBL>
	<U16>
		<Name>TR2 In Mode 4</Name>
		<Val>0</Val>
	</U16>
	<DBL>
		<Name>TR2 From 5</Name>
		<Val>0</Val>
	</DBL>
	<DBL>
		<Name>TR2 To 5</Name>
		<Val>0</Val>
	</DBL>
	<DBL>
		<Name>TR2 Steps 5</Name>
		<Val>0</Val>
	</DBL>
	<U16>
		<Name>TR2 In Mode 5</Name>
		<Val>0</Val>
	</U16>
	<DBL>
		<Name>TR3 From 1</Name>
		<Val>0</Val>
	</DBL>
	<DBL>
		<Name>TR3 To 1</Name>
		<Val>0</Val>
	</DBL>
	<DBL>
		<Name>TR3 Steps 1</Name>
		<Val>0</Val>
	</DBL>
	<U16>
		<Name>TR3 In Mode 1</Name>
		<Val>0</Val>
	</U16>
	<DBL>
		<Name>TR3 From 2</Name>
		<Val>0</Val>
	</DBL>
	<DBL>
		<Name>TR3 To 2</Name>
		<Val>0</Val>
	</DBL>
	<DBL>
		<Name>TR3 Steps 2</Name>
		<Val>0</Val>
	</DBL>
	<U16>
		<Name>TR3 In Mode 2</Name>
		<Val>0</Val>
	</U16>
	<DBL>
		<Name>TR3 From 3</Name>
		<Val>0</Val>
	</DBL>
	<DBL>
		<Name>TR3 To 3</Name>
		<Val>0</Val>
	</DBL>
	<DBL>
		<Name>TR3 Steps 3</Name>
		<Val>0</Val>
	</DBL>
	<U16>
		<Name>TR3 In Mode 3</Name>
		<Val>0</Val>
	</U16>
	<DBL>
		<Name>TR3 From 4</Name>
		<Val>0</Val>
	</DBL>
	<DBL>
		<Name>TR3 To 4</Name>
		<Val>0</Val>
	</DBL>
	<DBL>
		<Name>TR3 Steps 4</Name>
		<Val>0</Val>
	</DBL>
	<U16>
		<Name>TR3 In Mode 4</Name>
		<Val>0</Val>
	</U16>
	<DBL>
		<Name>TR3 From 5</Name>
		<Val>0</Val>
	</DBL>
	<DBL>
		<Name>TR3 To 5</Name>
		<Val>0</Val>
	</DBL>
	<DBL>
		<Name>TR3 Steps 5</Name>
		<Val>0</Val>
	</DBL>
	<U16>
		<Name>TR3 In Mode 5</Name>
		<Val>0</Val>
	</U16>
	<DBL>
		<Name>TR4 From 1</Name>
		<Val>0</Val>
	</DBL>
	<DBL>
		<Name>TR4 To 1</Name>
		<Val>0</Val>
	</DBL>
	<DBL>
		<Name>TR4 Steps 1</Name>
		<Val>0</Val>
	</DBL>
	<U16>
		<Name>TR4 In Mode 1</Name>
		<Val>0</Val>
	</U16>
	<DBL>
		<Name>TR4 From 2</Name>
		<Val>0</Val>
	</DBL>
	<DBL>
		<Name>TR4 To 2</Name>
		<Val>0</Val>
	</DBL>
	<DBL>
		<Name>TR4 Steps 2</Name>
		<Val>0</Val>
	</DBL>
	<U16>
		<Name>TR4 In Mode 2</Name>
		<Val>0</Val>
	</U16>
	<DBL>
		<Name>TR4 From 3</Name>
		<Val>0</Val>
	</DBL>
	<DBL>
		<Name>TR4 To 3</Name>
		<Val>0</Val>
	</DBL>
	<DBL>
		<Name>TR4 Steps 3</Name>
		<Val>0</Val>
	</DBL>
	<U16>
		<Name>TR4 In Mode 3</Name>
		<Val>0</Val>
	</U16>
	<DBL>
		<Name>TR4 From 4</Name>
		<Val>0</Val>
	</DBL>
	<DBL>
		<Name>TR4 To 4</Name>
		<Val>0</Val>
	</DBL>
	<DBL>
		<Name>TR4 Steps 4</Name>
		<Val>0</Val>
	</DBL>
	<U16>
		<Name>TR4 In Mode 4</Name>
		<Val>0</Val>
	</U16>
	<DBL>
		<Name>TR4 From 5</Name>
		<Val>0</Val>
	</DBL>
	<DBL>
		<Name>TR4 To 5</Name>
		<Val>0</Val>
	</DBL>
	<DBL>
		<Name>TR4 Steps 5</Name>
		<Val>0</Val>
	</DBL>
	<U16>
		<Name>TR4 In Mode 5</Name>
		<Val>0</Val>
	</U16>
	<DBL>
		<Name>TR5 From 1</Name>
		<Val>0</Val>
	</DBL>
	<DBL>
		<Name>TR5 To 1</Name>
		<Val>0</Val>
	</DBL>
	<DBL>
		<Name>TR5 Steps 1</Name>
		<Val>0</Val>
	</DBL>
	<U16>
		<Name>TR5 In Mode 1</Name>
		<Val>0</Val>
	</U16>
	<DBL>
		<Name>TR5 From 2</Name>
		<Val>0</Val>
	</DBL>
	<DBL>
		<Name>TR5 To 2</Name>
		<Val>0</Val>
	</DBL>
	<DBL>
		<Name>TR5 Steps 2</Name>
		<Val>0</Val>
	</DBL>
	<U16>
		<Name>TR5 In Mode 2</Name>
		<Val>0</Val>
	</U16>
	<DBL>
		<Name>TR5 From 3</Name>
		<Val>0</Val>
	</DBL>
	<DBL>
		<Name>TR5 To 3</Name>
		<Val>0</Val>
	</DBL>
	<DBL>
		<Name>TR5 Steps 3</Name>
		<Val>0</Val>
	</DBL>
	<U16>
		<Name>TR5 In Mode 3</Name>
		<Val>0</Val>
	</U16>
	<DBL>
		<Name>TR5 From 4</Name>
		<Val>0</Val>
	</DBL>
	<DBL>
		<Name>TR5 To 4</Name>
		<Val>0</Val>
	</DBL>
	<DBL>
		<Name>TR5 Steps 4</Name>
		<Val>0</Val>
	</DBL>
	<U16>
		<Name>TR5 In Mode 4</Name>
		<Val>0</Val>
	</U16>
	<DBL>
		<Name>TR5 From 5</Name>
		<Val>0</Val>
	</DBL>
	<DBL>
		<Name>TR5 To 5</Name>
		<Val>0</Val>
	</DBL>
	<DBL>
		<Name>TR5 Steps 5</Name>
		<Val>0</Val>
	</DBL>
	<U16>
		<Name>TR5 In Mode 5</Name>
		<Val>0</Val>
	</U16>
	<DBL>
		<Name>TR6 From 1</Name>
		<Val>0</Val>
	</DBL>
	<DBL>
		<Name>TR6 To 1</Name>
		<Val>0</Val>
	</DBL>
	<DBL>
		<Name>TR6 Steps 1</Name>
		<Val>0</Val>
	</DBL>
	<U16>
		<Name>TR6 In Mode 1</Name>
		<Val>0</Val>
	</U16>
	<DBL>
		<Name>TR6 From 2</Name>
		<Val>0</Val>
	</DBL>
	<DBL>
		<Name>TR6 To 2</Name>
		<Val>0</Val>
	</DBL>
	<DBL>
		<Name>TR6 Steps 2</Name>
		<Val>0</Val>
	</DBL>
	<U16>
		<Name>TR6 In Mode 2</Name>
		<Val>0</Val>
	</U16>
	<DBL>
		<Name>TR6 From 3</Name>
		<Val>0</Val>
	</DBL>
	<DBL>
		<Name>TR6 To 3</Name>
		<Val>0</Val>
	</DBL>
	<DBL>
		<Name>TR6 Steps 3</Name>
		<Val>0</Val>
	</DBL>
	<U16>
		<Name>TR6 In Mode 3</Name>
		<Val>0</Val>
	</U16>
	<DBL>
		<Name>TR6 From 4</Name>
		<Val>0</Val>
	</DBL>
	<DBL>
		<Name>TR6 To 4</Name>
		<Val>0</Val>
	</DBL>
	<DBL>
		<Name>TR6 Steps 4</Name>
		<Val>0</Val>
	</DBL>
	<U16>
		<Name>TR6 In Mode 4</Name>
		<Val>0</Val>
	</U16>
	<DBL>
		<Name>TR6 From 5</Name>
		<Val>0</Val>
	</DBL>
	<DBL>
		<Name>TR6 To 5</Name>
		<Val>0</Val>
	</DBL>
	<DBL>
		<Name>TR6 Steps 5</Name>
		<Val>0</Val>
	</DBL>
	<U16>
		<Name>TR6 In Mode 5</Name>
		<Val>0</Val>
	</U16>
</Cluster>
"""
initial_tcb_settings = """
<Cluster>
	<Name>Time Channels</Name>
	<NumElts>123</NumElts>
	<DBL>
		<Name>TR1 From 1</Name>
		<Val>150</Val>
	</DBL>
	<DBL>
		<Name>TR1 To 1</Name>
		<Val>95000</Val>
	</DBL>
	<DBL>
		<Name>TR1 Steps 1</Name>
		<Val>0.002</Val>
	</DBL>
	<U16>
		<Name>TR1 In Mode 1</Name>
		<Val>2</Val>
	</U16>
	<DBL>
		<Name>TR1 From 2</Name>
		<Val>0</Val>
	</DBL>
	<DBL>
		<Name>TR1 To 2</Name>
		<Val>0</Val>
	</DBL>
	<DBL>
		<Name>TR1 Steps 2</Name>
		<Val>0</Val>
	</DBL>
	<U16>
		<Name>TR1 In Mode 2</Name>
		<Val>0</Val>
	</U16>
	<DBL>
		<Name>TR1 From 3</Name>
		<Val>0</Val>
	</DBL>
	<DBL>
		<Name>TR1 To 3</Name>
		<Val>0</Val>
	</DBL>
	<DBL>
		<Name>TR1 Steps 3</Name>
		<Val>0</Val>
	</DBL>
	<U16>
		<Name>TR1 In Mode 3</Name>
		<Val>0</Val>
	</U16>
	<DBL>
		<Name>TR1 From 4</Name>
		<Val>0</Val>
	</DBL>
	<DBL>
		<Name>TR1 To 4</Name>
		<Val>0</Val>
	</DBL>
	<DBL>
		<Name>TR1 Steps 4</Name>
		<Val>0</Val>
	</DBL>
	<U16>
		<Name>TR1 In Mode 4</Name>
		<Val>0</Val>
	</U16>
	<DBL>
		<Name>TR1 From 5</Name>
		<Val>0</Val>
	</DBL>
	<DBL>
		<Name>TR1 To 5</Name>
		<Val>0</Val>
	</DBL>
	<DBL>
		<Name>TR1 Steps 5</Name>
		<Val>0</Val>
	</DBL>
	<U16>
		<Name>TR1 In Mode 5</Name>
		<Val>0</Val>
	</U16>
	<U16>
		<Name>Time Unit</Name>
		<Val>0</Val>
	</U16>
	<String>
		<Name>Time Channel File</Name>
		<Val></Val>
	</String>
	<U16>
		<Name>Calculation Method</Name>
		<Val>0</Val>
	</U16>
	<DBL>
		<Name>TR2 From 1</Name>
		<Val>150</Val>
	</DBL>
	<DBL>
		<Name>TR2 To 1</Name>
		<Val>95000</Val>
	</DBL>
	<DBL>
		<Name>TR2 Steps 1</Name>
		<Val>1.5</Val>
	</DBL>
	<U16>
		<Name>TR2 In Mode 1</Name>
		<Val>1</Val>
	</U16>
	<DBL>
		<Name>TR2 From 2</Name>
		<Val>0</Val>
	</DBL>
	<DBL>
		<Name>TR2 To 2</Name>
		<Val>0</Val>
	</DBL>
	<DBL>
		<Name>TR2 Steps 2</Name>
		<Val>0</Val>
	</DBL>
	<U16>
		<Name>TR2 In Mode 2</Name>
		<Val>0</Val>
	</U16>
	<DBL>
		<Name>TR2 From 3</Name>
		<Val>0</Val>
	</DBL>
	<DBL>
		<Name>TR2 To 3</Name>
		<Val>0</Val>
	</DBL>
	<DBL>
		<Name>TR2 Steps 3</Name>
		<Val>0</Val>
	</DBL>
	<U16>
		<Name>TR2 In Mode 3</Name>
		<Val>0</Val>
	</U16>
	<DBL>
		<Name>TR2 From 4</Name>
		<Val>0</Val>
	</DBL>
	<DBL>
		<Name>TR2 To 4</Name>
		<Val>0</Val>
	</DBL>
	<DBL>
		<Name>TR2 Steps 4</Name>
		<Val>0</Val>
	</DBL>
	<U16>
		<Name>TR2 In Mode 4</Name>
		<Val>0</Val>
	</U16>
	<DBL>
		<Name>TR2 From 5</Name>
		<Val>0</Val>
	</DBL>
	<DBL>
		<Name>TR2 To 5</Name>
		<Val>0</Val>
	</DBL>
	<DBL>
		<Name>TR2 Steps 5</Name>
		<Val>0</Val>
	</DBL>
	<U16>
		<Name>TR2 In Mode 5</Name>
		<Val>0</Val>
	</U16>
	<DBL>
		<Name>TR3 From 1</Name>
		<Val>0</Val>
	</DBL>
	<DBL>
		<Name>TR3 To 1</Name>
		<Val>0</Val>
	</DBL>
	<DBL>
		<Name>TR3 Steps 1</Name>
		<Val>0</Val>
	</DBL>
	<U16>
		<Name>TR3 In Mode 1</Name>
		<Val>0</Val>
	</U16>
	<DBL>
		<Name>TR3 From 2</Name>
		<Val>0</Val>
	</DBL>
	<DBL>
		<Name>TR3 To 2</Name>
		<Val>0</Val>
	</DBL>
	<DBL>
		<Name>TR3 Steps 2</Name>
		<Val>0</Val>
	</DBL>
	<U16>
		<Name>TR3 In Mode 2</Name>
		<Val>0</Val>
	</U16>
	<DBL>
		<Name>TR3 From 3</Name>
		<Val>0</Val>
	</DBL>
	<DBL>
		<Name>TR3 To 3</Name>
		<Val>0</Val>
	</DBL>
	<DBL>
		<Name>TR3 Steps 3</Name>
		<Val>0</Val>
	</DBL>
	<U16>
		<Name>TR3 In Mode 3</Name>
		<Val>0</Val>
	</U16>
	<DBL>
		<Name>TR3 From 4</Name>
		<Val>0</Val>
	</DBL>
	<DBL>
		<Name>TR3 To 4</Name>
		<Val>0</Val>
	</DBL>
	<DBL>
		<Name>TR3 Steps 4</Name>
		<Val>0</Val>
	</DBL>
	<U16>
		<Name>TR3 In Mode 4</Name>
		<Val>0</Val>
	</U16>
	<DBL>
		<Name>TR3 From 5</Name>
		<Val>0</Val>
	</DBL>
	<DBL>
		<Name>TR3 To 5</Name>
		<Val>0</Val>
	</DBL>
	<DBL>
		<Name>TR3 Steps 5</Name>
		<Val>0</Val>
	</DBL>
	<U16>
		<Name>TR3 In Mode 5</Name>
		<Val>0</Val>
	</U16>
	<DBL>
		<Name>TR4 From 1</Name>
		<Val>0</Val>
	</DBL>
	<DBL>
		<Name>TR4 To 1</Name>
		<Val>0</Val>
	</DBL>
	<DBL>
		<Name>TR4 Steps 1</Name>
		<Val>0</Val>
	</DBL>
	<U16>
		<Name>TR4 In Mode 1</Name>
		<Val>0</Val>
	</U16>
	<DBL>
		<Name>TR4 From 2</Name>
		<Val>0</Val>
	</DBL>
	<DBL>
		<Name>TR4 To 2</Name>
		<Val>0</Val>
	</DBL>
	<DBL>
		<Name>TR4 Steps 2</Name>
		<Val>0</Val>
	</DBL>
	<U16>
		<Name>TR4 In Mode 2</Name>
		<Val>0</Val>
	</U16>
	<DBL>
		<Name>TR4 From 3</Name>
		<Val>0</Val>
	</DBL>
	<DBL>
		<Name>TR4 To 3</Name>
		<Val>0</Val>
	</DBL>
	<DBL>
		<Name>TR4 Steps 3</Name>
		<Val>0</Val>
	</DBL>
	<U16>
		<Name>TR4 In Mode 3</Name>
		<Val>0</Val>
	</U16>
	<DBL>
		<Name>TR4 From 4</Name>
		<Val>0</Val>
	</DBL>
	<DBL>
		<Name>TR4 To 4</Name>
		<Val>0</Val>
	</DBL>
	<DBL>
		<Name>TR4 Steps 4</Name>
		<Val>0</Val>
	</DBL>
	<U16>
		<Name>TR4 In Mode 4</Name>
		<Val>0</Val>
	</U16>
	<DBL>
		<Name>TR4 From 5</Name>
		<Val>0</Val>
	</DBL>
	<DBL>
		<Name>TR4 To 5</Name>
		<Val>0</Val>
	</DBL>
	<DBL>
		<Name>TR4 Steps 5</Name>
		<Val>0</Val>
	</DBL>
	<U16>
		<Name>TR4 In Mode 5</Name>
		<Val>0</Val>
	</U16>
	<DBL>
		<Name>TR5 From 1</Name>
		<Val>0</Val>
	</DBL>
	<DBL>
		<Name>TR5 To 1</Name>
		<Val>0</Val>
	</DBL>
	<DBL>
		<Name>TR5 Steps 1</Name>
		<Val>0</Val>
	</DBL>
	<U16>
		<Name>TR5 In Mode 1</Name>
		<Val>0</Val>
	</U16>
	<DBL>
		<Name>TR5 From 2</Name>
		<Val>0</Val>
	</DBL>
	<DBL>
		<Name>TR5 To 2</Name>
		<Val>0</Val>
	</DBL>
	<DBL>
		<Name>TR5 Steps 2</Name>
		<Val>0</Val>
	</DBL>
	<U16>
		<Name>TR5 In Mode 2</Name>
		<Val>0</Val>
	</U16>
	<DBL>
		<Name>TR5 From 3</Name>
		<Val>0</Val>
	</DBL>
	<DBL>
		<Name>TR5 To 3</Name>
		<Val>0</Val>
	</DBL>
	<DBL>
		<Name>TR5 Steps 3</Name>
		<Val>0</Val>
	</DBL>
	<U16>
		<Name>TR5 In Mode 3</Name>
		<Val>0</Val>
	</U16>
	<DBL>
		<Name>TR5 From 4</Name>
		<Val>0</Val>
	</DBL>
	<DBL>
		<Name>TR5 To 4</Name>
		<Val>0</Val>
	</DBL>
	<DBL>
		<Name>TR5 Steps 4</Name>
		<Val>0</Val>
	</DBL>
	<U16>
		<Name>TR5 In Mode 4</Name>
		<Val>0</Val>
	</U16>
	<DBL>
		<Name>TR5 From 5</Name>
		<Val>0</Val>
	</DBL>
	<DBL>
		<Name>TR5 To 5</Name>
		<Val>0</Val>
	</DBL>
	<DBL>
		<Name>TR5 Steps 5</Name>
		<Val>0</Val>
	</DBL>
	<U16>
		<Name>TR5 In Mode 5</Name>
		<Val>0</Val>
	</U16>
	<DBL>
		<Name>TR6 From 1</Name>
		<Val>0</Val>
	</DBL>
	<DBL>
		<Name>TR6 To 1</Name>
		<Val>0</Val>
	</DBL>
	<DBL>
		<Name>TR6 Steps 1</Name>
		<Val>0</Val>
	</DBL>
	<U16>
		<Name>TR6 In Mode 1</Name>
		<Val>0</Val>
	</U16>
	<DBL>
		<Name>TR6 From 2</Name>
		<Val>0</Val>
	</DBL>
	<DBL>
		<Name>TR6 To 2</Name>
		<Val>0</Val>
	</DBL>
	<DBL>
		<Name>TR6 Steps 2</Name>
		<Val>0</Val>
	</DBL>
	<U16>
		<Name>TR6 In Mode 2</Name>
		<Val>0</Val>
	</U16>
	<DBL>
		<Name>TR6 From 3</Name>
		<Val>0</Val>
	</DBL>
	<DBL>
		<Name>TR6 To 3</Name>
		<Val>0</Val>
	</DBL>
	<DBL>
		<Name>TR6 Steps 3</Name>
		<Val>0</Val>
	</DBL>
	<U16>
		<Name>TR6 In Mode 3</Name>
		<Val>0</Val>
	</U16>
	<DBL>
		<Name>TR6 From 4</Name>
		<Val>0</Val>
	</DBL>
	<DBL>
		<Name>TR6 To 4</Name>
		<Val>0</Val>
	</DBL>
	<DBL>
		<Name>TR6 Steps 4</Name>
		<Val>0</Val>
	</DBL>
	<U16>
		<Name>TR6 In Mode 4</Name>
		<Val>0</Val>
	</U16>
	<DBL>
		<Name>TR6 From 5</Name>
		<Val>0</Val>
	</DBL>
	<DBL>
		<Name>TR6 To 5</Name>
		<Val>0</Val>
	</DBL>
	<DBL>
		<Name>TR6 Steps 5</Name>
		<Val>0</Val>
	</DBL>
	<U16>
		<Name>TR6 In Mode 5</Name>
		<Val>0</Val>
	</U16>
</Cluster>
"""

dae_settings_template = """<?xml version="1.0"?>
<Cluster>
  <Name>Data Acquisition</Name>
  <NumElts>23</NumElts>
  <I32>
    <Name>Monitor Spectrum</Name>
    <Val>{mon_spec}</Val>
  </I32>
  <DBL>
    <Name>from</Name>
    <Val>{from_}</Val>
  </DBL>
  <DBL>
    <Name>to</Name>
    <Val>{to}</Val>
  </DBL>
  <String>
    <Name>Wiring Table</Name>
    <Val>{wiring_table}</Val>
  </String>
  <String>
    <Name>Detector Table</Name>
    <Val>{detector_table}</Val>
  </String>
  <String>
    <Name>Spectra Table</Name>
    <Val>{spectra_table}</Val>
  </String>
  <EW>
    <Name>DAETimingSource</Name>
    <Choice>ISIS</Choice>
    <Choice>Internal Test Clock</Choice>
    <Choice>SMP</Choice>
    <Choice>Muon Cerenkov</Choice>
    <Choice>Muon MS</Choice>
    <Choice>ISIS (first TS1)</Choice>
    <Choice>TS1 Only</Choice>
    <Val>{timing_src}</Val>
  </EW>
  <EW>
    <Name>SMP (Chopper) Veto</Name>
    <Choice>NO</Choice>
    <Choice>YES</Choice>
    <Val>{smp_veto}</Val>
  </EW>
  <EW>
    <Name>Veto 0</Name>
    <Choice>NO</Choice>
    <Choice>YES</Choice>
    <Val>{veto_0}</Val>
  </EW>
  <EW>
    <Name>Muon MS Mode</Name>
    <Choice>DISABLED</Choice>
    <Choice>ENABLED</Choice>
    <Val>{muon_ms_mode}</Val>
  </EW>
  <EW>
    <Name> Fermi Chopper Veto</Name>
    <Choice>NO</Choice>
    <Choice>YES</Choice>
    <Val>{fermi_veto}</Val>
  </EW>
  <DBL>
    <Name>FC Delay</Name>
    <Val>{fc_delay}</Val>
  </DBL>
  <DBL>
    <Name>FC Width</Name>
    <Val>{fc_width}</Val>
  </DBL>
  <EW>
    <Name>Veto 1</Name>
    <Choice>NO</Choice>
    <Choice>YES</Choice>
    <Val>{veto_1}</Val>
  </EW>
  <EW>
    <Name>Veto 2</Name>
    <Choice>NO</Choice>
    <Choice>YES</Choice>
    <Val>{veto_2}</Val>
  </EW>
  <EW>
    <Name>Veto 3</Name>
    <Choice>NO</Choice>
    <Choice>YES</Choice>
    <Val>{veto_3}</Val>
  </EW>
  <EW>
    <Name>Muon Cerenkov Pulse</Name>
    <Choice>FIRST</Choice>
    <Choice>SECOND</Choice>
    <Val>{muon_cherenkov_pulse}</Val>
  </EW>
  <EW>
    <Name> TS2 Pulse Veto</Name>
    <Choice>NO</Choice>
    <Choice>YES</Choice>
    <Val>{ts2_veto}</Val>
  </EW>
  <EW>
    <Name> ISIS 50Hz Veto</Name>
    <Choice>NO</Choice>
    <Choice>YES</Choice>
    <Val>{hz50_veto}</Val>
  </EW>
  <String>
    <Name>Veto 0 Name</Name>
    <Val>{veto_0_name}</Val>
  </String>
  <String>
    <Name>Veto 1 Name</Name>
    <Val>{veto_1_name}</Val>
  </String>
  <String>
    <Name>Veto 2 Name</Name>
    <Val/>
  </String>
  <String>
    <Name>Veto 3 Name</Name>
    <Val/>
  </String>
</Cluster>
"""
initial_dae_settings = r"""<?xml version="1.0"?>
<Cluster>
  <Name>Data Acquisition</Name>
  <NumElts>23</NumElts>
  <I32>
    <Name>Monitor Spectrum</Name>
    <Val>4</Val>
  </I32>
  <DBL>
    <Name>from</Name>
    <Val>1000</Val>
  </DBL>
  <DBL>
    <Name>to</Name>
    <Val>5000</Val>
  </DBL>
  <String>
    <Name>Wiring Table</Name>
    <Val>C:/Instrument/Settings/config/NDXNIMROD/configurations/tables/NIMROD84modules+9monitors+LAB5Oct2012Wiring.dat</Val>
  </String>
  <String>
    <Name>Detector Table</Name>
    <Val>C:/Instrument/Settings/config/NDXNIMROD/configurations/tables/NIMROD84modules+9monitors+LAB5Oct2012Detector.dat</Val>
  </String>
  <String>
    <Name>Spectra Table</Name>
    <Val>C:/Instrument/Settings/config/NDXNIMROD/configurations/tables/NIMROD84modules+9monitors+LAB5Oct2012Spectra.dat</Val>
  </String>
  <EW>
    <Name>DAETimingSource</Name>
    <Choice>ISIS</Choice>
    <Choice>Internal Test Clock</Choice>
    <Choice>SMP</Choice>
    <Choice>Muon Cerenkov</Choice>
    <Choice>Muon MS</Choice>
    <Choice>ISIS (first TS1)</Choice>
    <Choice>TS1 Only</Choice>
    <Val>0</Val>
  </EW>
  <EW>
    <Name>SMP (Chopper) Veto</Name>
    <Choice>NO</Choice>
    <Choice>YES</Choice>
    <Val>0</Val>
  </EW>
  <EW>
    <Name>Veto 0</Name>
    <Choice>NO</Choice>
    <Choice>YES</Choice>
    <Val>0</Val>
  </EW>
  <EW>
    <Name>Muon MS Mode</Name>
    <Choice>DISABLED</Choice>
    <Choice>ENABLED</Choice>
    <Val>1</Val>
  </EW>
  <EW>
    <Name> Fermi Chopper Veto</Name>
    <Choice>NO</Choice>
    <Choice>YES</Choice>
    <Val>0</Val>
  </EW>
  <DBL>
    <Name>FC Delay</Name>
    <Val>0</Val>
  </DBL>
  <DBL>
    <Name>FC Width</Name>
    <Val>0</Val>
  </DBL>
  <EW>
    <Name>Veto 1</Name>
    <Choice>NO</Choice>
    <Choice>YES</Choice>
    <Val>0</Val>
  </EW>
  <EW>
    <Name>Veto 2</Name>
    <Choice>NO</Choice>
    <Choice>YES</Choice>
    <Val>0</Val>
  </EW>
  <EW>
    <Name>Veto 3</Name>
    <Choice>NO</Choice>
    <Choice>YES</Choice>
    <Val>0</Val>
  </EW>
  <EW>
    <Name>Muon Cerenkov Pulse</Name>
    <Choice>FIRST</Choice>
    <Choice>SECOND</Choice>
    <Val>0</Val>
  </EW>
  <EW>
    <Name> TS2 Pulse Veto</Name>
    <Choice>NO</Choice>
    <Choice>YES</Choice>
    <Val>0</Val>
  </EW>
  <EW>
    <Name> ISIS 50Hz Veto</Name>
    <Choice>NO</Choice>
    <Choice>YES</Choice>
    <Val>0</Val>
  </EW>
  <String>
    <Name>Veto 0 Name</Name>
    <Val/>
  </String>
  <String>
    <Name>Veto 1 Name</Name>
    <Val/>
  </String>
  <String>
    <Name>Veto 2 Name</Name>
    <Val/>
  </String>
  <String>
    <Name>Veto 3 Name</Name>
    <Val/>
  </String>
</Cluster>
"""


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
    await daesettings.dae_settings.connect(mock=True)
    await daesettings.dae_settings.set(initial_dae_settings)

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
    xml = await daesettings.dae_settings.get_value()
    assert ET.canonicalize(xml) == ET.canonicalize(xml_filled_in)

async def test_period_settings_get_parsed_correctly():
    data = DaePeriodSettingsData()

    periodsettings = DaePeriodSettings(MOCK_PREFIX)
    await periodsettings.period_settings.connect(mock=True)
    await periodsettings.period_settings.set(initial_period_settings)
    pass

async def test_tcb_settings_get_parsed_correctly():
    data = DaeTCBSettingsData()

    tcbsettings = DaeTCBSettings(MOCK_PREFIX)
    await tcbsettings.tcb_settings.connect(mock=True)
    await tcbsettings.tcb_settings.set(initial_tcb_settings)
    pass
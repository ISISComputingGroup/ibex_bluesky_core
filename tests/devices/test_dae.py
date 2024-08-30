# pyright: reportMissingParameterType=false
from enum import Enum
from xml.etree import ElementTree as ET

import pytest
from ibex_bluesky_core.devices.dae.dae import Dae, RunstateEnum
from ophyd_async.core import get_mock_put

from src.ibex_bluesky_core.devices.dae import set_value_in_dae_xml, convert_xml_to_names_and_values
from src.ibex_bluesky_core.devices.dae.dae_controls import BeginRunExBits


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
    await dae.controls.begin_run_ex.set(BeginRunExBits.NONE+BeginRunExBits.BEGINIFPAUSED+BeginRunExBits.BEGINIFDELAYED)
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
    assert not ret

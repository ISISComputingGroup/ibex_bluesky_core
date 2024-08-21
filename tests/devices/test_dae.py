# pyright: reportMissingParameterType=false

import pytest
from ophyd_async.core import get_mock_put

from ibex_bluesky_core.devices.dae import Dae


@pytest.fixture
async def dae() -> Dae:
    dae = Dae("UNITTEST:MOCK:")
    await dae.connect(mock=True)
    return dae


def test_dae_naming(dae: Dae):
    assert dae.name == "DAE"
    assert dae.good_uah.name == "DAE-good_uah"


def test_explicit_dae_naming():
    dae_explicitly_named = Dae("UNITTEST:MOCK:", name="my_special_dae")
    assert dae_explicitly_named.name == "my_special_dae"
    assert dae_explicitly_named.good_uah.name == "my_special_dae-good_uah"


def test_dae_monitors_correct_pvs(dae: Dae):
    assert dae.good_uah.source.endswith("UNITTEST:MOCK:DAE:GOODUAH")
    assert dae.begin_run.source.endswith("UNITTEST:MOCK:DAE:BEGINRUN")
    assert dae.end_run.source.endswith("UNITTEST:MOCK:DAE:ENDRUN")


async def test_dae_read_contains_intensity_and_default_keys(dae: Dae):
    reading = await dae.read()

    assert "DAE" in reading.keys()
    assert "DAE-good_uah" in reading.keys()


async def test_dae_describe_contains_intensity_and_default_keys(dae: Dae):
    descriptor = await dae.describe()

    assert "DAE" in descriptor.keys()
    assert "DAE-good_uah" in descriptor.keys()


async def test_dae_descriptor_contains_same_keys_as_reading(dae: Dae):
    reading = await dae.read()
    descriptor = await dae.describe()

    assert reading.keys() == descriptor.keys()


async def test_trigger_calls_triggers_begin_and_end(dae: Dae):
    get_mock_put(dae.begin_run).assert_not_called()
    get_mock_put(dae.end_run).assert_not_called()

    await dae.trigger()

    get_mock_put(dae.begin_run).assert_called_once()
    get_mock_put(dae.end_run).assert_called_once()

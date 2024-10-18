# pyright: reportMissingParameterType=false
import functools
from collections import namedtuple
from unittest.mock import patch

import pytest
from bluesky import preprocessors as bpp
from bluesky.utils import Msg
from ophyd_async.core import set_mock_value
from ophyd_async.epics.signal import epics_signal_r

from ibex_bluesky_core.preprocessors import _get_rb_number_signal, add_rb_number_processor
from tests.conftest import MOCK_PREFIX

SignalWithExpectedRbv = namedtuple("SignalWithExpectedRbv", ["signal", "rb_num"])


@pytest.fixture
async def mock_rb_num() -> SignalWithExpectedRbv:
    mock_rbnum_signal = epics_signal_r(str, f"{MOCK_PREFIX}ED:RBNUMBER", name="rb_number")
    await mock_rbnum_signal.connect(mock=True)
    rb_num = "123456"
    set_mock_value(mock_rbnum_signal, rb_num)
    return SignalWithExpectedRbv(mock_rbnum_signal, rb_num)


async def test_rb_number_preprocessor_adds_rb_number(RE, mock_rb_num):
    with (
        patch(
            "ibex_bluesky_core.preprocessors._get_rb_number_signal", return_value=mock_rb_num.signal
        ),
        patch("ibex_bluesky_core.preprocessors.ensure_connected"),
    ):
        messages = []
        RE.preprocessors = [functools.partial(bpp.plan_mutator, msg_proc=add_rb_number_processor)]

        @bpp.subs_decorator(lambda typ, doc: messages.append((typ, doc)))
        def plan():
            yield Msg("open_run")
            yield Msg("close_run")

        RE(plan())
        start_typ, start_doc = messages[0]
        assert start_typ == "start"
        assert start_doc["rb_number"] == mock_rb_num.rb_num


async def test_rb_number_preprocessor_adds_unknown_if_signal_not_connected(RE, mock_rb_num):
    with (
        patch(
            "ibex_bluesky_core.preprocessors._get_rb_number_signal", return_value=mock_rb_num.signal
        ),
        patch("ibex_bluesky_core.preprocessors.ensure_connected", side_effect=Exception("test")),
    ):
        messages = []

        RE.preprocessors = [functools.partial(bpp.plan_mutator, msg_proc=add_rb_number_processor)]

        @bpp.subs_decorator(lambda typ, doc: messages.append((typ, doc)))
        def plan():
            yield Msg("open_run")
            yield Msg("close_run")

        RE(plan())
        start_typ, start_doc = messages[0]
        assert start_typ == "start"
        assert start_doc["rb_number"] == "(unknown)"


def test_get_rb_number_signal_name_is_correct():
    rb_num_pv = "ED:RBNUMBER"
    protocol_prefix = "ca://"
    with patch("ibex_bluesky_core.preprocessors.get_pv_prefix", return_value=MOCK_PREFIX):
        signal = _get_rb_number_signal()
        assert signal.source == f"{protocol_prefix}{MOCK_PREFIX}{rb_num_pv}"

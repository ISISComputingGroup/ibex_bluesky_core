from unittest.mock import patch

from ibex_bluesky_core.preprocessors import add_rb_number_processor
from ophyd_async.epics.signal import epics_signal_r
from ophyd_async.core import set_mock_value
from bluesky.utils import Msg





async def test_rb_number_preprocessor_adds_rb_number():
    mock_rbnum_signal = epics_signal_r(str, f"UNITTEST:ED:RBNUMBER", name="rb_number")
    await mock_rbnum_signal.connect(mock=True)
    set_mock_value(mock_rbnum_signal, "123456")

    with patch("ibex_bluesky_core.preprocessors._get_rb_number_signal", return_value=mock_rbnum_signal):
        initial_msg = Msg("open_run")
        output_gen = add_rb_number_processor(initial_msg)[0]

        assert False
from ibex_bluesky_core.utils.isis_epics_signals import isis_epics_signal_rw
from unittest.mock import patch
from time import sleep


def test_isis_epics_rw_signal_appends_correct_sp_suffix():
    with patch(
        "ibex_bluesky_core.utils.isis_epics_signals.epics_signal_rw"
    ) as mock_epics_signal_rw:
        read_pv = "TEST"
        expected_sp_pv = f"{read_pv}:SP"
        datatype = int
        isis_epics_signal_rw(datatype=datatype, read_pv=read_pv)
        mock_epics_signal_rw.assert_called_with(int, read_pv, expected_sp_pv, "")

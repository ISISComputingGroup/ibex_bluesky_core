from unittest.mock import patch

from ibex_bluesky_core.devices.dae import Dae


def test_dae_naming():
    dae = Dae()

    assert dae.name == "DAE"


def test_dae_monitors_correct_pvs():
    with patch("ibex_bluesky_core.devices.dae.get_pv_prefix") as mock_prefix:
        mock_prefix.return_value = "UNITTEST:MOCK:"

        dae = Dae()

        assert dae.good_uah.source == "ca://UNITTEST:MOCK:DAE:GOODUAH"
        assert dae.begin_run.source == "ca://UNITTEST:MOCK:DAE:BEGINRUN"
        assert dae.end_run.source == "ca://UNITTEST:MOCK:DAE:ENDRUN"

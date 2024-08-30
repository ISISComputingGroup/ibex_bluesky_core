from unittest.mock import patch

import pytest

from ibex_bluesky_core.devices import (
    compress_and_hex,
    dehex_and_decompress,
    get_pv_prefix,
    isis_epics_signal_rw,
)


def test_can_dehex_and_decompress():
    expected = b"test123"
    hexed_and_compressed = b"789c2b492d2e31343206000aca0257"
    result = dehex_and_decompress(hexed_and_compressed)
    assert result == expected


def test_can_hex_and_compress():
    to_compress_and_hex = "test123"
    expected = b"789c2b492d2e31343206000aca0257"
    result = compress_and_hex(to_compress_and_hex)
    assert result == expected


def test_get_pv_prefix():
    with patch("os.getenv") as mock_getenv:
        mock_getenv.return_value = "UNITTEST:MOCK:"
        assert get_pv_prefix() == "UNITTEST:MOCK:"


def test_cannot_get_pv_prefix():
    with patch("os.getenv") as mock_getenv:
        mock_getenv.return_value = None
        with pytest.raises(EnvironmentError):
            get_pv_prefix()


def test_isis_epics_rw_signal_appends_correct_sp_suffix():
    with patch("ibex_bluesky_core.devices.epics_signal_rw") as mock_epics_signal_rw:
        read_pv = "TEST"
        expected_sp_pv = f"{read_pv}:SP"
        datatype = int
        isis_epics_signal_rw(datatype=datatype, read_pv=read_pv)
        mock_epics_signal_rw.assert_called_with(int, read_pv, expected_sp_pv, "")

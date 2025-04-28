from unittest.mock import patch

import pytest

from ibex_bluesky_core.utils import centred_pixel, get_pv_prefix, is_matplotlib_backend_qt


def test_get_pv_prefix():
    with patch("os.getenv") as mock_getenv:
        mock_getenv.return_value = "UNITTEST:MOCK:"
        assert get_pv_prefix() == "UNITTEST:MOCK:"


def test_cannot_get_pv_prefix():
    with patch("os.getenv") as mock_getenv:
        mock_getenv.return_value = None
        with pytest.raises(EnvironmentError, match="MYPVPREFIX environment variable not available"):
            get_pv_prefix()


def test_centred_pixel():
    assert centred_pixel(50, 3) == [47, 48, 49, 50, 51, 52, 53]


@pytest.mark.parametrize("mpl_backend", ["qt5Agg", "qt6Agg", "qtCairo", "something_else"])
def test_is_matplotlib_backend_qt(mpl_backend: str):
    with patch("ibex_bluesky_core.utils.matplotlib.get_backend", return_value=mpl_backend):
        assert is_matplotlib_backend_qt() == ("qt" in mpl_backend)

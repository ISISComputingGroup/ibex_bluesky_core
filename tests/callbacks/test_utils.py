import sys
from unittest.mock import patch


def test_default_output_location_with_env_var():
    with patch("ibex_bluesky_core.callbacks._utils.os.environ.get", return_value="foo"):
        del sys.modules["ibex_bluesky_core.callbacks._utils"]
        from ibex_bluesky_core.callbacks._utils import DEFAULT_PATH  # noqa PLC0415

        assert str(DEFAULT_PATH) == "foo"


def test_default_output_location_without_env_var():
    with patch("ibex_bluesky_core.callbacks._utils.os.environ.get", return_value=None):
        del sys.modules["ibex_bluesky_core.callbacks._utils"]
        from ibex_bluesky_core.callbacks._utils import DEFAULT_PATH  # noqa PLC0415

        assert "isis.cclrc.ac.uk" in str(DEFAULT_PATH)

import os
from unittest.mock import patch

import pytest

from ibex_bluesky_core.callbacks import get_default_output_path


def test_default_output_location_with_env_var():
    with patch("ibex_bluesky_core.callbacks._utils.os.environ.get", return_value="foo"):
        assert str(get_default_output_path()) == "foo"


@pytest.mark.skipif(os.name != "nt", reason="Windows only")
def test_default_output_location_without_env_var():
    with patch("ibex_bluesky_core.callbacks._utils.os.environ.get", return_value=None):
        assert str(get_default_output_path()).startswith(r"\\isis.cclrc.ac.uk")

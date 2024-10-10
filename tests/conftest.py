import pytest
from bluesky.run_engine import RunEngine

from ibex_bluesky_core.run_engine import get_run_engine

MOCK_PREFIX = "UNITTEST:MOCK:"


@pytest.fixture
def RE() -> RunEngine:
    get_run_engine.cache_clear()
    re = get_run_engine()
    # Clear the preprocessors as the file writing one relies
    # on a real signal which won't exist during testing
    re.preprocessors.clear()

    return re

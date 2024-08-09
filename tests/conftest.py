import pytest
from bluesky.run_engine import RunEngine
from ibex_bluesky_core.run_engine import get_run_engine


@pytest.fixture
def RE() -> RunEngine:
    get_run_engine.cache_clear()
    return get_run_engine()

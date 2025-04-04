import pytest
from bluesky.run_engine import RunEngine

from ibex_bluesky_core.devices.simpledae import SimpleDae
from ibex_bluesky_core.devices.simpledae.strategies import Controller, Reducer, Waiter
from ibex_bluesky_core.run_engine import get_run_engine

MOCK_PREFIX = "UNITTEST:MOCK:"


@pytest.fixture
def RE() -> RunEngine:
    get_run_engine.cache_clear()
    RE = get_run_engine()
    # Clear the preprocessors as the rb number metadata injector relies
    # on a real signal which won't exist during testing
    RE.preprocessors.clear()

    return RE


@pytest.fixture
async def simpledae() -> SimpleDae:
    dae = SimpleDae(
        prefix="unittest:mock:",
        name="dae",
        controller=Controller(),
        waiter=Waiter(),
        reducer=Reducer(),
    )
    await dae.connect(mock=True)
    return dae

from collections.abc import Generator

import pytest
from bluesky.run_engine import RunEngine

from ibex_bluesky_core.devices.simpledae import Controller, Reducer, SimpleDae, Waiter
from ibex_bluesky_core.run_engine import get_run_engine

MOCK_PREFIX = "UNITTEST:MOCK:"


@pytest.fixture
def RE() -> Generator[RunEngine, None, None]:
    get_run_engine.cache_clear()
    RE = get_run_engine()
    # Clear the preprocessors as the rb number metadata injector relies
    # on a real signal which won't exist during testing
    RE.preprocessors.clear()

    yield RE

    # This is to avoid allowing one test to leave the RE in running/paused state
    # which may affect further tests
    if RE.state != "idle":
        RE.abort()


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

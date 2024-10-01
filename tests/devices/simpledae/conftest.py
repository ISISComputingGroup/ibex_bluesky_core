import pytest

from ibex_bluesky_core.devices.simpledae import SimpleDae
from ibex_bluesky_core.devices.simpledae.strategies import Controller, Reducer, Waiter


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

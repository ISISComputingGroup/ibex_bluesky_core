from unittest.mock import patch

import numpy as np

from ibex_bluesky_core.devices.block import BlockRw
from ibex_bluesky_core.devices.simpledae import SimpleDae, Controller, Waiter
from ibex_bluesky_core.devices.simpledae.reducers import PeriodSpecIntegralsReducer
from ibex_bluesky_core.plans.reflectometry.det_map_align import mapping_alignment_plan


async def test_det_map_align(RE):
    noop_controller = Controller()
    noop_waiter = Waiter()
    reducer = PeriodSpecIntegralsReducer(monitors=np.array([1]), detectors=np.array([2, 3, 4]))

    dae = SimpleDae(prefix="unittest:", name="dae", controller=noop_controller, waiter=noop_waiter, reducer=reducer)
    height = BlockRw(prefix="unittest:", block_name="height", datatype=float)

    await dae.connect(mock=True)
    await height.connect(mock=True)

    with patch("ibex_bluesky_core.plans.reflectometry.det_map_align.ensure_connected"):
        result = RE(mapping_alignment_plan(
            dae=dae,  # type: ignore
            height=height,
            start=0,
            stop=10,
            num=10,
            angle_map=np.array([1, 2, 3]),
        ))

    assert result == {}

# pyright: reportMissingParameterType=false
from unittest.mock import patch

import numpy as np
import pytest
from ophyd_async.core import soft_signal_rw
from ophyd_async.testing import callback_on_mock_put, set_mock_value

from ibex_bluesky_core.devices.simpledae import SimpleDae
from ibex_bluesky_core.devices.simpledae.reducers import PeriodSpecIntegralsReducer
from ibex_bluesky_core.devices.simpledae.strategies import Controller, Waiter
from ibex_bluesky_core.plans.reflectometry.det_map_align import mapping_alignment_plan


async def test_det_map_align(RE):
    noop_controller = Controller()
    noop_waiter = Waiter()
    reducer = PeriodSpecIntegralsReducer(
        monitors=np.array([1]), detectors=np.array([2, 3, 4, 5, 6])
    )

    dae = SimpleDae(
        prefix="unittest:",
        name="dae",
        controller=noop_controller,
        waiter=noop_waiter,
        reducer=reducer,
    )
    height = soft_signal_rw(float, name="height")

    await dae.connect(mock=True)
    await height.connect(mock=True)

    set_mock_value(dae.number_of_periods, 6)
    set_mock_value(dae.num_spectra, 6)
    set_mock_value(dae.num_time_channels, 1)

    specdata = np.array([
        0, 0, 0, 5000, 0, 0, 0, 0, 0, 1, 0, 0, 0, 0,
        0, 0, 0, 5000, 0, 0, 0, 1, 0, 2, 0, 1, 0, 0,
        0, 0, 0, 5000, 0, 1, 0, 2, 0, 3, 0, 2, 0, 1,
        0, 0, 0, 5000, 0, 1, 0, 2, 0, 3, 0, 2, 0, 1,
        0, 0, 0, 5000, 0, 0, 0, 1, 0, 2, 0, 1, 0, 0,
        0, 0, 0, 5000, 0, 0, 0, 0, 0, 1, 0, 0, 0, 0,
    ])  # fmt: skip

    set_mock_value(dae.raw_spec_data, specdata)
    set_mock_value(dae.raw_spec_data_nord, len(specdata))

    period_num = 0

    def _increment_period_num(*_, **__):
        nonlocal period_num
        period_num += 1
        set_mock_value(dae.period_num, period_num)

    callback_on_mock_put(height, _increment_period_num)

    with patch("ibex_bluesky_core.plans.reflectometry.det_map_align.ensure_connected"):
        result = RE(
            mapping_alignment_plan(
                dae=dae,  # type: ignore
                height=height,  # type: ignore
                start=0,
                stop=10,
                num=6,
                angle_map=np.array([21, 22, 23, 24, 25]),
            )
        )

    print(result.plan_result)
    assert result.plan_result["height_fit"].params["x0"].value == pytest.approx(5.0)
    assert result.plan_result["angle_fit"].params["x0"].value == pytest.approx(23.0)

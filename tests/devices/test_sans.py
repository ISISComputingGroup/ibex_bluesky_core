# pyright: reportMissingParameterType=false
from unittest import mock

import pytest
from ophyd_async.core import soft_signal_rw

from ibex_bluesky_core.devices.simpledae import (
    MultiRegionOfInterestReducer,
    PeriodPerPointController,
    SimpleDae,
    Waiter,
)
from ibex_bluesky_core.fitting import Gaussian
from ibex_bluesky_core.plans.sans import rocking_scan
from ibex_bluesky_core.utils import average_model_results

DETECTOR_SPECTRA_ROIS = {"a": [1, 2, 3], "b": [4, 5, 6], "c": [7, 8, 9]}


@pytest.fixture
async def dae():
    noop_controller = mock.MagicMock(spec=PeriodPerPointController)
    noop_waiter = Waiter()
    reducer = MultiRegionOfInterestReducer(detector_spectra_rois=DETECTOR_SPECTRA_ROIS)

    dae = SimpleDae(
        prefix="unittest:",
        name="dae",
        controller=noop_controller,
        waiter=noop_waiter,
        reducer=reducer,
    )
    await dae.connect(mock=True)
    return dae


@pytest.fixture
def rotation():
    return soft_signal_rw(float, name="rotation")


def test_rocking_scan_decorator(RE, dae, rotation):
    fit_method = Gaussian.fit()

    @rocking_scan(dae, x=rotation.name, fit_method=fit_method)
    def _fake_plan():
        yield from ()

    with mock.patch("ibex_bluesky_core.plans.sans._rocking._rocking_scan_wrapper") as mock_wrapper:
        RE(_fake_plan())

    mock_wrapper.assert_called_once_with(
        mock.ANY,
        dae,
        x="rotation",
        fit_method=fit_method,
        average_method=average_model_results,
    )

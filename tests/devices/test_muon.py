# pyright: reportMissingParameterType=false
from unittest.mock import AsyncMock, patch

import numpy as np
import pytest
import scipp as sc
import scipp.testing

from ibex_bluesky_core.devices.muon import MuonAsymmetryReducer, damped_oscillator
from ibex_bluesky_core.devices.simpledae import MEventsWaiter, PeriodPerPointController, SimpleDae


@pytest.fixture
def asymmetry_reducer():
    return MuonAsymmetryReducer(
        forward_detectors=np.array([1]),
        backward_detectors=np.array([2]),
        prefix="UNITTEST:",
    )


@pytest.fixture
def rebinning_asymmetry_reducer():
    return MuonAsymmetryReducer(
        forward_detectors=np.array([1]),
        backward_detectors=np.array([2]),
        time_bin_edges=sc.linspace("tof", 0, 5, num=6, unit=sc.units.ns, dtype="float64"),
        prefix="UNITTEST:",
    )


@pytest.fixture
async def simpledae(rebinning_asymmetry_reducer):
    dae = SimpleDae(
        prefix="UNITTEST:",
        reducer=rebinning_asymmetry_reducer,
        waiter=MEventsWaiter(5000),
        controller=PeriodPerPointController(save_run=False),
    )
    await dae.connect(mock=True)
    return dae


def test_asymmetry_reducer_readable_signals(simpledae, rebinning_asymmetry_reducer):
    assert rebinning_asymmetry_reducer.additional_readable_signals(simpledae) == [
        simpledae.reducer.B
    ]


def test_rebin_and_sum(rebinning_asymmetry_reducer):
    raw_data = np.array(
        [
            [1, 2, 3, 4, 5],
            [6, 7, 8, 9, 10],
        ],
        dtype="float32",
    )

    time = sc.array(dims=["tof"], values=[0, 0.5, 1, 1.5, 2, 2.5], unit="ns", dtype="float64")
    result = rebinning_asymmetry_reducer._rebin_and_sum(raw_data, time)

    scipp.testing.assert_allclose(
        result.data,
        sc.array(
            dims=["tof"],
            values=[1 + 6 + 2 + 7, 3 + 4 + 8 + 9, 5 + 10, 0, 0],
            variances=[1 + 6 + 2 + 7, 3 + 4 + 8 + 9, 5 + 10, 0, 0],
            unit=sc.units.counts,
            dtype="float64",
        ),
    )
    scipp.testing.assert_allclose(result.coords["tof"], rebinning_asymmetry_reducer._time_bin_edges)


def test_rebin_and_sum_with_no_rebinning(asymmetry_reducer):
    raw_data = np.array(
        [
            [1, 2, 3, 4, 5],
            [6, 7, 8, 9, 10],
        ],
        dtype="float32",
    )

    time = sc.array(dims=["tof"], values=[0, 0.5, 1, 1.5, 2, 2.5], unit="ns", dtype="float64")
    result = asymmetry_reducer._rebin_and_sum(raw_data, time)

    scipp.testing.assert_allclose(
        result.data,
        sc.array(
            dims=["tof"],
            values=[1 + 6, 2 + 7, 3 + 8, 4 + 9, 5 + 10],
            variances=[1 + 6, 2 + 7, 3 + 8, 4 + 9, 5 + 10],
            unit=sc.units.counts,
            dtype="float64",
        ),
    )
    scipp.testing.assert_allclose(result.coords["tof"], time)


async def test_asymmetry_reducer(simpledae):
    simpledae.trigger_and_get_specdata = AsyncMock(return_value=None)
    simpledae.reducer._first_det.read_spectrum_dataarray = AsyncMock(return_value=None)

    with patch(
        "ibex_bluesky_core.devices.muon.MuonAsymmetryReducer._calculate_asymmetry",
    ) as calculate_asymmetry_mock:
        calculate_asymmetry_mock.return_value = sc.DataArray(
            data=sc.Variable(
                dims=["tof"],
                values=[0.0, 0.0, 0.0, 0.0, 0.0, 0.0],
                variances=[1, 1, 1, 1, 1, 1],
                unit=sc.units.counts,
                dtype="float64",
            ),
            coords={
                "tof": sc.linspace("tof", start=0, stop=6, num=7, unit=sc.units.ns, dtype="float64")
            },
        )

        await simpledae.reducer.reduce_data(simpledae)

    assert await simpledae.reducer.B.get_value() == pytest.approx(0.0, abs=1e-8)
    assert await simpledae.reducer.A_0.get_value() == pytest.approx(0.0, abs=1e-8)


async def test_asymmetry_reducer_real_data():
    reducer = MuonAsymmetryReducer(
        forward_detectors=np.array([1]),
        backward_detectors=np.array([2]),
        time_bin_edges=sc.linspace("tof", 0, 5, num=20, unit=sc.units.ns, dtype="float64"),
        prefix="UNITTEST:",
    )

    dae = SimpleDae(
        prefix="UNITTEST:",
        reducer=reducer,
        waiter=MEventsWaiter(5000),
        controller=PeriodPerPointController(save_run=False),
    )
    await dae.connect(mock=True)

    dae.trigger_and_get_specdata = AsyncMock(return_value=None)
    dae.reducer._first_det.read_spectrum_dataarray = AsyncMock(return_value=None)

    B = 0.1  # noqa: N806
    A_0 = 1  # noqa: N806
    omega_0 = 0.1
    phi_0 = 0
    lambda_0 = 0.001

    x = np.array(np.linspace(0.5, 19.5, 20))
    y = damped_oscillator(x, B, A_0, omega_0, phi_0, lambda_0)

    with patch(
        "ibex_bluesky_core.devices.muon.MuonAsymmetryReducer._calculate_asymmetry",
    ) as calculate_asymmetry_mock:
        calculate_asymmetry_mock.return_value = sc.DataArray(
            data=sc.Variable(
                dims=["tof"],
                values=y,
                variances=[1] * 20,
                unit=sc.units.counts,
                dtype="float64",
            ),
            coords={
                "tof": sc.linspace(
                    "tof",
                    start=0,
                    stop=20,
                    num=21,
                    unit=sc.units.ns,
                    dtype="float64",
                )
            },
        )

        await dae.reducer.reduce_data(dae)

    assert await dae.reducer.B.get_value() == pytest.approx(B, abs=1e-3)
    assert await dae.reducer.A_0.get_value() == pytest.approx(A_0, abs=1e-3)
    assert await dae.reducer.omega_0.get_value() == pytest.approx(omega_0, abs=1e-3)
    assert await dae.reducer.phi_0.get_value() == pytest.approx(phi_0, abs=1e-3)
    assert await dae.reducer.lambda_0.get_value() == pytest.approx(lambda_0, abs=1e-3)

# pyright: reportMissingParameterType=false
import re
from unittest.mock import AsyncMock, MagicMock, patch

import lmfit
import numpy as np
import pytest
import scipp as sc
import scipp.testing

from ibex_bluesky_core.devices.muon import (
    MuonAsymmetryReducer,
    MuonLifetimeReducer,
    damped_oscillator,
    double_damped_oscillator,
    double_exponential_decay,
)
from ibex_bluesky_core.devices.simpledae import (
    MEventsWaiter,
    PeriodGoodFramesNormalizer,
    PeriodPerPointController,
    SimpleDae,
)

damped_oscillator_model = lmfit.Model(damped_oscillator)
damped_oscillator_params = lmfit.Parameters()
damped_oscillator_params.add("B", 0.0)
damped_oscillator_params.add("A_0", 0.1, min=0)
damped_oscillator_params.add("omega_0", 0.1, min=0)
damped_oscillator_params.add("phi_0", 0.0)
damped_oscillator_params.add("lambda_0", 0.001)

decay_model = lmfit.Model(double_exponential_decay)
decay_model_params = lmfit.Parameters()
decay_model_params.add("n_0", 900.0, min=0)
decay_model_params.add("lambda_0", 8e-4, min=0)
decay_model_params.add("n_1", 120.0, min=0)
decay_model_params.add("lambda_1", 1.2e-4, min=0)


@pytest.fixture
def asymmetry_reducer():
    return MuonAsymmetryReducer(
        forward_detectors=np.array([1]),
        backward_detectors=np.array([2]),
        prefix="UNITTEST:",
        model=damped_oscillator_model,
        fit_parameters=damped_oscillator_params,
    )


@pytest.fixture
def rebinning_asymmetry_reducer():
    return MuonAsymmetryReducer(
        forward_detectors=np.array([1]),
        backward_detectors=np.array([2]),
        time_bin_edges=sc.linspace("tof", 0, 5, num=6, unit=sc.units.ns, dtype="float64"),
        prefix="UNITTEST:",
        model=damped_oscillator_model,
        fit_parameters=damped_oscillator_params,
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


def test_damped_oscillator():
    np.testing.assert_allclose(
        damped_oscillator(
            t=np.array([0, 1, 2, 3, 4, 5], dtype=np.float64),
            B=1,
            A_0=0.0,
            phi_0=0.0,
            omega_0=0.0,
            lambda_0=0.0,
        ),
        np.array([1, 1, 1, 1, 1, 1], dtype=np.float64),
    )


def test_double_damped_oscillator():
    np.testing.assert_allclose(
        double_damped_oscillator(
            t=np.array([0, 1, 2, 3, 4, 5], dtype=np.float64),
            B=1,
            A_0=0.0,
            phi_0=0.0,
            omega_0=0.0,
            lambda_0=0.0,
            A_1=0.0,
            phi_1=0.0,
            omega_1=0.0,
            lambda_1=0.0,
        ),
        np.array([1, 1, 1, 1, 1, 1], dtype=np.float64),
    )


def test_asymmetry_reducer_readable_signals(
    simpledae: SimpleDae[PeriodPerPointController, MEventsWaiter, MuonAsymmetryReducer],
    rebinning_asymmetry_reducer,
):
    assert set(rebinning_asymmetry_reducer.additional_readable_signals(simpledae)) == {
        simpledae.reducer.B,
        simpledae.reducer.B_err,
        simpledae.reducer.A_0,
        simpledae.reducer.A_0_err,
        simpledae.reducer.omega_0,
        simpledae.reducer.omega_0_err,
        simpledae.reducer.phi_0,
        simpledae.reducer.phi_0_err,
        simpledae.reducer.lambda_0,
        simpledae.reducer.lambda_0_err,
    }


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

    # For all-zero data we expect the fit to converge to background = 0 and amplitude = 0.
    assert await simpledae.reducer.B.get_value() == pytest.approx(0.0, abs=1e-8)
    assert await simpledae.reducer.A_0.get_value() == pytest.approx(0.0, abs=1e-8)


async def test_asymmetry_reducer_real_data():
    reducer = MuonAsymmetryReducer(
        forward_detectors=np.array([1]),
        backward_detectors=np.array([2]),
        time_bin_edges=sc.linspace("tof", 0, 5, num=20, unit=sc.units.ns, dtype="float64"),
        prefix="UNITTEST:",
        model=damped_oscillator_model,
        fit_parameters=damped_oscillator_params,
    )

    dae: SimpleDae[PeriodPerPointController, MEventsWaiter, MuonAsymmetryReducer] = SimpleDae(
        prefix="UNITTEST:",
        reducer=reducer,
        waiter=MEventsWaiter(5000),
        controller=PeriodPerPointController(save_run=False),
    )
    await dae.connect(mock=True)

    dae.trigger_and_get_specdata = AsyncMock(return_value=None)
    dae.reducer._first_det.read_spectrum_dataarray = AsyncMock(return_value=None)

    B = 0.1  # ruff:ignore[non-lowercase-variable-in-function]
    A_0 = 1  # ruff:ignore[non-lowercase-variable-in-function]
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

    # Verify that the fitted parameters are the same (or at least similar to) the
    # parameters which we used to generate the test data.
    assert await dae.reducer.B.get_value() == pytest.approx(B, abs=1e-3)
    assert await dae.reducer.A_0.get_value() == pytest.approx(A_0, abs=1e-3)
    assert await dae.reducer.omega_0.get_value() == pytest.approx(omega_0, abs=1e-3)
    assert await dae.reducer.phi_0.get_value() == pytest.approx(phi_0, abs=1e-3)
    assert await dae.reducer.lambda_0.get_value() == pytest.approx(lambda_0, abs=1e-3)


def test_missing_parameters():
    with pytest.raises(ValueError, match=r"Missing parameters: .*"):
        MuonAsymmetryReducer(
            forward_detectors=np.array([1]),
            backward_detectors=np.array([2]),
            time_bin_edges=sc.linspace("tof", 0, 5, num=20, unit=sc.units.ns, dtype="float64"),
            prefix="UNITTEST:",
            model=damped_oscillator_model,
            fit_parameters=lmfit.Parameters(),
        )


def test_calculate_asymmetry(asymmetry_reducer):
    with (
        patch.object(asymmetry_reducer, "_rebin_and_sum") as rebin_sum_mock,
        patch("ibex_bluesky_core.devices.muon.calculate_polarisation") as calculate_asymmetry_mock,
    ):
        fake_da = MagicMock(spec=sc.DataArray)
        rebin_sum_mock.return_value = sc.scalar(value=5.0, variance=10.0)
        asymmetry_reducer._calculate_asymmetry(
            np.array([[0], [0], [0]]), first_spec_dataarray=fake_da
        )

        calculate_asymmetry_mock.assert_called_with(
            sc.scalar(value=5.0, variance=10.5),
            sc.scalar(value=5.0, variance=10.5),
            asymmetry_reducer._alpha,
        )


async def test_if_fit_fails_then_get_error(asymmetry_reducer, simpledae):
    await asymmetry_reducer.connect(mock=True)

    with (
        patch.object(asymmetry_reducer, "_calculate_asymmetry"),
        patch.object(asymmetry_reducer, "_fit_data") as fit_data_mock,
        patch.object(simpledae, "trigger_and_get_specdata"),
        patch.object(asymmetry_reducer._first_det, "read_spectrum_dataarray"),
    ):
        fit_data_mock.return_value = None

        with pytest.raises(
            ValueError,
            match=re.escape(
                "MuonAsymmetryReducer failed to fit asymmetry model to muon data.\n"
                "Check beamline setup."
            ),
        ):
            await asymmetry_reducer.reduce_data(simpledae)


@pytest.fixture
def lifetime_reducer():
    return MuonLifetimeReducer(
        prefix="UNITTEST:",
        detectors=np.array([1, 2]),
        model=decay_model,
        fit_parameters=decay_model_params,
    )


@pytest.fixture
async def simpledae_lt(lifetime_reducer):
    dae = SimpleDae(
        prefix="UNITTEST:",
        reducer=lifetime_reducer,
        waiter=MEventsWaiter(5000),
        controller=PeriodPerPointController(save_run=False),
    )
    await dae.connect(mock=True)
    return dae


def _tof_coord(edges: np.typing.NDArray[np.float64]) -> sc.Variable:
    return sc.array(dims=["tof"], values=edges, unit=sc.units.ns, dtype="float64")


def _mock_summed_counts(values, variances, edges):

    async def _fake_super_reduce_data(self, dae) -> None:  # ruff: ignore[unused-async] Needs to reflect function signatrue of reduce_data
        self.summed_counts = sc.DataArray(
            data=sc.array(
                dims=["tof"],
                values=values,
                variances=variances,
                unit=sc.units.counts,
                dtype="float64",
            ),
            coords={"tof": _tof_coord(edges)},
        )

    return patch.object(PeriodGoodFramesNormalizer, "reduce_data", new=_fake_super_reduce_data)


def test_double_exponential_decay():
    np.testing.assert_allclose(
        double_exponential_decay(
            t=np.array([0.0, 1000.0], dtype=np.float64),
            n_0=2.0,
            lambda_0=1e-3,
            n_1=3.0,
            lambda_1=2e-3,
        ),
        np.array([5.0, 2.0 * np.exp(-1.0) + 3.0 * np.exp(-2.0)], dtype=np.float64),
    )


def test_lifetime_reducer_readable_signals(simpledae_lt, lifetime_reducer):
    assert set(lifetime_reducer.additional_readable_signals(simpledae_lt)) == {
        lifetime_reducer.n_0,
        lifetime_reducer.n_0_err,
        lifetime_reducer.lambda_0,
        lifetime_reducer.lambda_0_err,
        lifetime_reducer.n_1,
        lifetime_reducer.n_1_err,
        lifetime_reducer.lambda_1,
        lifetime_reducer.lambda_1_err,
    }


async def test_reduce_data_fits_summed_counts(simpledae_lt):
    reducer = simpledae_lt.reducer
    edges = np.array([0.0, 1.0, 2.0])

    with (
        _mock_summed_counts(values=[4.0, 6.0], variances=[4.0, 6.0], edges=edges),
        patch.object(reducer, "_fit_data") as fit_data_mock,
    ):
        fit_data_mock.return_value.params = {
            name: type("P", (), {"value": 1.0, "stderr": 0.1})() for name in decay_model.param_names
        }

        await reducer.reduce_data(simpledae_lt)

    # _fit_data was called with the summed/normalized counts
    (data_arg,) = fit_data_mock.call_args.args
    assert data_arg is reducer.summed_counts

    # fitted values were pushed onto signals
    assert await reducer.n_0.get_value() == pytest.approx(1.0)
    assert await reducer.n_0_err.get_value() == pytest.approx(0.1)


async def test_lifetime_reducer_fits_synthetic_data(simpledae_lt):
    reducer = simpledae_lt.reducer

    edges = np.linspace(0.0, 10000.0, num=51, dtype=np.float64)
    centres = (edges[:-1] + edges[1:]) / 2
    counts = double_exponential_decay(
        centres,
        decay_model_params["n_0"],
        decay_model_params["lambda_0"],
        decay_model_params["n_1"],
        decay_model_params["lambda_1"],
    )

    with _mock_summed_counts(values=counts, variances=np.ones_like(counts), edges=edges):
        await reducer.reduce_data(simpledae_lt)

    assert await reducer.n_0.get_value() == pytest.approx(decay_model_params["n_0"], rel=1e-3)
    assert await reducer.lambda_0.get_value() == pytest.approx(
        decay_model_params["lambda_0"], rel=1e-3
    )
    assert await reducer.n_1.get_value() == pytest.approx(decay_model_params["n_1"], rel=1e-3)
    assert await reducer.lambda_1.get_value() == pytest.approx(
        decay_model_params["lambda_1"], rel=1e-3
    )


async def test_if_fit_fails_then_get_error_lt(simpledae_lt):
    reducer = simpledae_lt.reducer
    edges = np.array([0.0, 1.0, 2.0])

    with (
        _mock_summed_counts(values=[0.0, 0.0], variances=[1.0, 1.0], edges=edges),
        patch.object(reducer, "_fit_data") as fit_data_mock,
    ):
        fit_data_mock.return_value = None

        with pytest.raises(
            ValueError,
            match=re.escape("MuonLifetimeReducer failed to fit decay model to muon data."),
        ):
            await reducer.reduce_data(simpledae_lt)

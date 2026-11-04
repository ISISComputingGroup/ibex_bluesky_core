# pyright: reportMissingParameterType=false
import re
from unittest.mock import AsyncMock, MagicMock, patch

import lmfit
import numpy as np
import pytest
import scipp as sc
import scipp.testing
from scipp.testing import assert_identical

from ibex_bluesky_core.devices.muon import (
    MuonAsymmetryReducer,
    MuonLifetimeReducer,
    _create_fit_parameter_signals,
    _fit_and_publish_params,
    _fit_model,
    _muon_fit_readable_signals,
    _rebin_and_sum,
    damped_oscillator,
    double_damped_oscillator,
    muon_lifetime,
)
from ibex_bluesky_core.devices.simpledae import MEventsWaiter, PeriodPerPointController, SimpleDae

damped_oscillator_model = lmfit.Model(damped_oscillator)

damped_oscillator_params = lmfit.Parameters()
damped_oscillator_params.add("B", 0.0)
damped_oscillator_params.add("A_0", 0.1, min=0)
damped_oscillator_params.add("omega_0", 0.1, min=0)
damped_oscillator_params.add("phi_0", 0.0)
damped_oscillator_params.add("lambda_0", 0.001)

lifetime_model = lmfit.Model(muon_lifetime)

lifetime_model_params = lmfit.Parameters()
lifetime_model_params.add("N_0", 900.0, min=0)
lifetime_model_params.add("lambda_0", 8e-4, min=0)
lifetime_model_params.add("N_1", 120.0, min=0)
lifetime_model_params.add("lambda_1", 1.2e-4, min=0)


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


def test_rebin_and_sum():
    raw_data = np.array(
        [
            [1, 2, 3, 4, 5],
            [6, 7, 8, 9, 10],
        ],
        dtype="float32",
    )

    time = sc.array(dims=["tof"], values=[0, 0.5, 1, 1.5, 2, 2.5], unit="ns", dtype="float64")
    time_bin_edges = sc.linspace("tof", 0, 5, num=6, unit=sc.units.ns, dtype="float64")
    result = _rebin_and_sum(raw_data, time, time_bin_edges)

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
    scipp.testing.assert_allclose(result.coords["tof"], time_bin_edges)


def test_rebin_and_sum_with_no_rebinning():
    raw_data = np.array(
        [
            [1, 2, 3, 4, 5],
            [6, 7, 8, 9, 10],
        ],
        dtype="float32",
    )

    time = sc.array(dims=["tof"], values=[0, 0.5, 1, 1.5, 2, 2.5], unit="ns", dtype="float64")
    result = _rebin_and_sum(raw_data, time, None)

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
        patch("ibex_bluesky_core.devices.muon._rebin_and_sum") as rebin_sum_mock,
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
                "MuonAsymmetryReducer failed to fit model to muon data.\nCheck beamline setup."
            ),
        ):
            await asymmetry_reducer.reduce_data(simpledae)


# Shared composite functions


def _linear(t, m, c):
    return m * t + c


def _linear_params():
    params = lmfit.Parameters()
    params.add("m", 0.0)
    params.add("c", 0.0)

    return params


def _linear_fit_data(m=2.0, c=1.0):
    t = np.linspace(0.5, 9.5, 10)
    return sc.DataArray(
        data=sc.array(dims=["tof"], values=m * t + c, variances=[1.0] * 10, unit=sc.units.counts),
        coords={"tof": sc.linspace("tof", 0, 10, num=11, unit=sc.units.ns, dtype="float64")},
    )


def test_create_fit_parameter_signals_sets_signals_and_returns_setters():
    owner = MagicMock(spec=[])
    model = lmfit.Model(_linear)

    setters, error_setters = _create_fit_parameter_signals(owner, model, _linear_params())

    assert set(setters) == {"m", "c"}
    assert set(error_setters) == {"m", "c"}
    for name in ("m", "m_err", "c", "c_err"):
        assert hasattr(owner, name)


def test_create_fit_parameter_signals_missing_parameters():
    params = lmfit.Parameters()
    params.add("m", 0.0)

    with pytest.raises(ValueError, match=r"Missing parameters: \{'c'\}"):
        _create_fit_parameter_signals(MagicMock(spec=[]), lmfit.Model(_linear), params)


def test_fit_muon_model_fits_against_bin_centres():
    result = _fit_model(lmfit.Model(_linear), _linear_params(), _linear_fit_data(2.0, 1.0))

    assert result is not None
    assert result.params["m"].value == pytest.approx(2.0)
    assert result.params["c"].value == pytest.approx(1.0)


def test_fit_muon_model_converts_tof_to_nanoseconds():
    data = _linear_fit_data(2.0, 1.0)
    data.coords["tof"] = data.coords["tof"].to(unit=sc.units.us)

    result = _fit_model(lmfit.Model(_linear), _linear_params(), data)

    assert result is not None
    assert result.params["m"].value == pytest.approx(2.0)
    assert result.params["c"].value == pytest.approx(1.0)


def test_fit_and_publish_params_applies_result():
    fit_result = MagicMock()
    fit_result.params = {
        "m": MagicMock(value=3.0, stderr=0.5),
        "c": MagicMock(value=1.0, stderr=0.2),
    }

    fit_data = MagicMock(return_value=fit_result)
    setters = {"m": MagicMock(), "c": MagicMock()}
    error_setters = {"m": MagicMock(), "c": MagicMock()}
    data = _linear_fit_data()

    _fit_and_publish_params(object(), fit_data, setters, error_setters, data)

    fit_data.assert_called_once_with(data)
    setters["m"].assert_called_once_with(3.0)
    setters["c"].assert_called_once_with(1.0)
    error_setters["m"].assert_called_once_with(0.5)
    error_setters["c"].assert_called_once_with(0.2)


def test_fit_and_publish_params_raises_if_fit_fails():
    class SomeReducer:
        pass

    setters = {"m": MagicMock()}

    with pytest.raises(
        ValueError,
        match=re.escape("SomeReducer failed to fit model to muon data.\nCheck beamline setup."),
    ):
        _fit_and_publish_params(
            SomeReducer(), MagicMock(return_value=None), setters, {}, _linear_fit_data()
        )

    setters["m"].assert_not_called()


def test_muon_fit_readable_signals_returns_values_then_errors():
    owner = MagicMock(spec=[])
    owner.m, owner.m_err, owner.c, owner.c_err = (MagicMock() for _ in range(4))

    signals = _muon_fit_readable_signals(owner, lmfit.Model(_linear))

    assert signals == [owner.m, owner.c, owner.m_err, owner.c_err]


# MuonLifetimeReducer


def _spectrum_with_tof(tof_edges):
    return sc.DataArray(
        data=sc.zeros(dims=["tof"], shape=[tof_edges.sizes["tof"] - 1], unit=sc.units.counts),
        coords={"tof": tof_edges},
    )


@pytest.fixture
def lifetime_reducer():
    return MuonLifetimeReducer(
        prefix="UNITTEST:",
        detectors=np.array([1, 2]),
        fit_parameters=lifetime_model_params,
        model=lifetime_model,
    )


@pytest.fixture
async def lifetime_dae(lifetime_reducer):
    dae = SimpleDae(
        prefix="UNITTEST:",
        reducer=lifetime_reducer,
        waiter=MEventsWaiter(5000),
        controller=PeriodPerPointController(save_run=False),
    )

    await dae.connect(mock=True)

    return dae


def test_muon_lifetime():
    np.testing.assert_allclose(
        muon_lifetime(
            t=np.array([0.0, 1000.0], dtype=np.float64),
            N_0=2.0,
            lambda_0=1e-3,
            N_1=3.0,
            lambda_1=2e-3,
        ),
        np.array([5.0, 2.0 * np.exp(-1.0) + 3.0 * np.exp(-2.0)], dtype=np.float64),
    )


def test_lifetime_reducer_defaults_to_muon_lifetime_model():
    reducer = MuonLifetimeReducer(
        prefix="UNITTEST:", detectors=np.array([1]), model=lifetime_model, fit_parameters=lifetime_model_params
    )

    assert reducer._model.func is muon_lifetime
    assert reducer._time_bin_edges is None

    for name in ("N_0", "N_0_err", "lambda_0", "lambda_0_err", "N_1", "lambda_1_err"):
        assert hasattr(reducer, name)


def test_lifetime_reducer_missing_parameters():
    with pytest.raises(ValueError, match=r"Missing parameters: .*"):
        MuonLifetimeReducer(
            prefix="UNITTEST:", detectors=np.array([1]), model=lifetime_model, fit_parameters=lmfit.Parameters()
        )


def test_lifetime_reducer_creates_detectors(lifetime_reducer):
    assert set(lifetime_reducer.detectors) == {1, 2}
    assert lifetime_reducer._first_det.tof.source == "ca://UNITTEST:DAE:SPEC:0:1:X"


def test_lifetime_reducer_readable_signals(lifetime_dae, lifetime_reducer):
    assert set(lifetime_reducer.additional_readable_signals(lifetime_dae)) == {
        lifetime_reducer.N_0,
        lifetime_reducer.N_0_err,
        lifetime_reducer.lambda_0,
        lifetime_reducer.lambda_0_err,
        lifetime_reducer.N_1,
        lifetime_reducer.N_1_err,
        lifetime_reducer.lambda_1,
        lifetime_reducer.lambda_1_err,
    }


def test_lifetime_reducer_fit_data_delegates(lifetime_reducer):
    data = _linear_fit_data()

    with patch("ibex_bluesky_core.devices.muon._fit_model") as fit_mock:
        result = lifetime_reducer._fit_data(data)

    fit_mock.assert_called_once_with(lifetime_model, lifetime_model_params, data)
    assert result is fit_mock.return_value


@pytest.mark.parametrize(
    "time_bin_edges",
    [None, sc.linspace("tof", 0, 4, num=3, unit=sc.units.ns, dtype="float64")],
)
async def test_lifetime_reducer_reduce_data_normalises_and_fits(lifetime_dae, time_bin_edges):
    reducer = lifetime_dae.reducer
    reducer._time_bin_edges = time_bin_edges
    current_period_data = np.array([[1, 2, 3, 4], [5, 6, 7, 8]])
    tof = sc.linspace("tof", 0, 4, num=5, unit=sc.units.ns, dtype="float64")

    with (
        patch.object(
            lifetime_dae, "trigger_and_get_specdata", AsyncMock(return_value=current_period_data)
        ),
        patch.object(
            reducer._first_det,
            "read_spectrum_dataarray",
            AsyncMock(return_value=_spectrum_with_tof(tof)),
        ),
        patch.object(lifetime_dae.period.good_frames, "get_value", AsyncMock(return_value=2)),
        patch("ibex_bluesky_core.devices.muon._fit_and_publish_params") as publish_mock,
    ):
        await reducer.reduce_data(lifetime_dae)

    publish_mock.assert_called_once()
    owner, fit_data, setters, error_setters, data = publish_mock.call_args.args

    assert owner is reducer
    assert fit_data == reducer._fit_data
    assert setters is reducer._parameter_setters
    assert error_setters is reducer._parameter_error_setters

    expected = _rebin_and_sum(current_period_data, tof, time_bin_edges)
    expected.variances += 0.5
    assert_identical(data, expected / 2)


async def test_lifetime_reducer_real_data():
    reducer = MuonLifetimeReducer(
        prefix="UNITTEST:",
        detectors=np.array([1, 2]),
        fit_parameters=_linear_params(),
        model=lmfit.Model(_linear),
    )

    dae: SimpleDae[PeriodPerPointController, MEventsWaiter, MuonLifetimeReducer] = SimpleDae(
        prefix="UNITTEST:",
        reducer=reducer,
        waiter=MEventsWaiter(5000),
        controller=PeriodPerPointController(save_run=False),
    )

    await dae.connect(mock=True)

    good_frames = 10
    tof = sc.linspace("tof", 0, 10, num=11, unit=sc.units.ns, dtype="float64")
    t = np.linspace(0.5, 9.5, 10)
    per_frame = 1000 * t + 500

    # Split the counts across two spectra, which the reducer should sum back together.
    total = per_frame * good_frames
    current_period_data = np.array([total * 0.25, total * 0.75])

    with (
        patch.object(dae, "trigger_and_get_specdata", AsyncMock(return_value=current_period_data)),
        patch.object(
            reducer._first_det,
            "read_spectrum_dataarray",
            AsyncMock(return_value=_spectrum_with_tof(tof)),
        ),
        patch.object(dae.period.good_frames, "get_value", AsyncMock(return_value=good_frames)),
    ):
        await reducer.reduce_data(dae)

    assert await reducer.m.get_value() == pytest.approx(1000, rel=1e-6)
    assert await reducer.c.get_value() == pytest.approx(500, rel=1e-6)


async def test_lifetime_reducer_fit_fails_raises(lifetime_dae, lifetime_reducer):
    tof = sc.linspace("tof", 0, 4, num=5, unit=sc.units.ns, dtype="float64")

    with (
        patch.object(
            lifetime_dae, "trigger_and_get_specdata", AsyncMock(return_value=np.ones((2, 4)))
        ),
        patch.object(
            lifetime_reducer._first_det,
            "read_spectrum_dataarray",
            AsyncMock(return_value=_spectrum_with_tof(tof)),
        ),
        patch.object(lifetime_dae.period.good_frames, "get_value", AsyncMock(return_value=1)),
        patch.object(lifetime_reducer, "_fit_data", return_value=None),
        pytest.raises(
            ValueError,
            match=re.escape(
                "MuonLifetimeReducer failed to fit model to muon data.\nCheck beamline setup."
            ),
        ),
    ):
        await lifetime_reducer.reduce_data(lifetime_dae)

# pyright: reportMissingParameterType=false
import typing
from unittest import mock
from unittest.mock import patch

import numpy as np
import pytest
import scipp as sc
from lmfit.model import ModelResult
from numpy.ma.testutils import assert_close
from uncertainties import ufloat, unumpy

from ibex_bluesky_core import utils
from ibex_bluesky_core.fitting import Gaussian, Linear
from ibex_bluesky_core.utils import (
    calculate_polarisation,
    centred_pixel,
    get_pv_prefix,
    is_matplotlib_backend_qt,
)


def test_get_pv_prefix():
    with patch("os.getenv") as mock_getenv:
        mock_getenv.return_value = "UNITTEST:MOCK:"
        assert get_pv_prefix() == "UNITTEST:MOCK:"


def test_cannot_get_pv_prefix():
    with patch("os.getenv") as mock_getenv:
        mock_getenv.return_value = None
        with pytest.raises(EnvironmentError, match="MYPVPREFIX environment variable not available"):
            get_pv_prefix()


def test_centred_pixel():
    assert centred_pixel(50, 3) == [47, 48, 49, 50, 51, 52, 53]


@pytest.mark.parametrize("mpl_backend", ["qt5Agg", "qt6Agg", "qtCairo", "something_else"])
def test_is_matplotlib_backend_qt(mpl_backend: str):
    with patch("ibex_bluesky_core.utils.matplotlib.get_backend", return_value=mpl_backend):
        assert is_matplotlib_backend_qt() == ("qt" in mpl_backend)


@pytest.mark.parametrize(
    ("a", "b", "variance_a", "variance_b", "alpha"),
    [
        # Case 1: Symmetric case with equal uncertainties
        (5.0, 3.0, 0.1, 0.1, 1.0),
        # Case 2: Asymmetric case with different uncertainties
        (10.0, 6.0, 0.2, 0.3, 1.0),
        # Case 3: Case with larger values and different uncertainty magnitudes
        (100.0, 60.0, 1.0, 2.0, 1.0),
        # Case 4/5: Case with larger values and alpha != 1
        (100.0, 60.0, 1.0, 2.0, 10),
        (100.0, 60.0, 1.0, 2.0, 0.1),
    ],
)
def test_polarisation_function_calculates_accurately(a, b, variance_a, variance_b, alpha):
    # 'Uncertainties' library ufloat type; a nominal value and an error value
    a_ufloat = ufloat(a, variance_a**0.5)
    b_ufloat = ufloat(b, variance_b**0.5)
    result_ufloat = (a_ufloat - alpha * b_ufloat) / (a_ufloat + alpha * b_ufloat)

    a_scipp = sc.scalar(value=a, variance=variance_a, unit="", dtype="float64")
    b_scipp = sc.scalar(value=b, variance=variance_b, unit="", dtype="float64")
    result_scipp = calculate_polarisation(a_scipp, b_scipp, alpha=alpha)

    assert result_scipp.value == pytest.approx(result_ufloat.n)
    assert result_scipp.variance**0.5 == pytest.approx(result_ufloat.s)


@pytest.mark.parametrize(
    ("a", "b", "variances_a", "variances_b"),
    [
        ([5.0, 10.0, 100.0], [3.0, 6.0, 60.0], [0.1, 0.2, 1.0], [0.1, 0.3, 2.0]),
    ],
)
def test_polarisation_2_arrays(a, b, variances_a, variances_b):
    # 'Uncertainties' library ufloat type; a nominal value and an error value
    a_uarray = unumpy.uarray(a, [v**0.5 for v in variances_a])  # convert variances to std dev
    b_uarray = unumpy.uarray(b, [v**0.5 for v in variances_b])

    # polarisation value, i.e. (a - b) / (a + b)
    polarisation_uarray = (a_uarray - b_uarray) / (a_uarray + b_uarray)

    a_scipp = sc.array(dims="x", values=a, variances=variances_a, unit="", dtype="float64")
    b_scipp = sc.array(dims="x", values=b, variances=variances_b, unit="", dtype="float64")

    result_scipp = calculate_polarisation(a_scipp, b_scipp)

    assert result_scipp.values == pytest.approx(unumpy.nominal_values(polarisation_uarray))
    assert result_scipp.variances**0.5 == pytest.approx(unumpy.std_devs(polarisation_uarray))


def test_polarisation_units_mismatch():
    var_a = sc.scalar(value=1, variance=0.1, unit="m", dtype="float64")
    var_b = sc.scalar(value=1, variance=0.1, unit="u", dtype="float64")

    with pytest.raises(
        expected_exception=ValueError, match=r"The units of a and b are not equivalent."
    ):
        calculate_polarisation(var_a, var_b)


def test_polarisation_arrays_of_different_sizes():
    var_a = sc.array(dims=["x"], values=[1, 2], variances=[0.1, 0.1], unit="m", dtype="float64")
    var_b = sc.array(dims=["x"], values=[1], variances=[0.1], unit="m", dtype="float64")

    with pytest.raises(
        expected_exception=ValueError, match=r"Dimensions/shape of a and b must match."
    ):
        calculate_polarisation(var_a, var_b)


@pytest.mark.parametrize(
    ("values", "errs", "expected_value", "expected_err"),
    [
        ([1.0, 2.0, 3.0], [0.5, 0.6, 0.7], 2.0, 0.35),
        ([1.0, 2.0, 3.0], [0.5, None, 0.5], 2.0, None),
    ],
)
def test_average_model_results_combine_param(
    values: list[float], errs: list[float | None], expected_value: float, expected_err: float | None
):
    actual_value, actual_err = utils._average_values(values, errs)
    assert_close(actual_value, expected_value, decimal=3)

    if expected_err:
        assert_close(actual_err, expected_err, decimal=3)
    else:
        assert not actual_err


def _sum_values(values: list[float], errs: list[float | None]) -> tuple[float, float | None]:
    if any(e is None for e in errs):
        return sum(values), None
    return sum(values), sum(typing.cast("list[float]", errs))


@pytest.mark.parametrize(
    ("m", "c", "expected_m", "expected_c"),
    [
        (
            ([1.0, 2.0, 3.0], [0.5, 0.6, 0.7]),
            ([4.0, 5.0, 6.0], [0.1, 0.2, 0.3]),
            (6.0, 1.8),
            (15.0, 0.6),
        ),
        (
            ([1.0, 2.0, 3.0], [0.5, None, 0.5]),
            ([4.0, 5.0, 6.0], [0.1, 0.2, 0.3]),
            (6.0, None),
            (15.0, 0.6),
        ),
        (
            ([1.0, 2.0, 3.0], [0.5, 0.6, 0.7]),
            ([4.0, 5.0, 6.0], [None, 0.2, 0.3]),
            (6.0, 1.8),
            (15.0, None),
        ),
    ],
)
def test_average_model_results_returns_correct(
    m: tuple[list[float], list[float | None]],
    c: tuple[list[float], list[float | None]],
    expected_m: tuple[float, float | None],
    expected_c: tuple[float, float | None],
):
    m_values, m_errs = m
    c_values, c_errs = c
    expected_m_value, expected_m_err = expected_m
    expected_c_value, expected_c_err = expected_c

    model = Linear.model()
    x = np.array([0.0, 1.0, 2.0, 3.0])

    results = []
    for m_value, m_err, c_value, c_err in zip(m_values, m_errs, c_values, c_errs, strict=True):
        params = model.make_params(c1=m_value, c0=c_value)
        params["c1"].stderr = m_err
        params["c0"].stderr = c_err
        res = ModelResult(model, params)
        res.userkws = {"x": x}
        results.append(res)

    with mock.patch("ibex_bluesky_core.utils._average_values", side_effect=_sum_values):
        avg = utils.average_model_results(results)

    assert isinstance(avg, ModelResult)
    assert avg.model is model

    assert avg.params["c1"].value == pytest.approx(expected_m_value)
    assert avg.params["c0"].value == pytest.approx(expected_c_value)

    if expected_m_err is None:
        assert avg.params["c1"].stderr is None
    else:
        assert avg.params["c1"].stderr == pytest.approx(expected_m_err)

    if expected_c_err is None:
        assert avg.params["c0"].stderr is None
    else:
        assert avg.params["c0"].stderr == pytest.approx(expected_c_err)

    assert avg.best_values == pytest.approx({"c1": expected_m_value, "c0": expected_c_value})
    assert avg.best_fit == pytest.approx(expected_m_value * x + expected_c_value)


def test_average_model_results_missing():
    with pytest.raises(ValueError, match="At least one result is required"):
        utils.average_model_results([])


def test_average_model_results_diff_models():
    modela = Linear.model()
    modelb = Gaussian.model()

    with pytest.raises(ValueError, match="Results must come from the same model"):
        utils.average_model_results(
            [ModelResult(modela, modela.make_params()), ModelResult(modelb, modelb.make_params())]
        )

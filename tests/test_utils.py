# pyright: reportMissingParameterType=false
from unittest.mock import patch

import pytest
import scipp as sc
from uncertainties import ufloat, unumpy

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

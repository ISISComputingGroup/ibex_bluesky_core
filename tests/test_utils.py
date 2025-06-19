# pyright: reportMissingParameterType=false
from unittest.mock import patch

import pytest
import scipp as sc
from uncertainties import ufloat, unumpy

from ibex_bluesky_core.utils import (
    centred_pixel,
    get_pv_prefix,
    is_matplotlib_backend_qt,
    polarisation,
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


# polarisation
@pytest.mark.parametrize(
    ("a", "b", "variance_a", "variance_b"),
    [
        # Case 1: Symmetric case with equal uncertainties
        (5.0, 3.0, 0.1, 0.1),
        # Case 2: Asymmetric case with different uncertainties
        (10.0, 6.0, 0.2, 0.3),
        # Case 3: Case with larger values and different uncertainty magnitudes
        (100.0, 60.0, 1.0, 2.0),
    ],
)
def test_polarisation_function_calculates_accurately(a, b, variance_a, variance_b):
    # 'Uncertainties' library ufloat type; a nominal value and an error value
    a_ufloat = ufloat(a, variance_a)
    b_ufloat = ufloat(b, variance_b)

    # polarisation value, i.e. (a - b) / (a + b)
    polarisation_ufloat = (a_ufloat.n - b_ufloat.n) / (a_ufloat.n + b_ufloat.n)

    # the partial derivatives of a and b, calculated with 'uncertainties' library's ufloat type
    partial_a = (2 * b_ufloat.n) / ((a_ufloat.n + b_ufloat.n) ** 2)
    partial_b = (-2 * a_ufloat.n) / ((a_ufloat.n + b_ufloat.n) ** 2)

    # variance calculated with 'uncertainties' library
    variance = (partial_a**2 * a_ufloat.s) + (partial_b**2 * b_ufloat.s)
    uncertainty = variance**0.5  # uncertainty is sqrt of variance

    # Two scipp scalars, to test our polarisation function
    var_a = sc.scalar(value=a, variance=variance_a, unit="", dtype="float64")
    var_b = sc.scalar(value=b, variance=variance_b, unit="", dtype="float64")
    result_value = polarisation(var_a, var_b)
    result_uncertainy = (result_value.variance) ** 0.5  # uncertainty is sqrt of variance

    assert result_value.value == pytest.approx(polarisation_ufloat)
    assert result_uncertainy == pytest.approx(uncertainty)


# test that arrays are supported
@pytest.mark.parametrize(
    ("a", "b", "variances_a", "variances_b"),
    [
        ([5.0, 10.0, 100.0], [3.0, 6.0, 60.0], [0.1, 0.2, 1.0], [0.1, 0.3, 2.0]),
    ],
)
def test_polarisation_2_arrays(a, b, variances_a, variances_b):
    # 'Uncertainties' library ufloat type; a nominal value and an error value

    a_arr = unumpy.uarray(a, [v**0.5 for v in variances_a])  # convert variances to std dev
    b_arr = unumpy.uarray(b, [v**0.5 for v in variances_b])

    # polarisation value, i.e. (a - b) / (a + b)
    polarisation_ufloat = (a_arr - b_arr) / (a_arr + b_arr)

    var_a = sc.array(dims="x", values=a, variances=variances_a, unit="", dtype="float64")
    var_b = sc.array(dims="x", values=b, variances=variances_b, unit="", dtype="float64")

    result_value = polarisation(var_a, var_b)

    result_uncertainties = (result_value.variances) ** 0.5

    assert result_value.values == pytest.approx(unumpy.nominal_values(polarisation_ufloat))
    assert result_uncertainties == pytest.approx(unumpy.std_devs(polarisation_ufloat))


# test that units don't match
def test_polarisation_units_mismatch():
    var_a = sc.scalar(value=1, variance=0.1, unit="m", dtype="float64")
    var_b = sc.scalar(value=1, variance=0.1, unit="u", dtype="float64")

    with pytest.raises(
        expected_exception=ValueError, match=r"The units of a and b are not equivalent."
    ):
        polarisation(var_a, var_b)


# test that arrays are of unmatching sizes
def test_polarisation_arrays_of_different_sizes():
    var_a = sc.array(dims=["x"], values=[1, 2], variances=[0.1, 0.1], unit="m", dtype="float64")
    var_b = sc.array(dims=["x"], values=[1], variances=[0.1], unit="m", dtype="float64")

    with pytest.raises(
        expected_exception=ValueError, match=r"Dimensions/shape of a and b must match."
    ):
        polarisation(var_a, var_b)

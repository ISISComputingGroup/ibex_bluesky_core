import unittest

import pytest

from ibex_bluesky_core.devices.polarisingdae import polarization
import scipp as sc


# Polarization
@pytest.mark.parametrize(
    ("a", "b", "variance_a", "variance_b", "expected_value", "expected_uncertainty"),
    [
        # Case 1: Symmetric case with equal uncertainties
        (5.0, 3.0, 0.1, 0.1, 0.25, 0.05762215285808055),  # comment where tf this number came from
        # Case 2: Asymmetric case with different uncertainties
        (10.0, 6.0, 0.2, 0.3, 0.25, 0.04764984588117782),
        # Case 3: Case with larger values and different uncertainty magnitudes
        (100.0, 60.0, 1.0, 2.0, 0.25, 0.0120017902310447),
    ],
)
def test_polarization_function_calculates_accurately(
    a, b, variance_a, variance_b, expected_value, expected_uncertainty
):
    var_a = sc.Variable(dims=[], values=a, variances=variance_a, unit="", dtype="float64")
    var_b = sc.Variable(dims=[], values=b, variances=variance_b, unit="", dtype="float64")
    result_value = polarization(var_a, var_b)

    result_uncertainy = (result_value.variance) ** 0.5  # uncertainty is sqrt of variance

    assert result_value == pytest.approx(expected_value)
    assert result_uncertainy == pytest.approx(expected_uncertainty)


# test that arrays are supported
@pytest.mark.parametrize(
    ("a", "b", "variances_a", "variances_b", "expected_values", "expected_uncertainties"),
    [
        # Case 1: Symmetric case with equal uncertainties
        (
            [5.0, 10.0, 100.0],
            [3.0, 6.0, 60.0],
            [0.1, 0.2, 1.0],
            [0.1, 0.3, 2.0],
            [0.25, 0.25, 0.25],
            [0.05762215285808055, 0.04764984588117782, 0.0120017902310447],
        ),
        # These uncertainty numbers were calculated using python's 'uncertainties' library
    ],
)
def test_polarization_2_arrays(
    a, b, variances_a, variances_b, expected_values, expected_uncertainties
):
    var_a = sc.Variable(dims=["x"], values=a, variances=variances_a, unit="")
    var_b = sc.Variable(dims=["x"], values=b, variances=variances_b, unit="")

    result_value = polarization(var_a, var_b)

    result_uncertainties = (result_value.variances) ** 0.5

    assert result_value == pytest.approx(expected_values)
    assert result_uncertainties == pytest.approx(expected_uncertainties)


# test that units don't match
def test_polarization_units_mismatch():
    var_a = sc.Variable(dims=["x"], values=[1], variances=[0.1], unit="m", dtype="float64")
    var_b = sc.Variable(dims=["x"], values=[1], variances=[0.1], unit="u", dtype="float64")

    with pytest.raises(
        expected_exception=ValueError, match=r"The units of a and b are not equivalent."
    ):
        polarization(var_a, var_b)


# test that arrays are of unmatching sizes
def test_polarization_arrays_of_different_sizes():
    var_a = sc.Variable(dims=["x"], values=[1, 2], variances=[0.1, 0.1], unit="m", dtype="float64")
    var_b = sc.Variable(dims=["x"], values=[1], variances=[0.1], unit="m", dtype="float64")

    with pytest.raises(
        expected_exception=ValueError, match=r"Dimensions/shape of a and b must match."
    ):
        polarization(var_a, var_b)


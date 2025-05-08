import unittest
from unittest.mock import MagicMock, AsyncMock

import pytest
from numpy.ma.testutils import assert_equal
from ophyd_async.core import SignalRW, soft_signal_rw

from ibex_bluesky_core.devices.dae._spectra import WavelengthBand, PolarisedWavelengthBand
from ibex_bluesky_core.devices.polarisingdae import (
    polarization,
    PolarisingDae,
    WavelengthBoundedNormalizer,
)
import scipp as sc

from ibex_bluesky_core.devices.simpledae import Controller, Waiter, Reducer


@pytest.fixture
async def wavelength_bounded_normaliser() -> WavelengthBoundedNormalizer:
    reducer = WavelengthBoundedNormalizer(
        prefix="",
        detector_spectra=[1],
        monitor_spectra=[2],
        intervals=[
            sc.array(
                dims=["tof"], values=[0, 300], unit=sc.units.angstrom, dtype="float64"
            ),
            sc.array(
                dims=["tof"], values=[300,9999999999.0], unit=sc.units.angstrom, dtype="float64"
            )
        ],
        total_flight_path_length=sc.scalar(value=10, unit=sc.units.m),
    )
    await reducer.connect(mock=True)
    return reducer


@pytest.fixture
def spectra_bins_easy_to_test() -> sc.DataArray:
    return sc.DataArray(
        data=sc.Variable(
            dims=["tof"],
            values=[1000.0, 2000.0, 3000.0, 2000.0, 1000.0],
            variances=[1000.0, 2000.0, 3000.0, 2000.0, 1000.0],
            unit=sc.units.counts,
            dtype="float64",
        ),
        coords={
            "tof": sc.array(
                dims=["tof"], values=[0, 1, 2, 3, 4, 5], unit=sc.units.us, dtype="float64"
            )
        },
    )


@pytest.fixture
def mock_controller() -> Controller:
    return MagicMock(spec=Controller)


@pytest.fixture
def mock_waiter() -> Waiter:
    return MagicMock(spec=Waiter)


@pytest.fixture
def mock_reducer() -> Reducer:
    return MagicMock(spec=Reducer)


@pytest.fixture
def mock_reducer_up() -> Reducer:
    return MagicMock(spec=Reducer)


@pytest.fixture
def mock_reducer_down() -> Reducer:
    return MagicMock(spec=Reducer)


@pytest.fixture
def flipper() -> SignalRW[float]:
    return soft_signal_rw(float, 0.0)


@pytest.fixture
async def mock_polarising_dae(
    mock_controller: Controller,
    mock_waiter: Waiter,
    mock_reducer: Reducer,
    mock_reducer_up: Reducer,
    mock_reducer_down: Reducer,
    flipper: SignalRW,
) -> PolarisingDae:
    mock_polarising_dae = PolarisingDae(
        prefix="unittest:mock:",
        name="polarisingdae",
        controller=mock_controller,
        waiter=mock_waiter,
        reducer=mock_reducer,
        reducer_up=mock_reducer_up,
        reducer_down=mock_reducer_down,
        flipper=flipper,
        flipper_states=(0.0, 1.0),
    )

    await mock_polarising_dae.connect(mock=True)
    return mock_polarising_dae


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


def test_wavelength_bounded_normalizer_publishes_wavelength_bands(
    mock_polarising_dae: PolarisingDae,
    wavelength_bounded_normaliser: WavelengthBoundedNormalizer,
):
    readables = wavelength_bounded_normaliser.additional_readable_signals(mock_polarising_dae)

    assert wavelength_bounded_normaliser.wavelength_bands == readables


async def test_wavelength_band_setter():
    det_counts = 100
    det_counts_stddev = 0.1
    mon_counts = 200
    mon_counts_stddev = 0.2
    intensity = 0.5
    intensity_stddev = 3.7500000000000005e-06

    wavelength_band = WavelengthBand()
    wavelength_band.setter(
        det_counts=det_counts,
        det_counts_stddev=det_counts_stddev,
        mon_counts=mon_counts,
        mon_counts_stddev=mon_counts_stddev,
        intensity=intensity,
        intensity_stddev=intensity_stddev,
    )

    assert await wavelength_band.det_counts.get_value() == det_counts
    assert await wavelength_band.det_counts_stddev.get_value() == det_counts_stddev
    assert await wavelength_band.mon_counts.get_value() == mon_counts
    assert await wavelength_band.mon_counts_stddev.get_value() == mon_counts_stddev
    assert await wavelength_band.intensity.get_value() == intensity
    assert await wavelength_band.intensity_stddev.get_value() == intensity_stddev


async def test_polarised_wavelength_band_setter():
    polarisation = 1
    polarisation_stddev = 0.5
    polarisation_ratio = 0.1
    polarisation_ratio_stddev = 0.5

    polarised_wavelength_band = PolarisedWavelengthBand()
    polarised_wavelength_band.setter(
        polarisation=polarisation,
        polarisation_stddev=polarisation_stddev,
        polarisation_ratio=polarisation_ratio,
        polarisation_ratio_stddev=polarisation_ratio_stddev,
    )

    assert await polarised_wavelength_band.polarisation.get_value() == polarisation
    assert await polarised_wavelength_band.polarisation_stddev.get_value() == polarisation_stddev
    assert await polarised_wavelength_band.polarisation_ratio.get_value() == polarisation_ratio
    assert await polarised_wavelength_band.polarisation_ratio_stddev.get_value() == polarisation_ratio_stddev

async def test_wavelength_bounded_normalizer():
    pass

    # test that data that goes into wavelength_bounded_normaliser via detectors & monitors device vector
    # is normalised correctly on a per wavelength band basis in reduce data
    # and that setter is called once per wavelength band


async def test_polarising_reducer():
    pass

    # test that data that goes into polarising_reducer via the two reducers wavelength bands subdevices
    # is correctly used to do polarisation on a per wavelength band basis
    # and setter is called per wavelength band


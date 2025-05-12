import math
import re
from unittest.mock import MagicMock, AsyncMock, patch

import pytest
from ophyd_async.core import SignalRW, soft_signal_rw, soft_signal_r_and_setter

from ibex_bluesky_core.devices.dae._spectra import WavelengthBand, PolarisedWavelengthBand
from ibex_bluesky_core.devices.polarisingdae import (
    polarization,
    PolarisingDae,
    WavelengthBoundedNormalizer,
)
import scipp as sc

from ibex_bluesky_core.devices.polarisingdae._reducers import VARIANCE_ADDITION, PolarisingReducer
from ibex_bluesky_core.devices.simpledae import Controller, Waiter, Reducer
from ibex_bluesky_core.devices.simpledae._reducers import sum_spectra, wavelength_bounded_spectra


async def wavelength_bounded_normaliser(sum_funcs) -> WavelengthBoundedNormalizer:
    reducer = WavelengthBoundedNormalizer(
        prefix="",
        detector_spectra=[1],
        monitor_spectra=[2],
        sum_wavelength_bands=sum_funcs
    )
    await reducer.connect(mock=True)
    return reducer

async def get_wavelength_bounded_normaliser() -> WavelengthBoundedNormalizer:
    return await wavelength_bounded_normaliser(
        [wavelength_bounded_spectra(
            bounds=sc.array(
                dims=["tof"],
                values=[0, 9999999999.0],
                unit=sc.units.angstrom,
                dtype="float64"
            ),
            total_flight_path_length=sc.scalar(
                value=10,
                unit=sc.units.m,
                dtype="float64"
            )
        )]
    )


async def get_wavelength_bounded_normaliser_two() -> WavelengthBoundedNormalizer:
    return await wavelength_bounded_normaliser(
        [
            wavelength_bounded_spectra(
                bounds=sc.array(
                    dims=["tof"],
                    values=[0.0, 0.0004],
                    unit=sc.units.angstrom,
                    dtype="float64"
                ),
                total_flight_path_length=sc.scalar(
                    value=10,
                    unit=sc.units.m,
                    dtype="float64",
                )
            ),
            wavelength_bounded_spectra(
                bounds=sc.array(
                    dims=["tof"],
                    values=[0.0004, 9999999999.0],
                    unit=sc.units.angstrom,
                    dtype="float64"
                ),
                total_flight_path_length=sc.scalar(
                    value=10,
                    unit=sc.units.m,
                    dtype="float64",
                )
            )
        ]
    )


@pytest.fixture
async def wavelength_bounded_normaliser_up() -> WavelengthBoundedNormalizer:
    return await get_wavelength_bounded_normaliser()


@pytest.fixture
async def wavelength_bounded_normaliser_down() -> WavelengthBoundedNormalizer:
    return await get_wavelength_bounded_normaliser()


@pytest.fixture
async def wavelength_bounded_normaliser_up_two() -> WavelengthBoundedNormalizer:
    return await get_wavelength_bounded_normaliser_two()


@pytest.fixture
async def wavelength_bounded_normaliser_down_two() -> WavelengthBoundedNormalizer:
    return await get_wavelength_bounded_normaliser_two()


@pytest.fixture
async def polarising_reducer() -> PolarisingReducer:
    return PolarisingReducer(
        [sc.array(dims=["tof"], values=[0, 9999999999.0], unit=sc.units.angstrom, dtype="float64")],
    )


@pytest.fixture
async def polarising_reducer_two() -> PolarisingReducer:
    return PolarisingReducer(
        [sc.array(dims=["tof"], values=[0.0, 0.0004], unit=sc.units.angstrom, dtype="float64"),
        sc.array(dims=["tof"], values=[0.0004, 9999999999.0], unit=sc.units.angstrom, dtype="float64")]
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
async def polarisingdae(
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

    result_uncertainty = (result_value.variance) ** 0.5  # uncertainty is sqrt of variance

    assert result_value == pytest.approx(expected_value)
    assert result_uncertainty == pytest.approx(expected_uncertainty)


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
    polarisingdae: PolarisingDae,
    wavelength_bounded_normaliser_up: WavelengthBoundedNormalizer,
):
    readables = wavelength_bounded_normaliser_up.additional_readable_signals(polarisingdae)

    assert wavelength_bounded_normaliser_up.wavelength_bands == readables


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

async def test_wavelength_bounded_normalizer(polarisingdae: PolarisingDae, wavelength_bounded_normaliser_up_two: WavelengthBoundedNormalizer):
    wavelength_bounded_normaliser_up_two.detectors[1].read_spectrum_dataarray = AsyncMock(

        side_effect=lambda: sc.DataArray(
            data=sc.Variable(
                dims=["tof"],
                values=[1000.0, 2000.0, 3000.0],
                variances=[1000.0, 2000.0, 3000.0],
                unit=sc.units.counts,
            ),
            coords={"tof": sc.array(dims=["tof"], values=[0, 1, 2, 3], unit=sc.units.us, dtype="float64")},
        )
    )
    wavelength_bounded_normaliser_up_two.monitors[2].read_spectrum_dataarray = AsyncMock(
        side_effect=lambda: sc.DataArray(
            data=sc.Variable(
                dims=["tof"],
                values=[4000.0, 5000.0, 6000.0],
                variances=[4000.0, 5000.0, 6000.0],
                unit=sc.units.counts,
            ),
            coords={"tof": sc.array(dims=["tof"], values=[0, 1, 2, 3], unit=sc.units.us, dtype="float64")},
        )
    )

    with patch.object(wavelength_bounded_normaliser_up_two.wavelength_bands[0], 'setter') as setter_mock:

        await wavelength_bounded_normaliser_up_two.reduce_data(dae=polarisingdae)

        setter_mock.assert_called_once_with(
            det_counts=pytest.approx(1022.2273083661819),
            det_counts_stddev=pytest.approx(31.980108010545898),
            mon_counts=pytest.approx(4055.568270915455),
            mon_counts_stddev=pytest.approx(63.68334374791775),
            intensity=pytest.approx(0.2520552583708415),
            intensity_stddev=pytest.approx(0.00882304684703932)
        )

    with patch.object(wavelength_bounded_normaliser_up_two.wavelength_bands[1], 'setter') as setter_mock:

        await wavelength_bounded_normaliser_up_two.reduce_data(dae=polarisingdae)

        setter_mock.assert_called_once_with(
            det_counts=pytest.approx(4977.772691633818),
            det_counts_stddev=pytest.approx(70.55687558015744),
            mon_counts=pytest.approx(10944.431729084547),
            mon_counts_stddev=pytest.approx(104.6156380713923),
            intensity=pytest.approx(0.45482239871856617),
            intensity_stddev=pytest.approx(0.0077757859250577885)
        )


async def test_wavelength_bounded_normaliser_zero_counts(
    polarisingdae: PolarisingDae, wavelength_bounded_normaliser_up: WavelengthBoundedNormalizer
):
    wavelength_bounded_normaliser_up.detectors[1].read_spectrum_dataarray = AsyncMock(
        return_value=sc.DataArray(
            data=sc.Variable(
                dims=["tof"],
                values=[0.0, 0.0, 0.0],
                variances=[0.0, 0.0, 0.0],
                unit=sc.units.counts,
            ),
            coords={"tof": sc.array(dims=["tof"], values=[0, 1, 2, 3], unit=sc.units.us)},
        )
    )
    wavelength_bounded_normaliser_up.monitors[2].read_spectrum_dataarray = AsyncMock(
        return_value=sc.DataArray(
            data=sc.Variable(
                dims=["tof"],
                values=[0.0, 0.0, 0.0],
                variances=[0.0, 0.0, 0.0],
                unit=sc.units.counts,
            ),
            coords={"tof": sc.array(dims=["tof"], values=[0, 1, 2, 3], unit=sc.units.us)},
        )
    )

    with pytest.raises(
        ValueError,
        match=re.escape("Cannot normalize; got zero monitor counts. Check beamline configuration."),
    ):
        await wavelength_bounded_normaliser_up.reduce_data(polarisingdae)


async def test_polarising_reducer(
    polarising_reducer_two: PolarisingReducer,
    wavelength_bounded_normaliser_up_two: WavelengthBoundedNormalizer,
    wavelength_bounded_normaliser_down_two: WavelengthBoundedNormalizer,
    mock_controller: Controller,
    mock_waiter: Waiter,
    flipper: SignalRW,
):

    dae = PolarisingDae(
        prefix="unittest:mock:",
        name="polarisingdae",
        controller=mock_controller,
        waiter=mock_waiter,
        reducer=polarising_reducer_two,
        reducer_up=wavelength_bounded_normaliser_up_two,
        reducer_down=wavelength_bounded_normaliser_down_two,
        flipper=flipper,
        flipper_states=(0.0, 1.0),
    )

    intensity_up_0 = 6000 / 15000
    intensity_up_stddev_0 = (6000 / 15000) * math.sqrt(((6000 + VARIANCE_ADDITION) / 6000 ** 2) + (15000 / 15000 ** 2))
    intensity_down_0 = 7000 / 15000
    intensity_down_stddev_0 = (7000 / 15000) * math.sqrt(((7000 + VARIANCE_ADDITION) / 7000 ** 2) + (15000 / 15000 ** 2))

    intensity_up_sc_0 = sc.scalar(value=intensity_up_0, variance=intensity_up_stddev_0)
    intensity_down_sc_0 = sc.scalar(value=intensity_down_0, variance=intensity_down_stddev_0)

    dae.reducer_up.wavelength_bands[0].intensity, _ = soft_signal_r_and_setter(float, intensity_up_0)
    dae.reducer_up.wavelength_bands[0].intensity_stddev, _ = soft_signal_r_and_setter(float, intensity_up_stddev_0)
    dae.reducer_down.wavelength_bands[0].intensity, _ = soft_signal_r_and_setter(float, intensity_down_0)
    dae.reducer_down.wavelength_bands[0].intensity_stddev, _ = soft_signal_r_and_setter(float, intensity_down_stddev_0)


    intensity_up_1 = 8000 / 15000
    intensity_up_stddev_1 = (8000 / 15000) * math.sqrt(((8000 + VARIANCE_ADDITION) / 8000 ** 2) + (15000 / 15000 ** 2))
    intensity_down_1 = 7000 / 15000
    intensity_down_stddev_1 = (7000 / 15000) * math.sqrt(((7000 + VARIANCE_ADDITION) / 7000 ** 2) + (15000 / 15000 ** 2))

    intensity_up_sc_1 = sc.scalar(value=intensity_up_1, variance=intensity_up_stddev_1)
    intensity_down_sc_1 = sc.scalar(value=intensity_down_1, variance=intensity_down_stddev_1)

    dae.reducer_up.wavelength_bands[1].intensity, _ = soft_signal_r_and_setter(float, intensity_up_1)
    dae.reducer_up.wavelength_bands[1].intensity_stddev, _ = soft_signal_r_and_setter(float, intensity_up_stddev_1)
    dae.reducer_down.wavelength_bands[1].intensity, _ = soft_signal_r_and_setter(float, intensity_down_1)
    dae.reducer_down.wavelength_bands[1].intensity_stddev, _ = soft_signal_r_and_setter(float, intensity_down_stddev_1)

    with patch.object(polarising_reducer_two.wavelength_bands[0], 'setter') as setter_mock_0:
        with patch.object(polarising_reducer_two.wavelength_bands[1], 'setter') as setter_mock_1:

            await polarising_reducer_two.reduce_data(dae=dae)

            polarisation_0 = polarization(
                a=intensity_up_sc_0,
                b=intensity_down_sc_0
            )

            polarisation_ratio_0 = intensity_up_sc_0 / intensity_down_sc_0

            setter_mock_0.assert_called_once_with(
                polarisation=polarisation_0.value,
                polarisation_stddev=polarisation_0.variance,
                polarisation_ratio=polarisation_ratio_0.value,
                polarisation_ratio_stddev=polarisation_ratio_0.variance,
            )

            polarisation_1 = polarization(
                a=intensity_up_sc_1,
                b=intensity_down_sc_1
            )

            polarisation_ratio_1 = intensity_up_sc_1 / intensity_down_sc_1

            setter_mock_1.assert_called_once_with(
                polarisation=polarisation_1.value,
                polarisation_stddev=polarisation_1.variance,
                polarisation_ratio=polarisation_ratio_1.value,
                polarisation_ratio_stddev=polarisation_ratio_1.variance,
            )

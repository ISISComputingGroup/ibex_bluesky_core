import re
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
import scipp as sc
from ophyd_async.core import DeviceVector, SignalRW, soft_signal_rw

from ibex_bluesky_core.devices.polarisingdae import (
    DualRunDae,
    MultiWavelengthBandNormalizer,
    PolarisationReducer,
)
from ibex_bluesky_core.devices.polarisingdae._spectra import (
    _PolarisedWavelengthBand,
    _WavelengthBand,
)
from ibex_bluesky_core.devices.simpledae import (
    VARIANCE_ADDITION,
    Controller,
    Reducer,
    Waiter,
    wavelength_bounded_spectra,
)
from ibex_bluesky_core.utils import polarisation


@pytest.fixture
def wavelength_bounds_single() -> sc.Variable:
    """Single wavelength band spanning the full range."""
    return sc.array(dims=["tof"], values=[0, 9999999999.0], unit=sc.units.angstrom, dtype="float64")


@pytest.fixture
def wavelength_bounds_dual() -> list[sc.Variable]:
    """Two wavelength bands: one for low and one for high wavelengths."""
    return [
        sc.array(dims=["tof"], values=[0.0, 0.0004], unit=sc.units.angstrom, dtype="float64"),
        sc.array(
            dims=["tof"], values=[0.0004, 9999999999.0], unit=sc.units.angstrom, dtype="float64"
        ),
    ]


@pytest.fixture
def flight_path() -> sc.Variable:
    """Total flight path length for the instrument."""
    return sc.scalar(value=10, unit=sc.units.m, dtype="float64")


@pytest.fixture
async def normalizer_single(
    wavelength_bounds_single: sc.Variable, flight_path: sc.Variable
) -> MultiWavelengthBandNormalizer:
    """Create a normalizer with a single wavelength band."""
    reducer = MultiWavelengthBandNormalizer(
        prefix="",
        detector_spectra=[1],
        monitor_spectra=[2],
        sum_wavelength_bands=[
            wavelength_bounded_spectra(
                bounds=wavelength_bounds_single, total_flight_path_length=flight_path
            )
        ],
    )
    await reducer.connect(mock=True)
    return reducer


@pytest.fixture
async def normalizer_dual(
    wavelength_bounds_dual: list[sc.Variable], flight_path: sc.Variable
) -> MultiWavelengthBandNormalizer:
    """Create a normalizer with two wavelength bands."""
    reducer = MultiWavelengthBandNormalizer(
        prefix="",
        detector_spectra=[1],
        monitor_spectra=[2],
        sum_wavelength_bands=[
            wavelength_bounded_spectra(
                bounds=wavelength_bounds_dual[0], total_flight_path_length=flight_path
            ),
            wavelength_bounded_spectra(
                bounds=wavelength_bounds_dual[1], total_flight_path_length=flight_path
            ),
        ],
    )
    await reducer.connect(mock=True)
    return reducer


@pytest.fixture
async def normalizer_dual_alt(
    wavelength_bounds_dual: list[sc.Variable], flight_path: sc.Variable
) -> MultiWavelengthBandNormalizer:
    """Create another normalizer with two wavelength bands."""
    reducer = MultiWavelengthBandNormalizer(
        prefix="",
        detector_spectra=[1],
        monitor_spectra=[2],
        sum_wavelength_bands=[
            wavelength_bounded_spectra(bounds=band, total_flight_path_length=flight_path)
            for band in wavelength_bounds_dual
        ],
    )
    await reducer.connect(mock=True)
    return reducer


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
def mock_reducer_up() -> MultiWavelengthBandNormalizer:
    return MagicMock(spec=MultiWavelengthBandNormalizer)


@pytest.fixture
def mock_reducer_down() -> MultiWavelengthBandNormalizer:
    return MagicMock(spec=MultiWavelengthBandNormalizer)


@pytest.fixture
def flipper() -> SignalRW[float]:
    return soft_signal_rw(float, 0.0)


@pytest.fixture
def polarising_reducer_single(
    wavelength_bounds_single: sc.Variable,
    normalizer_dual: MultiWavelengthBandNormalizer,
    normalizer_dual_alt: MultiWavelengthBandNormalizer,
) -> PolarisationReducer:
    """Create a polarising reducer with a single wavelength band."""
    return PolarisationReducer(
        intervals=[wavelength_bounds_single],
        reducer_up=normalizer_dual,
        reducer_down=normalizer_dual_alt,
    )


@pytest.fixture
def polarising_reducer_dual(
    wavelength_bounds_dual: list[sc.Variable],
    normalizer_dual: MultiWavelengthBandNormalizer,
    normalizer_dual_alt: MultiWavelengthBandNormalizer,
) -> PolarisationReducer:
    """Create a polarising reducer with two wavelength bands."""
    return PolarisationReducer(
        intervals=wavelength_bounds_dual,
        reducer_up=normalizer_dual,
        reducer_down=normalizer_dual_alt,
    )


@pytest.fixture
async def mock_dae(
    mock_controller: Controller,
    mock_waiter: Waiter,
    mock_reducer: Reducer,
    mock_reducer_up: Reducer,
    mock_reducer_down: Reducer,
    flipper: SignalRW[float],
) -> DualRunDae:
    mock_polarising_dae = DualRunDae(
        prefix="unittest:mock:",
        name="mock_dae",
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


@pytest.fixture
async def test_dae(
    mock_controller: Controller,
    mock_waiter: Waiter,
    polarising_reducer_dual: PolarisationReducer,
    normalizer_dual: MultiWavelengthBandNormalizer,
    normalizer_dual_alt: MultiWavelengthBandNormalizer,
    flipper: SignalRW[float],
) -> DualRunDae:
    """Create a test DAE instance with proper mocks and reducers."""
    # Add additional_readable_signals method to controller and waiter mocks
    mock_controller.additional_readable_signals = MagicMock(return_value=[])
    mock_waiter.additional_readable_signals = MagicMock(return_value=[])

    dae = DualRunDae(
        prefix="unittest:mock:",
        name="mock_dae",
        controller=mock_controller,
        waiter=mock_waiter,
        reducer=polarising_reducer_dual,
        reducer_up=normalizer_dual,
        reducer_down=normalizer_dual_alt,
        flipper=flipper,
        flipper_states=(0.0, 1.0),
    )

    await dae.connect(mock=True)
    return dae


def test_wavelength_bounded_normalizer_publishes_wavelength_bands(
    mock_dae: DualRunDae,
    normalizer_single: MultiWavelengthBandNormalizer,
):
    """Test that MultiWavelengthBandNormalizer publishes the correct signals."""
    readables = normalizer_single.additional_readable_signals(mock_dae)

    assert list(normalizer_single._wavelength_bands.values()) == readables


def test_polarising_reducer_publishes_wavelength_bands(
    mock_dae: DualRunDae,
    polarising_reducer_single: PolarisationReducer,
):
    """Test that PolarisationReducer publishes the correct signals."""
    readables = polarising_reducer_single.additional_readable_signals(mock_dae)

    assert list(polarising_reducer_single._wavelength_bands.values()) == readables


async def test_wavelength_band_setter():
    """Test that WavelengthBand correctly sets counts/intensity info."""
    det_counts = 100
    det_counts_stddev = 0.1
    mon_counts = 200
    mon_counts_stddev = 0.2
    intensity = 0.5
    intensity_stddev = 3.7500000000000005e-06

    wavelength_band = _WavelengthBand()
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
    """Test that PolarisedWavelengthBand correctly sets polarisation info."""
    polarisation = 1
    polarisation_stddev = 0.5
    polarisation_ratio = 0.1
    polarisation_ratio_stddev = 0.5

    polarised_wavelength_band = _PolarisedWavelengthBand()
    polarised_wavelength_band.setter(
        polarisation=polarisation,
        polarisation_stddev=polarisation_stddev,
        polarisation_ratio=polarisation_ratio,
        polarisation_ratio_stddev=polarisation_ratio_stddev,
    )

    assert await polarised_wavelength_band.polarisation.get_value() == polarisation
    assert await polarised_wavelength_band.polarisation_stddev.get_value() == polarisation_stddev
    assert await polarised_wavelength_band.polarisation_ratio.get_value() == polarisation_ratio
    assert (
        await polarised_wavelength_band.polarisation_ratio_stddev.get_value()
        == polarisation_ratio_stddev
    )


async def test_wavelength_bounded_normalizer(
    mock_dae: DualRunDae, normalizer_dual: MultiWavelengthBandNormalizer
):
    """Test wavelength bounded normaliser with mock spectrum data."""
    normalizer_dual.detectors[1].read_spectrum_dataarray = AsyncMock(
        side_effect=lambda: sc.DataArray(
            data=sc.Variable(
                dims=["tof"],
                values=[1000.0, 2000.0, 3000.0],
                variances=[1000.0, 2000.0, 3000.0],
                unit=sc.units.counts,
            ),
            coords={
                "tof": sc.array(
                    dims=["tof"], values=[0, 1, 2, 3], unit=sc.units.us, dtype="float64"
                )
            },
        )
    )

    normalizer_dual.monitors[2].read_spectrum_dataarray = AsyncMock(
        side_effect=lambda: sc.DataArray(
            data=sc.Variable(
                dims=["tof"],
                values=[4000.0, 5000.0, 6000.0],
                variances=[4000.0, 5000.0, 6000.0],
                unit=sc.units.counts,
            ),
            coords={
                "tof": sc.array(
                    dims=["tof"], values=[0, 1, 2, 3], unit=sc.units.us, dtype="float64"
                )
            },
        )
    )

    with patch.object(normalizer_dual._wavelength_bands[0], "setter") as low_band_setter:
        with patch.object(normalizer_dual._wavelength_bands[1], "setter") as high_band_setter:
            await normalizer_dual.reduce_data(dae=mock_dae)

            # Test low wavelength band
            low_band_setter.assert_called_once_with(
                det_counts=pytest.approx(1022.2273083661819),
                det_counts_stddev=pytest.approx(31.980108010545898),
                mon_counts=pytest.approx(4055.568270915455),
                mon_counts_stddev=pytest.approx(63.68334374791775),
                intensity=pytest.approx(0.2520552583708415),
                intensity_stddev=pytest.approx(0.00882304684703932),
            )

            # Test high wavelength band
            high_band_setter.assert_called_once_with(
                det_counts=pytest.approx(4977.772691633818),
                det_counts_stddev=pytest.approx(70.55687558015744),
                mon_counts=pytest.approx(10944.431729084547),
                mon_counts_stddev=pytest.approx(104.6156380713923),
                intensity=pytest.approx(0.45482239871856617),
                intensity_stddev=pytest.approx(0.0077757859250577885),
            )


async def test_wavelength_bounded_normaliser_zero_counts(
    mock_dae: DualRunDae, normalizer_single: MultiWavelengthBandNormalizer
):
    """Test that MultiWavelengthBandNormalizer handles zero counts correctly."""

    mock_spectrum = sc.DataArray(
        data=sc.Variable(
            dims=["tof"],
            values=[0.0, 0.0, 0.0],
            variances=[0.0, 0.0, 0.0],
            unit=sc.units.counts,
        ),
        coords={"tof": sc.array(dims=["tof"], values=[0, 1, 2, 3], unit=sc.units.us)},
    )

    normalizer_single.detectors[1].read_spectrum_dataarray = AsyncMock(
        side_effect=lambda: mock_spectrum
    )
    normalizer_single.monitors[2].read_spectrum_dataarray = AsyncMock(
        side_effect=lambda: sc.DataArray(data=mock_spectrum.data, coords=mock_spectrum.coords)
    )

    with pytest.raises(
        ValueError,
        match=re.escape("Cannot normalize; got zero monitor counts in wavelength band 0."),
    ):
        await normalizer_single.reduce_data(mock_dae)


async def test_polarising_reducer(
    test_dae: DualRunDae,
    polarising_reducer_dual: PolarisationReducer,
):
    """Test PolarisationReducer calculates polarisation from up/down data with wavelength bands."""
    # Test data
    test_cases = [
        {
            # First wavelength band
            "up_intensity": 6000 / 15000,
            "up_stddev": (6000 / 15000)
            * ((6000 + VARIANCE_ADDITION) / 6000**2 + 15000 / 15000**2) ** 0.5,
            "down_intensity": 7000 / 15000,
            "down_stddev": (7000 / 15000)
            * ((7000 + VARIANCE_ADDITION) / 7000**2 + 15000 / 15000**2) ** 0.5,
        },
        {
            # Second wavelength band
            "up_intensity": 8000 / 15000,
            "up_stddev": (8000 / 15000)
            * ((8000 + VARIANCE_ADDITION) / 8000**2 + 15000 / 15000**2) ** 0.5,
            "down_intensity": 7000 / 15000,
            "down_stddev": (7000 / 15000)
            * ((7000 + VARIANCE_ADDITION) / 7000**2 + 15000 / 15000**2) ** 0.5,
        },
    ]

    # Configure mock intensity values for up/down states
    for i, case in enumerate(test_cases):
        # Set up mock values for up state
        polarising_reducer_dual.reducer_up()._wavelength_bands[i].intensity.get_value = AsyncMock(
            return_value=case["up_intensity"]
        )
        polarising_reducer_dual.reducer_up()._wavelength_bands[
            i
        ].intensity_stddev.get_value = AsyncMock(return_value=case["up_stddev"])

        # Set up mock values for down state
        polarising_reducer_dual.reducer_down()._wavelength_bands[i].intensity.get_value = AsyncMock(
            return_value=case["down_intensity"]
        )
        polarising_reducer_dual.reducer_down()._wavelength_bands[
            i
        ].intensity_stddev.get_value = AsyncMock(return_value=case["down_stddev"])

    # Test both wavelength bands
    for i, case in enumerate(test_cases):
        with patch.object(polarising_reducer_dual._wavelength_bands[i], "setter") as mock_setter:
            await polarising_reducer_dual.reduce_data(test_dae)

            # Calculate expected values
            intensity_up = sc.scalar(
                value=case["up_intensity"], variance=case["up_stddev"], dtype=float
            )
            intensity_down = sc.scalar(
                value=case["down_intensity"], variance=case["down_stddev"], dtype=float
            )

            expected_polarisation = polarisation(intensity_up, intensity_down)
            expected_ratio = intensity_up / intensity_down

            # Verify setter was called with correct values
            mock_setter.assert_called_once_with(
                polarisation=float(expected_polarisation.value),
                polarisation_stddev=float(expected_polarisation.variance),
                polarisation_ratio=float(expected_ratio.value),
                polarisation_ratio_stddev=float(expected_ratio.variance),
            )


@pytest.mark.parametrize(
    "invalid_intensity",
    [
        (0.0, 1.0),  # Zero up intensity
        (1.0, 0.0),  # Zero down intensity
    ],
)
async def test_polarising_reducer_zero_intensity(
    test_dae: DualRunDae,
    polarising_reducer_dual: PolarisationReducer,
    invalid_intensity: tuple[float, float],
):
    """Test that PolarisationReducer handles zero intensities appropriately."""
    up_intensity, down_intensity = invalid_intensity

    polarising_reducer_dual.reducer_up()._wavelength_bands[0].intensity.get_value = AsyncMock(
        return_value=up_intensity
    )
    polarising_reducer_dual.reducer_down()._wavelength_bands[0].intensity.get_value = AsyncMock(
        return_value=down_intensity
    )

    with pytest.raises(
        ValueError, match="Cannot calculate polarisation; zero intensity sum detected"
    ):
        await polarising_reducer_dual.reduce_data(test_dae)


async def test_polarising_reducer_mismatched_bands(
    test_dae: DualRunDae,
    polarising_reducer_single: PolarisationReducer,
):
    """Test that PolarisationReducer handles mismatched wavelength bands appropriately."""
    # Mock different number of wavelength bands for up and down states

    polarising_reducer_single.reducer_up()._wavelength_bands = DeviceVector(
        children={0: _WavelengthBand(), 1: _WavelengthBand()}
    )
    polarising_reducer_single.reducer_down()._wavelength_bands = DeviceVector(
        children={0: _WavelengthBand()}
    )

    with pytest.raises(ValueError, match="Mismatched number of wavelength bands"):
        await polarising_reducer_single.reduce_data(test_dae)


def test_polarising_reducer_name_properties(polarising_reducer_dual: PolarisationReducer):
    """Test that the polarisation-related name properties return correct values."""
    # Get all the wavelength bands
    bands = list(polarising_reducer_dual._wavelength_bands.values())

    # Test polarisation names
    assert polarising_reducer_dual.polarisation_names == [band.polarisation.name for band in bands]

    # Test polarisation standard deviation names
    assert polarising_reducer_dual.polarisation_stddev_names == [
        band.polarisation_stddev.name for band in bands
    ]

    # Test polarisation ratio names
    assert polarising_reducer_dual.polarisation_ratio == [
        band.polarisation_ratio.name for band in bands
    ]

    # Test polarisation ratio standard deviation names
    assert polarising_reducer_dual.polarisation_ratio_stddev == [
        band.polarisation_ratio_stddev.name for band in bands
    ]

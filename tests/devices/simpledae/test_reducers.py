# pyright: reportMissingParameterType=false
import math
from unittest.mock import AsyncMock

import numpy as np
import pytest
import scipp as sc
from ophyd_async.testing import get_mock_put, set_mock_value

from ibex_bluesky_core.devices.simpledae import SimpleDae
from ibex_bluesky_core.devices.simpledae.reducers import (
    GoodFramesNormalizer,
    MonitorNormalizer,
    PeriodGoodFramesNormalizer,
    PeriodSpecIntegralsReducer,
    ScalarNormalizer,
    tof_bounded_spectra,
    wavelength_bounded_spectra,
)


@pytest.fixture
async def period_good_frames_reducer() -> PeriodGoodFramesNormalizer:
    reducer = PeriodGoodFramesNormalizer(prefix="", detector_spectra=[1, 2])
    await reducer.connect(mock=True)
    return reducer


@pytest.fixture
async def good_frames_reducer() -> GoodFramesNormalizer:
    reducer = GoodFramesNormalizer(prefix="", detector_spectra=[1, 2])
    await reducer.connect(mock=True)
    return reducer


# detector summer sum_spectra/default, monitor summer sum_spectra/default 1, 1
@pytest.fixture
async def monitor_normalizer() -> MonitorNormalizer:
    reducer = MonitorNormalizer(prefix="", detector_spectra=[1], monitor_spectra=[2])
    await reducer.connect(mock=True)
    return reducer


# detector summer sum_spectra/default, monitor summer tof_bounded 1, 2
@pytest.fixture
async def monitor_normalizer_zero_to_one_half_det_norm_mon_tof() -> MonitorNormalizer:
    reducer = MonitorNormalizer(
        prefix="",
        detector_spectra=[1],
        monitor_spectra=[2],
        sum_monitor=tof_bounded_spectra(
            sc.array(dims=["tof"], values=[0.0, 0.5], unit=sc.units.us)
        ),
    )
    await reducer.connect(mock=True)
    return reducer


# detector summer sum_spectra/default, monitor summer wavelength 1, 3
@pytest.fixture
async def monitor_normalizer_det_normal_mon_wavelenth() -> MonitorNormalizer:
    reducer = MonitorNormalizer(
        prefix="",
        detector_spectra=[1],
        monitor_spectra=[2],
        sum_monitor=wavelength_bounded_spectra(
            bounds=sc.array(
                dims=["tof"], values=[0.0, 5.1], unit=sc.units.angstrom, dtype="float64"
            ),
            total_flight_path_length=sc.scalar(value=10.0, unit=sc.units.m),
        ),
    )
    await reducer.connect(mock=True)
    return reducer


# detector summer tof_bounded, monitor summer sum_spectra/default 2, 1
@pytest.fixture
async def monitor_normalizer_zero_to_one_half_det_tof_mon_normal() -> MonitorNormalizer:
    reducer = MonitorNormalizer(
        prefix="",
        detector_spectra=[1],
        monitor_spectra=[2],
        sum_detector=tof_bounded_spectra(
            sc.array(dims=["tof"], values=[0.0, 0.5], unit=sc.units.us)
        ),
    )
    await reducer.connect(mock=True)
    return reducer


# detector summer tof_bounded, monitor summer tof_bounded 2, 2
@pytest.fixture
async def monitor_normalizer_tof_bounded_one_to_three() -> MonitorNormalizer:
    reducer = MonitorNormalizer(
        prefix="",
        detector_spectra=[1],
        monitor_spectra=[2],
        sum_detector=tof_bounded_spectra(
            sc.array(dims=["tof"], values=[0.0, 3.0], unit=sc.units.us)
        ),
        sum_monitor=tof_bounded_spectra(
            sc.array(dims=["tof"], values=[0.0, 3.0], unit=sc.units.us)
        ),
    )
    await reducer.connect(mock=True)
    return reducer


@pytest.fixture
async def monitor_normalizer_tof_bounded_zero_to_one_half() -> MonitorNormalizer:
    reducer = MonitorNormalizer(
        prefix="",
        detector_spectra=[1],
        monitor_spectra=[2],
        sum_detector=tof_bounded_spectra(
            sc.array(dims=["tof"], values=[0.0, 0.5], unit=sc.units.us)
        ),
        sum_monitor=tof_bounded_spectra(
            sc.array(dims=["tof"], values=[0.0, 0.5], unit=sc.units.us)
        ),
    )
    await reducer.connect(mock=True)
    return reducer


# Monitor Normalizer detector summer tof_bounded, monitor summer wavelength 2, 3
@pytest.fixture
async def monitor_normalizer_det_tof_mon_wavelenth() -> MonitorNormalizer:
    reducer = MonitorNormalizer(
        prefix="",
        detector_spectra=[1],
        monitor_spectra=[2],
        sum_detector=tof_bounded_spectra(
            sc.array(dims=["tof"], values=[0.0, 0.5], unit=sc.units.us)
        ),
        sum_monitor=wavelength_bounded_spectra(
            bounds=sc.array(
                dims=["tof"], values=[0.0, 5.1], unit=sc.units.angstrom, dtype="float64"
            ),
            total_flight_path_length=sc.scalar(value=10.0, unit=sc.units.m),
        ),
    )
    await reducer.connect(mock=True)
    return reducer


# Monitor Normalizer detector summer wavelength bounded, monitor summer sum_spectra/default 3, 1
@pytest.fixture
async def monitor_normalizer_det_wavelength_mon_normal() -> MonitorNormalizer:
    reducer = MonitorNormalizer(
        prefix="",
        detector_spectra=[1],
        monitor_spectra=[2],
        sum_detector=wavelength_bounded_spectra(
            bounds=sc.array(
                dims=["tof"], values=[0.0, 5.1], unit=sc.units.angstrom, dtype="float64"
            ),
            total_flight_path_length=sc.scalar(value=10.0, unit=sc.units.m),
        ),
    )
    await reducer.connect(mock=True)
    return reducer


# Monitor Normalizer detector summer wavelength bounded, monitor summer tof_bounded 3, 2
@pytest.fixture
async def monitor_normalizer_det_wavelength_mon_tof() -> MonitorNormalizer:
    reducer = MonitorNormalizer(
        prefix="",
        detector_spectra=[1],
        monitor_spectra=[2],
        sum_detector=wavelength_bounded_spectra(
            bounds=sc.array(
                dims=["tof"], values=[0.0, 5.1], unit=sc.units.angstrom, dtype="float64"
            ),
            total_flight_path_length=sc.scalar(value=10.0, unit=sc.units.m),
        ),
        sum_monitor=tof_bounded_spectra(
            sc.array(dims=["tof"], values=[0.0, 0.5], unit=sc.units.us)
        ),
    )
    await reducer.connect(mock=True)
    return reducer


# Monitor Normalizer detector summer wavelength bounded, monitor summer wavelength 3, 3
@pytest.fixture
async def monitor_normalizer_det_wavelength_mon_wavelength() -> MonitorNormalizer:
    reducer = MonitorNormalizer(
        prefix="",
        detector_spectra=[1],
        monitor_spectra=[2],
        sum_detector=wavelength_bounded_spectra(
            bounds=sc.array(
                dims=["tof"], values=[0.0, 5.1], unit=sc.units.angstrom, dtype="float64"
            ),
            total_flight_path_length=sc.scalar(value=10.0, unit=sc.units.m),
        ),
        sum_monitor=wavelength_bounded_spectra(
            bounds=sc.array(
                dims=["tof"], values=[0.0, 4.5], unit=sc.units.angstrom, dtype="float64"
            ),
            total_flight_path_length=sc.scalar(value=10.0, unit=sc.units.m),
        ),
    )
    await reducer.connect(mock=True)
    return reducer


@pytest.fixture
async def scalar_normalizer_bounded_sum_zero_to_one_half(simpledae: SimpleDae) -> ScalarNormalizer:
    set_mock_value(simpledae.period.good_frames, 1)
    reducer = PeriodGoodFramesNormalizer(
        prefix="",
        detector_spectra=[1, 2],
        sum_detector=tof_bounded_spectra(sc.array(dims=["tof"], values=[0, 0.5], unit=sc.units.us)),
    )
    await reducer.connect(mock=True)
    return reducer


@pytest.fixture
async def scalar_normalizer_bounded_sum_one_to_one(simpledae: SimpleDae) -> ScalarNormalizer:
    set_mock_value(simpledae.period.good_frames, 1)
    reducer = PeriodGoodFramesNormalizer(
        prefix="",
        detector_spectra=[1, 2],
        sum_detector=tof_bounded_spectra(
            sc.array(dims=["tof"], values=[1.0, 1.0], unit=sc.units.us)
        ),
    )
    await reducer.connect(mock=True)
    return reducer


@pytest.fixture
async def scalar_normalizer_bounded_sum_one_to_three_micro_sec(
    simpledae: SimpleDae,
) -> ScalarNormalizer:
    set_mock_value(simpledae.period.good_frames, 1)
    reducer = PeriodGoodFramesNormalizer(
        prefix="",
        detector_spectra=[1, 2],
        sum_detector=tof_bounded_spectra(
            sc.array(dims=["tof"], values=[0.0, 3.0], unit=sc.units.us)
        ),
    )
    await reducer.connect(mock=True)
    return reducer


@pytest.fixture
def spectra_bins_easy_to_test() -> sc.DataArray:
    return sc.DataArray(
        data=sc.Variable(
            dims=["tof"],
            values=[1000.0, 2000.0, 3000.0, 2000.0, 1000.0],
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
def spectra_bins_tof_convert_to_wavelength_easy() -> sc.DataArray:
    return sc.DataArray(
        data=sc.Variable(
            dims=["tof"],
            values=[1000.0, 2000.0, 3000.0, 2000.0, 1000.0],
            unit=sc.units.counts,
            dtype="float64",
        ),
        coords={
            "tof": sc.array(
                dims=["tof"],
                values=[10000, 11000, 12000, 13000, 14000, 15000],
                unit=sc.units.us,
                dtype="float64",
            )
        },
    )


@pytest.fixture
def spectra_bins_tof_convert_to_wavelength_easy_copy() -> sc.DataArray:
    return sc.DataArray(
        data=sc.Variable(
            dims=["tof"],
            values=[1000.0, 2000.0, 3000.0, 2000.0, 1000.0],
            unit=sc.units.counts,
            dtype="float64",
        ),
        coords={
            "tof": sc.array(
                dims=["tof"],
                values=[10000, 11000, 12000, 13000, 14000, 15000],
                unit=sc.units.us,
                dtype="float64",
            )
        },
    )


class FakePeriod:
    def __init__(self):
        self.good_frames = object()


class FakeDae:
    def __init__(self):
        self.good_uah = object()
        self.good_frames = object()
        self.period = FakePeriod()


# Scalar Normalizer


def test_period_good_frames_normalizer_publishes_period_good_frames(
    period_good_frames_reducer: PeriodGoodFramesNormalizer,
):
    fake_dae: SimpleDae = FakeDae()  # type: ignore
    readables = period_good_frames_reducer.additional_readable_signals(fake_dae)
    assert fake_dae.good_uah not in readables
    assert fake_dae.period.good_frames in readables

    assert period_good_frames_reducer.denominator(fake_dae) == fake_dae.period.good_frames


def test_good_frames_normalizer_publishes_good_frames(
    good_frames_reducer: GoodFramesNormalizer,
):
    fake_dae: SimpleDae = FakeDae()  # type: ignore
    readables = good_frames_reducer.additional_readable_signals(fake_dae)
    assert fake_dae.good_uah not in readables
    assert fake_dae.good_frames in readables

    assert good_frames_reducer.denominator(fake_dae) == fake_dae.good_frames


def test_scalar_normalizer_publishes_uncertainties(
    simpledae: SimpleDae,
    good_frames_reducer: GoodFramesNormalizer,
):
    readables = good_frames_reducer.additional_readable_signals(simpledae)
    assert good_frames_reducer.intensity_stddev in readables
    assert good_frames_reducer.det_counts_stddev in readables


async def test_period_good_frames_normalizer(
    simpledae: SimpleDae,
    period_good_frames_reducer: PeriodGoodFramesNormalizer,
):
    set_mock_value(simpledae.period.good_frames, 123)

    period_good_frames_reducer.detectors[1].read_spectrum_dataarray = AsyncMock(
        return_value=sc.DataArray(
            data=sc.Variable(dims=["tof"], values=[1000.0, 2000.0, 3000.0], unit=sc.units.counts),
            coords={"tof": sc.array(dims=["tof"], values=[0, 1, 2, 3])},
        )
    )
    period_good_frames_reducer.detectors[2].read_spectrum_dataarray = AsyncMock(
        return_value=sc.DataArray(
            data=sc.Variable(dims=["tof"], values=[4000.0, 5000.0, 6000.0], unit=sc.units.counts),
            coords={"tof": sc.array(dims=["tof"], values=[0, 1, 2, 3])},
        )
    )

    await period_good_frames_reducer.reduce_data(simpledae)

    det_counts = await period_good_frames_reducer.det_counts.get_value()
    intensity = await period_good_frames_reducer.intensity.get_value()

    assert det_counts == 21000
    # (21000 det counts) / (123 good frames)
    assert intensity == pytest.approx(170.731707317)


async def test_period_good_frames_normalizer_uncertainties(
    simpledae: SimpleDae,
    period_good_frames_reducer: PeriodGoodFramesNormalizer,
):
    set_mock_value(simpledae.period.good_frames, 123)

    period_good_frames_reducer.detectors[1].read_spectrum_dataarray = AsyncMock(
        return_value=sc.DataArray(
            data=sc.Variable(
                dims=["tof"],
                values=[1000.0, 2000.0, 3000.0],
                variances=[1000.0, 2000.0, 3000.0],
                unit=sc.units.counts,
            ),
            coords={"tof": sc.array(dims=["tof"], values=[0, 1, 2, 3])},
        )
    )
    period_good_frames_reducer.detectors[2].read_spectrum_dataarray = AsyncMock(
        return_value=sc.DataArray(
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

    await period_good_frames_reducer.reduce_data(simpledae)

    det_counts_stddev = await period_good_frames_reducer.det_counts_stddev.get_value()
    intensity_stddev = await period_good_frames_reducer.intensity_stddev.get_value()

    assert det_counts_stddev == math.sqrt(21000)
    assert intensity_stddev == pytest.approx(math.sqrt((21000 + (123**2 / 21000)) / 123**2), 1e-4)


async def test_period_good_frames_normalizer_zero_counts(
    simpledae: SimpleDae, period_good_frames_reducer: PeriodGoodFramesNormalizer
):
    period_good_frames_reducer.detectors[1].read_spectrum_dataarray = AsyncMock(
        return_value=sc.DataArray(
            data=sc.Variable(
                dims=["tof"],
                values=[0.0, 0.0, 0.0],
                variances=[0.0, 0.0, 0.0],
                unit=sc.units.counts,
            ),
            coords={
                "tof": sc.array(
                    dims=["tof"], values=[0, 1, 2, 3], unit=sc.units.us, dtype="float64"
                )
            },
        )
    )
    period_good_frames_reducer.detectors[2].read_spectrum_dataarray = AsyncMock(
        return_value=sc.DataArray(
            data=sc.Variable(
                dims=["tof"],
                values=[0.0, 0.0, 0.0],
                variances=[0.0, 0.0, 0.0],
                unit=sc.units.counts,
            ),
            coords={
                "tof": sc.array(
                    dims=["tof"], values=[0, 1, 2, 3], unit=sc.units.us, dtype="float64"
                )
            },
        )
    )

    await period_good_frames_reducer.reduce_data(simpledae)

    det_counts_stddev = await period_good_frames_reducer.det_counts_stddev.get_value()
    intensity_stddev = await period_good_frames_reducer.intensity_stddev.get_value()

    assert det_counts_stddev == 0
    assert intensity_stddev == 0


async def test_scalar_normalizer_tof_bounded_zero_to_one_half(
    simpledae: SimpleDae, scalar_normalizer_bounded_sum_zero_to_one_half: ScalarNormalizer
):
    scalar_normalizer_bounded_sum_zero_to_one_half.detectors[1].read_spectrum_dataarray = AsyncMock(
        return_value=sc.DataArray(
            data=sc.Variable(
                dims=["tof"],
                values=[1000.0, 2000.0, 3000.0],
                variances=[1000.0, 2000.0, 3000.0],
                unit=sc.units.counts,
                dtype="float64",
            ),
            coords={
                "tof": sc.array(
                    dims=["tof"], values=[0, 1, 2, 3], unit=sc.units.us, dtype="float64"
                )
            },
        )
    )
    scalar_normalizer_bounded_sum_zero_to_one_half.detectors[2].read_spectrum_dataarray = AsyncMock(
        return_value=sc.DataArray(
            data=sc.Variable(
                dims=["tof"],
                values=[4000.0, 5000.0, 6000.0],
                variances=[4000.0, 5000.0, 6000.0],
                unit=sc.units.counts,
                dtype="float64",
            ),
            coords={
                "tof": sc.array(
                    dims=["tof"], values=[0, 1, 2, 3], unit=sc.units.us, dtype="float64"
                )
            },
        )
    )

    await scalar_normalizer_bounded_sum_zero_to_one_half.reduce_data(simpledae)

    det_counts = await scalar_normalizer_bounded_sum_zero_to_one_half.det_counts.get_value()
    intensity = await scalar_normalizer_bounded_sum_zero_to_one_half.intensity.get_value()

    assert det_counts == 2500  # 500 from first detector + 2000 from second detector
    assert intensity == pytest.approx(2500)


async def test_scalar_normalizer_tof_bounded_upper_and_lower_bound_equal(
    simpledae: SimpleDae,
    scalar_normalizer_bounded_sum_one_to_one: ScalarNormalizer,
    spectra_bins_easy_to_test: sc.DataArray,
):
    scalar_normalizer_bounded_sum_one_to_one.detectors[1].read_spectrum_dataarray = AsyncMock(
        return_value=spectra_bins_easy_to_test
    )

    scalar_normalizer_bounded_sum_one_to_one.detectors[2].read_spectrum_dataarray = AsyncMock(
        return_value=spectra_bins_easy_to_test
    )

    await scalar_normalizer_bounded_sum_one_to_one.reduce_data(simpledae)

    det_counts = await scalar_normalizer_bounded_sum_one_to_one.det_counts.get_value()
    intensity = await scalar_normalizer_bounded_sum_one_to_one.intensity.get_value()

    assert det_counts == 0  # 0 from first detector + 0 from second detector
    assert intensity == pytest.approx(0)


# Monitor Normalizer


async def test_monitor_normalizer(
    simpledae: SimpleDae, monitor_normalizer: MonitorNormalizer
):  # 1, 1
    monitor_normalizer.detectors[1].read_spectrum_dataarray = AsyncMock(
        return_value=sc.DataArray(
            data=sc.Variable(dims=["tof"], values=[1000.0, 2000.0, 3000.0], unit=sc.units.counts),
            coords={"tof": sc.array(dims=["tof"], values=[0, 1, 2, 3])},
        )
    )
    monitor_normalizer.monitors[2].read_spectrum_dataarray = AsyncMock(
        return_value=sc.DataArray(
            data=sc.Variable(dims=["tof"], values=[4000.0, 5000.0, 6000.0], unit=sc.units.counts),
            coords={"tof": sc.array(dims=["tof"], values=[0, 1, 2, 3])},
        )
    )

    await monitor_normalizer.reduce_data(simpledae)

    det_counts = await monitor_normalizer.det_counts.get_value()
    mon_counts = await monitor_normalizer.mon_counts.get_value()
    intensity = await monitor_normalizer.intensity.get_value()

    assert det_counts == 6000
    assert mon_counts == 15000
    assert intensity == pytest.approx(6000 / 15000)


async def test_monitor_normalizer_zero_counts(
    simpledae: SimpleDae, monitor_normalizer: MonitorNormalizer
):
    monitor_normalizer.detectors[1].read_spectrum_dataarray = AsyncMock(
        return_value=sc.DataArray(
            data=sc.Variable(
                dims=["tof"],
                values=[0.0, 0.0, 0.0],
                variances=[0.0, 0.0, 0.0],
                unit=sc.units.counts,
            ),
            coords={"tof": sc.array(dims=["tof"], values=[0, 1, 2, 3])},
        )
    )
    monitor_normalizer.monitors[2].read_spectrum_dataarray = AsyncMock(
        return_value=sc.DataArray(
            data=sc.Variable(
                dims=["tof"],
                values=[0.0, 0.0, 0.0],
                variances=[0.0, 0.0, 0.0],
                unit=sc.units.counts,
            ),
            coords={"tof": sc.array(dims=["tof"], values=[0, 1, 2, 3])},
        )
    )

    await monitor_normalizer.reduce_data(simpledae)

    det_counts_stddev = await monitor_normalizer.det_counts_stddev.get_value()
    mon_counts_stddev = await monitor_normalizer.mon_counts_stddev.get_value()
    intensity_stddev = await monitor_normalizer.intensity_stddev.get_value()

    assert det_counts_stddev == 0
    assert mon_counts_stddev == 0
    assert intensity_stddev == 0


async def test_monitor_normalizer_uncertainties(
    simpledae: SimpleDae, monitor_normalizer: MonitorNormalizer
):
    monitor_normalizer.detectors[1].read_spectrum_dataarray = AsyncMock(
        return_value=sc.DataArray(
            data=sc.Variable(
                dims=["tof"],
                values=[1000.0, 2000.0, 3000.0],
                variances=[1000.0, 2000.0, 3000.0],
                unit=sc.units.counts,
            ),
            coords={"tof": sc.array(dims=["tof"], values=[0, 1, 2, 3])},
        )
    )
    monitor_normalizer.monitors[2].read_spectrum_dataarray = AsyncMock(
        return_value=sc.DataArray(
            data=sc.Variable(
                dims=["tof"],
                values=[4000.0, 5000.0, 6000.0],
                variances=[4000.0, 5000.0, 6000.0],
                unit=sc.units.counts,
            ),
            coords={"tof": sc.array(dims=["tof"], values=[0, 1, 2, 3])},
        )
    )

    await monitor_normalizer.reduce_data(simpledae)

    det_counts_stddev = await monitor_normalizer.det_counts_stddev.get_value()
    mon_counts_stddev = await monitor_normalizer.mon_counts_stddev.get_value()
    intensity_stddev = await monitor_normalizer.intensity_stddev.get_value()

    assert det_counts_stddev == math.sqrt(6000)
    assert mon_counts_stddev == math.sqrt(15000)
    assert intensity_stddev == pytest.approx(math.sqrt((6000 + (6000**2 / 15000)) / 15000**2), 1e-4)


def test_monitor_normalizer_publishes_raw_and_normalized_counts(
    simpledae: SimpleDae,
    monitor_normalizer: MonitorNormalizer,
):
    readables = monitor_normalizer.additional_readable_signals(simpledae)
    assert monitor_normalizer.intensity in readables
    assert monitor_normalizer.det_counts in readables
    assert monitor_normalizer.mon_counts in readables


def test_monitor_normalizer_publishes_raw_and_normalized_count_uncertainties(
    simpledae: SimpleDae,
    monitor_normalizer: MonitorNormalizer,
):
    readables = monitor_normalizer.additional_readable_signals(simpledae)
    assert monitor_normalizer.intensity_stddev in readables
    assert monitor_normalizer.det_counts_stddev in readables
    assert monitor_normalizer.mon_counts_stddev in readables


async def test_monitor_normalizer_det_sum_normal_mon_sum_tof_bound_(  # 1, 2
    simpledae: SimpleDae,
    monitor_normalizer_zero_to_one_half_det_norm_mon_tof: MonitorNormalizer,
    spectra_bins_easy_to_test: sc.DataArray,
):
    monitor_normalizer_zero_to_one_half_det_norm_mon_tof.detectors[
        1
    ].read_spectrum_dataarray = AsyncMock(return_value=spectra_bins_easy_to_test)

    monitor_normalizer_zero_to_one_half_det_norm_mon_tof.monitors[
        2
    ].read_spectrum_dataarray = AsyncMock(return_value=spectra_bins_easy_to_test)

    await monitor_normalizer_zero_to_one_half_det_norm_mon_tof.reduce_data(simpledae)

    det_counts = await monitor_normalizer_zero_to_one_half_det_norm_mon_tof.det_counts.get_value()
    mon_counts = await monitor_normalizer_zero_to_one_half_det_norm_mon_tof.mon_counts.get_value()
    intensity = await monitor_normalizer_zero_to_one_half_det_norm_mon_tof.intensity.get_value()

    assert det_counts == 9000.0  # 1 + 2 + 3 + 2 + 1 from detector = 9
    assert mon_counts == 500.0  # 1k / 2 = 500 from monitor
    assert intensity == pytest.approx(9000.0 / 500.0)


# test_monitor_normalizer_det_sum_normal_mon_sum_wavelength 1, 3
async def test_monitor_normalizer_det_sum_normal_mon_sum_wavelenth(  # 1, 3
    simpledae: SimpleDae,
    monitor_normalizer_det_normal_mon_wavelenth: MonitorNormalizer,
    spectra_bins_easy_to_test: sc.DataArray,
    spectra_bins_tof_convert_to_wavelength_easy: sc.DataArray,
):
    monitor_normalizer_det_normal_mon_wavelenth.detectors[1].read_spectrum_dataarray = AsyncMock(
        return_value=spectra_bins_easy_to_test
    )

    monitor_normalizer_det_normal_mon_wavelenth.monitors[2].read_spectrum_dataarray = AsyncMock(
        return_value=spectra_bins_tof_convert_to_wavelength_easy
    )

    await monitor_normalizer_det_normal_mon_wavelenth.reduce_data(simpledae)

    det_counts = await monitor_normalizer_det_normal_mon_wavelenth.det_counts.get_value()
    mon_counts = await monitor_normalizer_det_normal_mon_wavelenth.mon_counts.get_value()
    intensity = await monitor_normalizer_det_normal_mon_wavelenth.intensity.get_value()

    assert det_counts == 9000.0  # 1 + 2 + 3 + 2 + 1 from detector = 9
    assert mon_counts == pytest.approx(5675.097)  # angstrom rebinning from monitor
    assert intensity == pytest.approx(9000.0 / 5675.097)


async def test_monitor_normalizer_det_sum_tof_bound_mon_sum_normal(  # 2, 1
    simpledae: SimpleDae,
    monitor_normalizer_zero_to_one_half_det_tof_mon_normal: MonitorNormalizer,
    spectra_bins_easy_to_test: sc.DataArray,
):
    monitor_normalizer_zero_to_one_half_det_tof_mon_normal.detectors[
        1
    ].read_spectrum_dataarray = AsyncMock(return_value=spectra_bins_easy_to_test)

    monitor_normalizer_zero_to_one_half_det_tof_mon_normal.monitors[
        2
    ].read_spectrum_dataarray = AsyncMock(return_value=spectra_bins_easy_to_test)

    await monitor_normalizer_zero_to_one_half_det_tof_mon_normal.reduce_data(simpledae)

    det_counts = await monitor_normalizer_zero_to_one_half_det_tof_mon_normal.det_counts.get_value()
    mon_counts = await monitor_normalizer_zero_to_one_half_det_tof_mon_normal.mon_counts.get_value()
    intensity = await monitor_normalizer_zero_to_one_half_det_tof_mon_normal.intensity.get_value()

    assert det_counts == 500  # 1/2 * 1000 from detector = 500
    assert mon_counts == 9000.0  # 1 + 2 + 3 + 2 + 1 from monitor = 9000
    assert intensity == pytest.approx(500 / 9000.0)


async def test_monitor_normalizer_det_and_mon_summer_tof_bounded(  # 2, 2
    simpledae: SimpleDae,
    monitor_normalizer_tof_bounded_one_to_three: MonitorNormalizer,
    spectra_bins_easy_to_test: sc.DataArray,
):
    monitor_normalizer_tof_bounded_one_to_three.detectors[1].read_spectrum_dataarray = AsyncMock(
        return_value=spectra_bins_easy_to_test
    )

    monitor_normalizer_tof_bounded_one_to_three.monitors[2].read_spectrum_dataarray = AsyncMock(
        return_value=spectra_bins_easy_to_test
    )

    await monitor_normalizer_tof_bounded_one_to_three.reduce_data(simpledae)

    det_counts = await monitor_normalizer_tof_bounded_one_to_three.det_counts.get_value()
    mon_counts = await monitor_normalizer_tof_bounded_one_to_three.mon_counts.get_value()
    intensity = await monitor_normalizer_tof_bounded_one_to_three.intensity.get_value()

    assert det_counts == 6000.0  # 1 + 2 + 3 from detector = 6
    assert mon_counts == 6000.0  # 1 + 2 + 3 from monitor = 6
    assert intensity == pytest.approx(1.0)


async def test_monitor_normalizer_det_mon_summer_tof_bounded_zero_to_one_half(  # 2, 2
    simpledae: SimpleDae, monitor_normalizer_tof_bounded_zero_to_one_half: MonitorNormalizer
):
    monitor_normalizer_tof_bounded_zero_to_one_half.detectors[
        1
    ].read_spectrum_dataarray = AsyncMock(
        return_value=sc.DataArray(
            data=sc.Variable(
                dims=["tof"],
                values=[1000.0, 2000.0, 3000.0],
                variances=[1000.0, 2000.0, 3000.0],
                unit=sc.units.counts,
                dtype="float64",
            ),
            coords={
                "tof": sc.array(
                    dims=["tof"], values=[0, 1, 2, 3], unit=sc.units.us, dtype="float64"
                )
            },
        )
    )
    monitor_normalizer_tof_bounded_zero_to_one_half.monitors[2].read_spectrum_dataarray = AsyncMock(
        return_value=sc.DataArray(
            data=sc.Variable(
                dims=["tof"],
                values=[4000.0, 5000.0, 6000.0],
                variances=[4000.0, 5000.0, 6000.0],
                unit=sc.units.counts,
                dtype="float64",
            ),
            coords={
                "tof": sc.array(
                    dims=["tof"], values=[0, 1, 2, 3], unit=sc.units.us, dtype="float64"
                )
            },
        )
    )

    await monitor_normalizer_tof_bounded_zero_to_one_half.reduce_data(simpledae)

    det_counts = await monitor_normalizer_tof_bounded_zero_to_one_half.det_counts.get_value()
    mon_counts = await monitor_normalizer_tof_bounded_zero_to_one_half.mon_counts.get_value()
    intensity = await monitor_normalizer_tof_bounded_zero_to_one_half.intensity.get_value()

    assert det_counts == 500  # 500 from first detector
    assert mon_counts == 2000  # 2000 half of monitor first bin
    assert intensity == pytest.approx(0.25)  # 500 / 2000


# test_monitor_normalizer_det_sum_tof_bound_mon_sum_wavelength 2, 3
async def test_monitor_normalizer_det_sum_tof_mon_sum_wavelength(  # 2, 3
    simpledae: SimpleDae,
    monitor_normalizer_det_tof_mon_wavelenth: MonitorNormalizer,
    spectra_bins_easy_to_test: sc.DataArray,
    spectra_bins_tof_convert_to_wavelength_easy: sc.DataArray,
):
    monitor_normalizer_det_tof_mon_wavelenth.detectors[1].read_spectrum_dataarray = AsyncMock(
        return_value=spectra_bins_easy_to_test
    )

    monitor_normalizer_det_tof_mon_wavelenth.monitors[2].read_spectrum_dataarray = AsyncMock(
        return_value=spectra_bins_tof_convert_to_wavelength_easy
    )

    await monitor_normalizer_det_tof_mon_wavelenth.reduce_data(simpledae)

    det_counts = await monitor_normalizer_det_tof_mon_wavelenth.det_counts.get_value()
    mon_counts = await monitor_normalizer_det_tof_mon_wavelenth.mon_counts.get_value()
    intensity = await monitor_normalizer_det_tof_mon_wavelenth.intensity.get_value()

    assert det_counts == 500.0  # 1/2 * 1000 from detector = 1000
    assert mon_counts == pytest.approx(5675.097)  # angstrom rebinning from monitor
    assert intensity == pytest.approx(500 / 5675.097)


# test_monitor_normalizer_det_sum_wavelength_mon_sum_normal 3, 1
async def test_monitor_normalizer_det_sum_wavelength_mon_sum_normal(  # 3, 1
    simpledae: SimpleDae,
    monitor_normalizer_det_wavelength_mon_normal: MonitorNormalizer,
    spectra_bins_easy_to_test: sc.DataArray,
    spectra_bins_tof_convert_to_wavelength_easy: sc.DataArray,
):
    monitor_normalizer_det_wavelength_mon_normal.detectors[1].read_spectrum_dataarray = AsyncMock(
        return_value=spectra_bins_tof_convert_to_wavelength_easy
    )

    monitor_normalizer_det_wavelength_mon_normal.monitors[2].read_spectrum_dataarray = AsyncMock(
        return_value=spectra_bins_easy_to_test
    )

    await monitor_normalizer_det_wavelength_mon_normal.reduce_data(simpledae)

    det_counts = await monitor_normalizer_det_wavelength_mon_normal.det_counts.get_value()
    mon_counts = await monitor_normalizer_det_wavelength_mon_normal.mon_counts.get_value()
    intensity = await monitor_normalizer_det_wavelength_mon_normal.intensity.get_value()

    assert det_counts == pytest.approx(5675.097)  # 1 + 2 + 3 + 2 + 1 from detector = 9
    assert mon_counts == 9000.0  # angstrom rebinning from monitor
    assert intensity == pytest.approx(5675.097 / 9000.0)


# test_monitor_normalizer_det_sum_wavelength_mon_sum_tof_bound 3, 2
async def test_monitor_normalizer_det_sum_wavelength_mon_sum_tof(  # 3, 2
    simpledae: SimpleDae,
    monitor_normalizer_det_wavelength_mon_tof: MonitorNormalizer,
    spectra_bins_easy_to_test: sc.DataArray,
    spectra_bins_tof_convert_to_wavelength_easy: sc.DataArray,
):
    monitor_normalizer_det_wavelength_mon_tof.detectors[1].read_spectrum_dataarray = AsyncMock(
        return_value=spectra_bins_tof_convert_to_wavelength_easy
    )

    monitor_normalizer_det_wavelength_mon_tof.monitors[2].read_spectrum_dataarray = AsyncMock(
        return_value=spectra_bins_easy_to_test
    )

    await monitor_normalizer_det_wavelength_mon_tof.reduce_data(simpledae)

    det_counts = await monitor_normalizer_det_wavelength_mon_tof.det_counts.get_value()
    mon_counts = await monitor_normalizer_det_wavelength_mon_tof.mon_counts.get_value()
    intensity = await monitor_normalizer_det_wavelength_mon_tof.intensity.get_value()

    assert det_counts == pytest.approx(5675.097)  # angstrom from detector = 9
    assert mon_counts == 500.0  # tof rebinning from monitor
    assert intensity == pytest.approx(5675.097 / 500.0)


# test_monitor_normalizer_det_sum_wavelength_mon_sum_wavelength 3, 3
async def test_monitor_normalizer_det_sum_wavelength_mon_sum_wavelength(  # 3, 3
    simpledae: SimpleDae,
    monitor_normalizer_det_wavelength_mon_wavelength: MonitorNormalizer,
    spectra_bins_tof_convert_to_wavelength_easy: sc.DataArray,
    spectra_bins_tof_convert_to_wavelength_easy_copy: sc.DataArray,
):
    monitor_normalizer_det_wavelength_mon_wavelength.detectors[
        1
    ].read_spectrum_dataarray = AsyncMock(return_value=spectra_bins_tof_convert_to_wavelength_easy)

    monitor_normalizer_det_wavelength_mon_wavelength.monitors[
        2
    ].read_spectrum_dataarray = AsyncMock(
        return_value=spectra_bins_tof_convert_to_wavelength_easy_copy
    )

    await monitor_normalizer_det_wavelength_mon_wavelength.reduce_data(simpledae)

    det_counts = await monitor_normalizer_det_wavelength_mon_wavelength.det_counts.get_value()
    mon_counts = await monitor_normalizer_det_wavelength_mon_wavelength.mon_counts.get_value()
    intensity = await monitor_normalizer_det_wavelength_mon_wavelength.intensity.get_value()

    assert det_counts == pytest.approx(5675.097)  # angstrom from detector = 9
    assert mon_counts == pytest.approx(1750.057)  # tof rebinning from monitor
    assert intensity == pytest.approx(5675.097 / 1750.057)


@pytest.mark.parametrize("data", [[], [0.0], [0.1, 0.2, 0.3]])
def test_tof_bounded_spectra_bounds_missing_or_too_many(data: list[float]):
    with pytest.raises(expected_exception=ValueError, match="Should contain lower and upper bound"):
        tof_bounded_spectra(sc.array(dims=["tof"], values=data, unit=sc.units.us))


def test_tof_bounded_spectra_missing_tof_in_bounds_dims():
    with pytest.raises(expected_exception=ValueError, match="Should contain tof dims"):
        tof_bounded_spectra(sc.array(dims=[""], values=[0], unit=sc.units.us))


def test_wavelength_bounded_spectra_missing_tof_in_bounds_dims():
    with pytest.raises(expected_exception=ValueError, match="Should contain tof dims"):
        wavelength_bounded_spectra(
            bounds=sc.array(dims=[""], values=[0], unit=sc.units.us),
            total_flight_path_length=sc.scalar(value=0),
        )


@pytest.mark.parametrize("data", [[], [0.0], [0.1, 0.2, 0.3]])
def test_wavelength_bounded_spectra_bounds_missing_or_too_many(data: list[float]):
    with pytest.raises(expected_exception=ValueError, match="Should contain lower and upper bound"):
        wavelength_bounded_spectra(
            bounds=sc.array(dims=["tof"], values=data, unit=sc.units.us),
            total_flight_path_length=sc.scalar(value=100, unit=sc.units.m),
        )


@pytest.mark.parametrize(
    ("current_period", "mon_integrals", "det_integrals"),
    [
        (1, np.array([6], dtype=np.int32), np.array([15, 24, 0], dtype=np.int32)),
        (2, np.array([66], dtype=np.int32), np.array([165, 264, 0], dtype=np.int32)),
    ],
)
async def test_period_spec_integrals_reducer(
    simpledae: SimpleDae, current_period, mon_integrals, det_integrals
):
    reducer = PeriodSpecIntegralsReducer(
        monitors=np.array([1]),
        detectors=np.array([2, 3, 4]),
    )
    await reducer.connect()

    set_mock_value(simpledae.number_of_periods.signal, 2)
    set_mock_value(simpledae.num_spectra, 4)
    set_mock_value(simpledae.num_time_channels, 3)

    set_mock_value(simpledae.period_num, current_period)

    set_mock_value(simpledae.raw_spec_data_nord, 2 * (3 + 1) * (4 + 1))
    set_mock_value(
        simpledae.raw_spec_data,
        np.array(
            [
                # Period 1
                [
                    # Note: every time channel starts with the "junk" time bin zero.
                    # Spectrum 0 (junk data spectrum)
                    [987654321, 9999999, 8888888, 7777777],
                    # Spectrum 1
                    [987654321, 1, 2, 3],
                    # Spectrum 2
                    [987654321, 4, 5, 6],
                    # Spectrum 3
                    [987654321, 7, 8, 9],
                    # Spectrum 4
                    [987654321, 0, 0, 0],
                ],
                # Period 2
                [
                    # Spectrum 0 (junk data spectrum)
                    [987654321, 9999999, 8888888, 7777777],
                    # Spectrum 1
                    [987654321, 11, 22, 33],
                    # Spectrum 2
                    [987654321, 44, 55, 66],
                    # Spectrum 3
                    [987654321, 77, 88, 99],
                    # Spectrum 4
                    [987654321, 0, 0, 0],
                ],
            ]
        ),
    )

    await reducer.reduce_data(simpledae)

    get_mock_put(simpledae.raw_spec_data_proc).assert_called_with(1, wait=True)

    np.testing.assert_equal(await reducer.mon_integrals.get_value(), mon_integrals)
    np.testing.assert_equal(await reducer.det_integrals.get_value(), det_integrals)


def test_period_spec_integrals_reducer_publishes_signals(simpledae: SimpleDae):
    reducer = PeriodSpecIntegralsReducer(detectors=np.array([]), monitors=np.array([]))
    assert reducer.mon_integrals in reducer.additional_readable_signals(simpledae)
    assert reducer.det_integrals in reducer.additional_readable_signals(simpledae)

    np.testing.assert_equal(reducer.detectors, np.array([]))
    np.testing.assert_equal(reducer.monitors, np.array([]))

import math
from unittest.mock import AsyncMock

import pytest
import scipp as sc
from ophyd_async.core import set_mock_value

from ibex_bluesky_core.devices.simpledae import SimpleDae
from ibex_bluesky_core.devices.simpledae.reducers import (
    GoodFramesNormalizer,
    MonitorNormalizer,
    PeriodGoodFramesNormalizer,
    ScalarNormalizer
)
from ibex_bluesky_core.devices.simpledae.reducers import tof_bounded_spectra


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


@pytest.fixture
async def monitor_normalizer() -> MonitorNormalizer:
    reducer = MonitorNormalizer(prefix="", detector_spectra=[1], monitor_spectra=[2])
    await reducer.connect(mock=True)
    return reducer


@pytest.fixture
async def scalar_normalizer_bounded_sum_zero_to_one_half(simpledae: SimpleDae) -> ScalarNormalizer:
    set_mock_value(simpledae.period.good_frames, 1)
    reducer = PeriodGoodFramesNormalizer(prefix="", detector_spectra=[1,2], summer=tof_bounded_spectra(sc.array(dims=["tof"], values=[0, 0.5], unit=sc.units.us)))
    await reducer.connect(mock=True)
    return reducer


@pytest.fixture
async def scalar_normalizer_bounded_sum_one_to_one(simpledae: SimpleDae) -> ScalarNormalizer:
    set_mock_value(simpledae.period.good_frames, 1)
    reducer = PeriodGoodFramesNormalizer(prefix="", detector_spectra=[1,2], summer=tof_bounded_spectra(sc.array(dims=["tof"], values=[1.0, 1.0], unit=sc.units.us)))
    await reducer.connect(mock=True)
    return reducer    
                                                                                                                          

@pytest.fixture
async def spectra_bins_easy_to_test() -> sc.DataArray:
    return sc.DataArray(
            data=sc.Variable(dims=["tof"], values=[1000.0, 2000.0, 3000.0, 2000.0, 1000.0], unit=sc.units.counts, dtype="float64"),
            coords={"tof": sc.array(dims=["tof"], values=[0, 1, 2, 3, 4, 5], unit=sc.units.us, dtype="float64")},
    )


@pytest.fixture
async def scalar_normalizer_unbounded_sum(simpledae: SimpleDae) -> ScalarNormalizer:
    set_mock_value(simpledae.period.good_frames, 1)
    reducer = PeriodGoodFramesNormalizer(prefix="", detector_spectra=[1,2], summer=tof_bounded_spectra(sc.array(dims=["tof"], values=[], unit=sc.units.us)))
    await reducer.connect(mock=True)
    return reducer


class FakePeriod:
    def __init__(self):
        self.good_frames = object()


class FakeDae:
    def __init__(self):
        self.good_uah = object()
        self.good_frames = object()
        self.period = FakePeriod()


# Scalar Normalizer


async def test_period_good_frames_normalizer_publishes_period_good_frames(
    period_good_frames_reducer: PeriodGoodFramesNormalizer,
):
    fake_dae: SimpleDae = FakeDae()  # type: ignore
    readables = period_good_frames_reducer.additional_readable_signals(fake_dae)
    assert fake_dae.good_uah not in readables
    assert fake_dae.period.good_frames in readables

    assert period_good_frames_reducer.denominator(fake_dae) == fake_dae.period.good_frames


async def test_good_frames_normalizer_publishes_good_frames(
    good_frames_reducer: GoodFramesNormalizer,
):
    fake_dae: SimpleDae = FakeDae()  # type: ignore
    readables = good_frames_reducer.additional_readable_signals(fake_dae)
    assert fake_dae.good_uah not in readables
    assert fake_dae.good_frames in readables

    assert good_frames_reducer.denominator(fake_dae) == fake_dae.good_frames


async def test_scalar_normalizer_publishes_uncertainties(
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
            coords={"tof": sc.array(dims=["tof"], values=[0, 1, 2, 3], unit=sc.units.us, dtype="float64")},
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
            coords={"tof": sc.array(dims=["tof"], values=[0, 1, 2, 3], unit=sc.units.us, dtype="float64")},
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
            coords={"tof": sc.array(dims=["tof"], values=[0, 1, 2, 3], unit=sc.units.us, dtype="float64")},
        )
    )

    await period_good_frames_reducer.reduce_data(simpledae)

    det_counts_stddev = await period_good_frames_reducer.det_counts_stddev.get_value()
    intensity_stddev = await period_good_frames_reducer.intensity_stddev.get_value()

    assert det_counts_stddev == 0
    assert intensity_stddev == 0


# Monitor Normalizer


async def test_monitor_normalizer(simpledae: SimpleDae, monitor_normalizer: MonitorNormalizer):
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


async def test_monitor_normalizer_publishes_raw_and_normalized_counts(
    simpledae: SimpleDae,
    monitor_normalizer: MonitorNormalizer,
):
    readables = monitor_normalizer.additional_readable_signals(simpledae)
    assert monitor_normalizer.intensity in readables
    assert monitor_normalizer.det_counts in readables
    assert monitor_normalizer.mon_counts in readables


async def test_monitor_normalizer_publishes_raw_and_normalized_count_uncertainties(
    simpledae: SimpleDae,
    monitor_normalizer: MonitorNormalizer,
):
    readables = monitor_normalizer.additional_readable_signals(simpledae)
    assert monitor_normalizer.intensity_stddev in readables
    assert monitor_normalizer.det_counts_stddev in readables
    assert monitor_normalizer.mon_counts_stddev in readables

async def test_tof_bounded_spectra_half_of_first_bin_rebinned_correctly(
    simpledae: SimpleDae,
    scalar_normalizer_bounded_sum_zero_to_one_half: ScalarNormalizer
    ):

    scalar_normalizer_bounded_sum_zero_to_one_half.detectors[1].read_spectrum_dataarray = AsyncMock(
        return_value=sc.DataArray(
            data=sc.Variable(
                dims=["tof"],
                values=[1000.0, 2000.0, 3000.0],
                variances=[1000.0, 2000.0, 3000.0],
                unit=sc.units.counts,
                dtype="float64"
            ),
            coords={"tof": sc.array(dims=["tof"], values=[0, 1, 2, 3], unit=sc.units.us,
                dtype="float64")},
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
            coords={"tof": sc.array(dims=["tof"], values=[0, 1, 2, 3], unit=sc.units.us,
                dtype="float64")},
        )
    )

    await scalar_normalizer_bounded_sum_zero_to_one_half.reduce_data(simpledae)

    det_counts = await scalar_normalizer_bounded_sum_zero_to_one_half.det_counts.get_value()
    intensity = await scalar_normalizer_bounded_sum_zero_to_one_half.intensity.get_value()

    assert det_counts == 2500 # 500 from first detector + 2000 from second detector
    assert intensity == pytest.approx(2500)


async def test_tof_bounded_spectra_upper_and_lower_bound_equal(
    simpledae: SimpleDae,
    scalar_normalizer_bounded_sum_one_to_one: ScalarNormalizer,
    spectra_bins_easy_to_test: sc.DataArray
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

    assert det_counts == 0 # 500 from first detector + 2000 from second detector
    assert intensity == pytest.approx(0)


async def test_tof_bounded_spectra_no_upper_bound(
    simpledae: SimpleDae,
    scalar_normalizer_unbounded_sum: ScalarNormalizer,
    spectra_bins_easy_to_test: sc.DataArray
):
    scalar_normalizer_unbounded_sum.detectors[1].read_spectrum_dataarray = AsyncMock(
        return_value=spectra_bins_easy_to_test
    )

    scalar_normalizer_unbounded_sum.detectors[2].read_spectrum_dataarray = AsyncMock(
        return_value=spectra_bins_easy_to_test
    )

    await scalar_normalizer_unbounded_sum.reduce_data(simpledae)

    det_counts = await scalar_normalizer_unbounded_sum.det_counts.get_value()
    intensity = await scalar_normalizer_unbounded_sum.intensity.get_value()

    assert det_counts == 9000.0 # 1 + 2 + 3 + 2 + 1 thousand = 9 thousand
    assert intensity == pytest.approx(9000.0)
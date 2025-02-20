"""Muon scan that uses two DAEs to scan a magnet."""

from collections.abc import Generator

import bluesky.plans as bp
import matplotlib.pyplot as plt
from bluesky.callbacks import LiveFitPlot, LiveTable
from bluesky.preprocessors import subs_decorator
from bluesky.utils import Msg
from ibex_bluesky_core.callbacks import LiveFitLogger
from ophyd_async.plan_stubs import ensure_connected

from ibex_bluesky_core.callbacks.fitting import LiveFit
from ibex_bluesky_core.callbacks.fitting.fitting_utils import Gaussian
from ibex_bluesky_core.callbacks.plotting import LivePlot
from ibex_bluesky_core.devices.block import block_rw_rbv, BlockWriteConfig
from ibex_bluesky_core.devices.simpledae import SimpleDae
from ibex_bluesky_core.devices.simpledae.controllers import (
    RunPerPointController,
)
from ibex_bluesky_core.devices.simpledae.reducers import (
    PeriodGoodFramesNormalizer,
)
from ibex_bluesky_core.devices.simpledae.waiters import GoodFramesWaiter
from ibex_bluesky_core.plan_stubs import call_qt_aware

from ibex_bluesky_core.callbacks.file_logger import HumanReadableFileCallback


def two_dae_scan(
    magnet_1_block,
    start_1,
    stop_1,
    magnet_2_block,
    start_2,
    stop_2,
    num,
    frames=500,
    save_run=True,
    magnet_tolerance=0.01,
    magnet_settle_time=1,
    dae_1_prefix="IN:ARGUS:",
    dae_2_prefix="IN:CHRONUS:",
    spectra_total_1=96,
    spectra_total_2=32,
) -> Generator[Msg, None, None]:
    """Scan a block using two DAEs and two magnets."""

    def check_within_tolerance(setpoint: float, actual: float) -> bool:
        return setpoint - magnet_tolerance <= actual <= setpoint + magnet_tolerance

    magnet_1 = block_rw_rbv(
        float,
        magnet_1_block,
        write_config=BlockWriteConfig(
            settle_time_s=magnet_settle_time, set_success_func=check_within_tolerance
        ),
    )

    magnet_2 = block_rw_rbv(
        float,
        magnet_2_block,
        write_config=BlockWriteConfig(
            settle_time_s=magnet_settle_time, set_success_func=check_within_tolerance
        ),
    )

    controller_1 = RunPerPointController(save_run=save_run)
    waiter_1 = GoodFramesWaiter(frames)
    reducer_1 = PeriodGoodFramesNormalizer(
        prefix=dae_1_prefix,
        detector_spectra=[i for i in range(1, spectra_total_1 + 1)],
    )

    dae_1 = SimpleDae(
        prefix=dae_1_prefix,
        controller=controller_1,
        waiter=waiter_1,
        reducer=reducer_1,
        name="dae_1",
    )

    controller_2 = RunPerPointController(save_run=save_run)
    waiter_2 = GoodFramesWaiter(frames)
    reducer_2 = PeriodGoodFramesNormalizer(
        prefix=dae_2_prefix,
        detector_spectra=[i for i in range(1, spectra_total_2 + 1)],
    )

    dae_2 = SimpleDae(
        prefix=dae_2_prefix,
        controller=controller_2,
        waiter=waiter_2,
        reducer=reducer_2,
        name="dae_2",
    )

    _, ax = yield from call_qt_aware(plt.subplots)

    lf_1 = LiveFit(
        Gaussian().fit(),
        y=reducer_1.intensity.name,
        x=magnet_1.name,
        yerr=reducer_1.intensity_stddev.name,
    )
    lf_2 = LiveFit(
        Gaussian().fit(),
        y=reducer_2.intensity.name,
        x=magnet_1.name,
        yerr=reducer_2.intensity_stddev.name,
    )

    yield from ensure_connected(magnet_1, magnet_2, dae_1, dae_2, force_reconnect=True)

    @subs_decorator(
        [
            LiveFitPlot(livefit=lf_1, ax=ax),
            LiveFitPlot(livefit=lf_2, ax=ax),
            LivePlot(
                y=reducer_1.intensity.name,
                x=magnet_1.name,
                marker="x",
                linestyle="none",
                ax=ax,
                yerr=reducer_1.intensity_stddev.name,
            ),
            LivePlot(
                y=reducer_2.intensity.name,
                x=magnet_1.name,
                marker="x",
                linestyle="none",
                ax=ax,
                yerr=reducer_2.intensity_stddev.name,
            ),
            LiveTable(
                [
                    magnet_1.name,
                    magnet_2.name,
                    controller_1.run_number.name,
                    reducer_1.intensity.name,
                    reducer_1.intensity_stddev.name,
                    reducer_1.det_counts.name,
                    reducer_1.det_counts_stddev.name,
                    dae_1.good_frames.name,
                    controller_2.run_number.name,
                    reducer_2.intensity.name,
                    reducer_2.intensity_stddev.name,
                    reducer_2.det_counts.name,
                    reducer_2.det_counts_stddev.name,
                    dae_2.good_frames.name,
                ]
            ),
            HumanReadableFileCallback(
                fields=[
                    magnet_1.name,
                    magnet_2.name,
                    controller_1.run_number.name,
                    reducer_1.intensity.name,
                    reducer_1.intensity_stddev.name,
                    reducer_1.det_counts.name,
                    reducer_1.det_counts_stddev.name,
                    dae_1.good_frames.name,
                    controller_2.run_number.name,
                    reducer_2.intensity.name,
                    reducer_2.intensity_stddev.name,
                    reducer_2.det_counts.name,
                    reducer_2.det_counts_stddev.name,
                    dae_2.good_frames.name,
                ]
            ),
            LiveFitLogger(
                lf_1,
                x=magnet_1.name,
                y=reducer_1.intensity.name,
                yerr=reducer_1.intensity_stddev.name,
                postfix="lf_1",
            ),
            LiveFitLogger(
                lf_2,
                x=magnet_1.name,
                y=reducer_2.intensity.name,
                yerr=reducer_2.intensity_stddev.name,
                postfix="lf_2",
            ),
        ]
    )
    def _inner() -> Generator[Msg, None, None]:
        yield from bp.scan(
            [dae_2, dae_1], magnet_1, start_1, stop_1, magnet_2, start_2, stop_2, num=num
        )
        print(lf_1.result.fit_report())
        print(lf_2.result.fit_report())

    yield from _inner()

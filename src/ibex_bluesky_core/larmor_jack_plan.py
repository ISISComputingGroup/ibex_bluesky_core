"""Spin-echo techniques for use on LARMOR."""

from collections.abc import Generator
from dataclasses import dataclass, field
from pathlib import Path

import lmfit
import scipp as sc
from bluesky import plan_stubs as bps
from bluesky.callbacks import CallbackBase, LiveTable
from bluesky.plans import scan
from bluesky.preprocessors import subs_decorator
from bluesky.utils import Msg
from lmfit import Parameter
from matplotlib import pyplot as plt
from matplotlib.axes import Axes
from ophyd_async.plan_stubs import ensure_connected

from ibex_bluesky_core.callbacks import (
    ChainedLiveFit,
    HumanReadableFileCallback,
    LiveFitLogger,
    LivePlot,
)
from ibex_bluesky_core.devices import isis_epics_signal_rw
from ibex_bluesky_core.devices.block import BlockWriteConfig, block_rw
from ibex_bluesky_core.devices.dae import (
    DaeSettingsData,
    DaeTCBSettingsData,
    TimeRegime,
    TimeRegimeRow,
)
from ibex_bluesky_core.devices.polarisingdae import polarising_dae
from ibex_bluesky_core.fitting import DampedOsc, FitMethod
from ibex_bluesky_core.plan_stubs import call_qt_aware


def _get_detector_i(detector: int | str) -> int:
    """Get detector index from name."""
    if isinstance(detector, int):
        return detector

    elif detector == "alanis":
        return 12

    elif detector == "scruffy":
        return 13

    else:
        raise ValueError("Detector not found.")


@dataclass
class EchoScanConfig:
    """Configuration for echo scan."""

    axis: str
    start: float
    stop: float
    num_points: int = 21
    wavelength_bounds: list[list[float]] = field(
        default_factory=lambda: [[222, 666], [222, 370], [370, 518], [518, 666]]
    )
    frames: int = 200
    flight_path_length_m: float = 10
    detector: int | str = "alanis"
    monitor: int = 2
    flipper: str = "IN:LARMOR:SPINFLIPPER_01:FLIPSTATE"
    flipper_states: list[float] = field(default_factory=lambda: [1.0, 0.0])
    dae_settings: DaeSettingsData | None = None
    tcb_settings: DaeTCBSettingsData | None = None


@dataclass
class AutoTuneConfig:
    """Configuration for auto tuning."""

    confidence: float = 0.5
    model: FitMethod | None = None
    param: str = "center"


def _callbacks_init(
    config: EchoScanConfig,
    model: FitMethod,
    polarisation_names: list[str],
    polarisation_stddev_names: list[str],
    axis_dev_name: str,
    axes: list[Axes],
) -> tuple[ChainedLiveFit, list[CallbackBase]]:
    """Initialise callbacks for echoscan_axis_ib."""
    spinecho_cb = ChainedLiveFit(
        method=model,
        y=polarisation_names,
        yerr=polarisation_stddev_names,
        x=axis_dev_name,
        ax=list(axes),
    )

    plots_cb = [
        LivePlot(y=polarisation_names[i], x=axis_dev_name, marker="x", linestyle="none", ax=axes[i])
        for i in range(len(config.wavelength_bounds))
    ]

    measured_fields = [axis_dev_name, *polarisation_names, *polarisation_stddev_names]

    table_cb = LiveTable(measured_fields)
    hrfile_cb = HumanReadableFileCallback(
        measured_fields, output_dir=Path(r"C:\temp")
    )  # change this

    lflogs_cb = [
        LiveFitLogger(
            livefit=spinecho_cb.live_fits[i],
            x=axis_dev_name,
            y=polarisation_names[i],
            yerr=polarisation_stddev_names[i],
            output_dir=Path(r"C:\temp"),  # change this
            postfix=f"_band{i}",
        )
        for i in range(len(config.wavelength_bounds))
    ]

    return spinecho_cb, [table_cb, hrfile_cb, *plots_cb, *lflogs_cb]


def echoscan_axis_ib(
    config: EchoScanConfig, model: FitMethod, param: str
) -> Generator[Msg, None, lmfit.Parameter]:
    """Technique for doing a general echo scan."""
    flipper_dev = isis_epics_signal_rw(datatype=float, read_pv=config.flipper, name="flipper")
    # Would change to a blockrw but no flipper block on LARMOR
    axis_dev = block_rw(float, config.axis, write_config=BlockWriteConfig(settle_time_s=0.5))

    intervals = [
        sc.array(dims=["tof"], values=bound, unit=sc.units.angstrom, dtype="float64")
        for bound in config.wavelength_bounds
    ]

    total_flight_path_length = sc.scalar(value=config.flight_path_length_m, unit=sc.units.m)

    dae = polarising_dae(
        det_pixels=[_get_detector_i(config.detector)],
        frames=config.frames,
        flipper=flipper_dev,
        flipper_states=config.flipper_states,
        intervals=intervals,
        total_flight_path_length=total_flight_path_length,
        monitor=config.monitor,
    )

    yield from call_qt_aware(plt.close, "all")

    _, axes = yield from call_qt_aware(plt.subplots, len(config.wavelength_bounds))

    polarisation_names = dae.reducer.polarisation_names
    polarisation_stddev_names = dae.reducer.polarisation_stddev_names

    spinecho_cb, callbacks = _callbacks_init(
        config, model, polarisation_names, polarisation_stddev_names, axis_dev.name, axes
    )

    @subs_decorator([spinecho_cb, *callbacks])
    def _inner() -> Generator[Msg, None, None]:
        yield from ensure_connected(flipper_dev, dae, axis_dev)
        yield from scan([dae], axis_dev, config.start, config.stop, num=config.num_points)

    # waiting for daniel's implementation to be able to do this
    # as can't do a context manager
    # Here we want to make a backup of dae and tcb settings
    # then set new dae/tcb settings from config

    # dae_settings_backup = yield from bps.wait_for([self.dae.dae_settings.locate])
    # self.dae_settings_backup_sp = dae_settings_backup["setpoint"]

    # tcb_settings_backup = yield from bps.wait_for([self.dae.tcb_settings.locate])
    # self.tcb_settings_backup_sp = tcb_settings_backup["setpoint"]

    yield from _inner()
    # here we want to restore dae/tcb settings

    # Returns the fit parameter for the last livefit in the chain
    return spinecho_cb.live_fits[-1].result.params[param]


def auto_tune_ib(
    scan_config: EchoScanConfig, tune_config: AutoTuneConfig | None = None
) -> Generator[Msg, None, lmfit.Parameter]:
    """Perform a more specialised version of the echoscan_axis_ib function."""
    if tune_config is None:
        tune_config = AutoTuneConfig()

    if tune_config.model is None:
        tune_config.model = DampedOsc.fit()

    if scan_config.dae_settings is None:
        if scan_config.detector == "alanis":
            scan_config.dae_settings = DaeSettingsData(
                detector_filepath=r"C:\Instrument\Settings\config\NDXLARMOR\configurations\tables\Alanis_Detector.dat",
                spectra_filepath=r"C:\Instrument\Settings\config\NDXLARMOR\configurations\tables\spectra_scanning_Alanis.dat",
                wiring_filepath=r"C:\Instrument\Settings\config\NDXLARMOR\configurations\tables\Alanis_Wiring_dae3.dat",
            )
        elif scan_config.detector == "scruffy":
            scan_config.dae_settings = DaeSettingsData(
                detector_filepath=r"C:\Instrument\Settings\config\NDXLARMOR\configurations\tables\scruffy_Detector.dat",
                spectra_filepath=r"C:\Instrument\Settings\config\NDXLARMOR\configurations\tables\spectra_scanning_scruffy.dat",
                wiring_filepath=r"C:\Instrument\Settings\config\NDXLARMOR\configurations\tables\scruffy_Wiring_dae3.dat",
            )

    if scan_config.tcb_settings is None:
        tr0 = TimeRegime({1: TimeRegimeRow(from_=5.0, to=100000.0, steps=100.0)})
        scan_config.tcb_settings = DaeTCBSettingsData(tcb_tables={1: tr0})

    optimal_param: Parameter = yield from echoscan_axis_ib(
        scan_config, tune_config.model, tune_config.param
    )

    # Add null check for stderr
    if optimal_param.stderr is None:
        raise ValueError(f"Fit did not produce uncertainty estimate for {tune_config.param}")

    if tune_config.confidence < optimal_param.stderr:
        raise ValueError(
            f"Error {tune_config.confidence} is less than uncertainty in "
            f"optimal param {optimal_param.stderr}"
        )

    bps.mv(scan_config.axis, optimal_param.value)

    return optimal_param

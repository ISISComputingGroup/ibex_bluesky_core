"""HIFI magnet scan."""

from collections.abc import Generator

import bluesky.plans as bp
import bluesky.preprocessors as bpp
import matplotlib
import matplotlib.pyplot as plt
from bluesky.callbacks import LiveFitPlot, LiveTable
from bluesky.utils import Msg
from ophyd_async.epics.signal import epics_signal_r
from ophyd_async.plan_stubs import ensure_connected

from ibex_bluesky_core.callbacks.file_logger import HumanReadableFileCallback
from ibex_bluesky_core.callbacks.fitting import FitMethod, LiveFit
from ibex_bluesky_core.callbacks.fitting.fitting_utils import Linear
from ibex_bluesky_core.callbacks.fitting.livefit_logger import LiveFitLogger
from ibex_bluesky_core.callbacks.plotting import LivePlot
from ibex_bluesky_core.devices import get_pv_prefix
from ibex_bluesky_core.devices.block import block_r
from ibex_bluesky_core.devices.muons.hifi_magnet import HIFIMagnetAxis

matplotlib.rcParams["figure.autolayout"] = True
matplotlib.rcParams["font.size"] = 8


def magnet_axis(axis: str) -> HIFIMagnetAxis:
    """Create a magnet axis device with the instrument's PV prefix."""
    prefix = get_pv_prefix()
    return HIFIMagnetAxis(prefix=prefix, axis=axis)


LINEAR = Linear().fit()


def magnet_scan(  # noqa: PLR0914
    axis: str,
    start: float,
    stop: float,
    count: int,
    *,
    model: FitMethod = LINEAR,
    rel: bool = False,
) -> Generator[Msg, None, None]:
    """Scan a magnet axis.

    Args:
        axis: the magnet axis
        start: the initial magnet sp
        stop: the final magnet sp
        count: the number of points to scan.
        model: the fitting method.
        rel: whether to perform a relative scan.

    """
    magnet = magnet_axis(axis)
    magnetometer_x1 = epics_signal_r(float, "IN:HIFI:G3HALLPR_01:0:FIELD", name="x1")
    magnetometer_x2 = epics_signal_r(float, "IN:HIFI:G3HALLPR_02:0:FIELD", name="x2")

    magnetometer_y1 = epics_signal_r(float, "IN:HIFI:G3HALLPR_01:1:FIELD", name="y1")
    magnetometer_y2 = epics_signal_r(float, "IN:HIFI:G3HALLPR_02:1:FIELD", name="y2")

    magnetometer_z1 = epics_signal_r(float, "IN:HIFI:G3HALLPR_01:2:FIELD", name="z1")
    magnetometer_z2 = epics_signal_r(float, "IN:HIFI:G3HALLPR_02:2:FIELD", name="z2")

    fluxgate_x = epics_signal_r(float, "IN:HIFI:ZFMAGFLD_01:MEASURED:X", name="fluxgate_x")
    fluxgate_y = epics_signal_r(float, "IN:HIFI:ZFMAGFLD_01:MEASURED:Y", name="fluxgate_y")
    fluxgate_z = epics_signal_r(float, "IN:HIFI:ZFMAGFLD_01:MEASURED:Z", name="fluxgate_z")

    psu_x = block_r(float, "Field_X")
    psu_y = block_r(float, "Field_Y")
    psu_z = block_r(float, "Field_Z")

    yield from ensure_connected(
        magnet,
        magnetometer_x1,
        magnetometer_x2,
        magnetometer_y1,
        magnetometer_y2,
        magnetometer_z1,
        magnetometer_z2,
        fluxgate_x,
        fluxgate_y,
        fluxgate_z,
        psu_x,
        psu_y,
        psu_z,
    )

    plt.close("all")
    plt.show()
    _, ax = plt.subplots()

    readbacks = [
        magnetometer_x1.name,
        magnetometer_x2.name,
        magnetometer_y1.name,
        magnetometer_y2.name,
        magnetometer_z1.name,
        magnetometer_z2.name,
        fluxgate_x.name,
        fluxgate_y.name,
        fluxgate_z.name,
        psu_x.name,
        psu_y.name,
        psu_z.name,
    ]

    fields = [magnet.name, *readbacks]

    plots = [
        LivePlot(
            y=r,  # type: ignore
            x=magnet.name,
            marker="x",
            linestyle="none",
            ax=ax,
        )
        for r in readbacks
    ]

    fits = [
        LiveFit(
            model,
            y=r,
            x=magnet.name,  # type: ignore
        )
        for r in readbacks
    ]

    fitplots = [LiveFitPlot(fit, ax=ax) for fit in fits]

    fitloggers = [LiveFitLogger(fit, r, magnet.name, postfix=r) for fit, r in zip(fits, readbacks)]

    @bpp.subs_decorator(
        [
            HumanReadableFileCallback(fields=fields),
            LiveTable(fields),
            *plots,
            *fits,
            *fitplots,
            *fitloggers,
        ]
    )
    def _inner() -> Generator[Msg, None, None]:
        if rel:
            plan = bp.rel_scan
        else:
            plan = bp.scan
        yield from plan(
            [
                magnetometer_x1,
                magnetometer_x2,
                magnetometer_y1,
                magnetometer_y2,
                magnetometer_z1,
                magnetometer_z2,
                fluxgate_x,
                fluxgate_y,
                fluxgate_z,
                psu_x,
                psu_y,
                psu_z,
            ],
            magnet,
            start,
            stop,
            num=count,
        )

    yield from _inner()

    for name, livefit in zip(readbacks, fits):
        print(f"--- {name} ---")
        if livefit.result is not None:
            print(livefit.result.fit_report())
        else:
            print("No LiveFit result, likely fit failed")


def three_axis_scan(start: int = -4, stop: int = 4, num: int = 9) -> Generator[Msg, None, None]:
    """Scan against three magnet axes.

    Args:
        start:
        stop:
        num:

    """
    yield from magnet_scan("X", start, stop, num, rel=True)
    yield from magnet_scan("Y", start, stop, num, rel=True)
    yield from magnet_scan("Z", start, stop, num, rel=True)


def three_axis_full_scan(num: int = 20) -> Generator[Msg, None, None]:
    yield from magnet_scan("X", -95.0, 95.0, num, rel=True)
    yield from magnet_scan("Y", -95.0, 95.0, num, rel=True)
    yield from magnet_scan("Z", -390.0, 390.0, num, rel=True)

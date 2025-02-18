"""e.g.
RE(magnet_scan("X", 0, 1, 2)).
"""

from pathlib import Path

import bluesky.plans as bp
import bluesky.preprocessors as bpp
import matplotlib
import matplotlib.pyplot as plt
from bluesky.callbacks import LiveFitPlot, LiveTable
from ophyd_async.epics.signal import epics_signal_r
from ophyd_async.plan_stubs import ensure_connected

from ibex_bluesky_core.callbacks.file_logger import HumanReadableFileCallback
from ibex_bluesky_core.callbacks.fitting import LiveFit
from ibex_bluesky_core.callbacks.fitting.fitting_utils import Fit, Linear
from ibex_bluesky_core.callbacks.fitting.livefit_logger import LiveFitLogger
from ibex_bluesky_core.callbacks.plotting import LivePlot
from ibex_bluesky_core.devices import get_pv_prefix
from ibex_bluesky_core.devices.block import block_r
from ibex_bluesky_core.devices.muons.hifi_magnet import HIFIMagnetAxis
from ibex_bluesky_core.run_engine import get_run_engine

matplotlib.rcParams["figure.autolayout"] = True
matplotlib.rcParams["font.size"] = 8

RE = get_run_engine()

READABLE_FILE_OUTPUT_DIR = Path("C:\\") / "instrument" / "var" / "logs" / "bluesky" / "output_files"


def magnet_axis(axis: str) -> HIFIMagnetAxis:
    prefix = get_pv_prefix()
    return HIFIMagnetAxis(prefix=prefix, axis=axis)


def magnet_scan(
    axis: str,
    start: float,
    stop: float,
    count: int,
    *,
    model: Fit = Linear(),
    rel: bool = False,
):
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
            model.fit(),
            y=r,
            x=magnet.name,  # type: ignore
        )
        for r in readbacks
    ]

    fitplots = [LiveFitPlot(fit, ax=ax) for fit in fits]

    fitloggers = [
        LiveFitLogger(fit, r, magnet.name, output_dir=READABLE_FILE_OUTPUT_DIR, postfix=r)
        for fit, r in zip(fits, readbacks)
    ]

    @bpp.subs_decorator(
        [
            HumanReadableFileCallback(output_dir=READABLE_FILE_OUTPUT_DIR, fields=fields),
            LiveTable(fields),
            *plots,
            *fits,
            *fitplots,
            *fitloggers,
        ]
    )
    def _inner():
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


def three_axis_scan(start=-4, stop=4, num=9):
    yield from magnet_scan("X", start, stop, num, rel=True)
    yield from magnet_scan("Y", start, stop, num, rel=True)
    yield from magnet_scan("Z", start, stop, num, rel=True)


def three_axis_full_scan(num=20):
    yield from magnet_scan("X", -95.0, 95.0, num, rel=True)
    yield from magnet_scan("Y", -95.0, 95.0, num, rel=True)
    yield from magnet_scan("Z", -390.0, 390.0, num, rel=True)

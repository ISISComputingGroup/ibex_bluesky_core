"""Demonstration plan showing basic bluesky functionality."""

import os
from collections.abc import Generator

import matplotlib
import matplotlib.pyplot as plt
import numpy as np
from bluesky.utils import Msg

from ibex_bluesky_core.devices import get_pv_prefix
from ibex_bluesky_core.devices.block import block_rw
from ibex_bluesky_core.devices.simpledae import SimpleDae
from ibex_bluesky_core.devices.simpledae.controllers import PeriodPerPointController
from ibex_bluesky_core.devices.simpledae.reducers import (
    PeriodSpecIntegralsReducer,
)
from ibex_bluesky_core.devices.simpledae.waiters import PeriodGoodFramesWaiter
from ibex_bluesky_core.plans.reflectometry.det_map_align import (
    DetMapAlignResult,
    mapping_alignment_plan,
)
from ibex_bluesky_core.run_engine import get_run_engine

matplotlib.rcParams["figure.autolayout"] = True
matplotlib.rcParams["font.size"] = 8


def map_align() -> Generator[Msg, None, DetMapAlignResult]:
    """Plan demonstrating reflectometry detector-mapping alignment."""
    block = block_rw(float, "NEW_BLOCK")

    controller = PeriodPerPointController(save_run=True)
    waiter = PeriodGoodFramesWaiter(50)
    reducer = PeriodSpecIntegralsReducer(
        monitors=np.array([1], dtype=np.int64),
        detectors=np.arange(2, 129),
    )

    prefix = get_pv_prefix()
    dae = SimpleDae(
        prefix=prefix,
        controller=controller,
        waiter=waiter,
        reducer=reducer,
    )

    result = yield from mapping_alignment_plan(
        dae,
        block,
        5,
        15,
        num=51,
        angle_map=np.linspace(-5, 5, num=127, dtype=np.float64),
    )

    print("HEIGHT FIT:")
    if height_fit := result["height_fit"]:
        print(height_fit.fit_report(show_correl=False))
    print("\n\n")
    print("ANGLE FIT:")
    if angle_fit := result["angle_fit"]:
        print(angle_fit.fit_report(show_correl=False))
    print("\n\n")

    return result


if __name__ == "__main__" and not os.environ.get("FROM_IBEX") == "True":
    matplotlib.use("qtagg")
    plt.ion()
    RE = get_run_engine()
    RE(map_align())
    input("Plan complete, press return to close plot and exit")

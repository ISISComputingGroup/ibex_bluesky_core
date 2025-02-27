"""Demonstration plan showing basic bluesky functionality."""

import os
from collections.abc import Generator

import matplotlib
import matplotlib.pyplot as plt
import numpy as np
from bluesky.utils import Msg

from ibex_bluesky_core.devices.block import block_rw
from ibex_bluesky_core.plans.reflectometry.det_map_align import mapping_alignment_plan
from ibex_bluesky_core.run_engine import get_run_engine

matplotlib.rcParams["figure.autolayout"] = True
matplotlib.rcParams["font.size"] = 8


def map_align() -> Generator[Msg, None, None]:
    """Plan demonstrating reflectometry detector-mapping alignment."""
    block = block_rw(float, "NEW_BLOCK")
    return (
        yield from mapping_alignment_plan(
            block,
            5,
            15,
            num=51,
            frames=50,
            detectors=np.arange(2, 129),
            monitor=1,
            angle_map=np.linspace(-5, 5, num=127),
        )
    )


if __name__ == "__main__" and not os.environ.get("FROM_IBEX") == "True":
    matplotlib.use("qtagg")
    plt.ion()
    RE = get_run_engine()
    RE(map_align())
    input("Plan complete, press return to close plot and exit")

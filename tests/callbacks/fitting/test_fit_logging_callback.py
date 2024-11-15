# pyright: reportMissingParameterType=false
from pathlib import Path
from unittest.mock import MagicMock, mock_open, patch

import pytest
from bluesky.plans import scan
from ophyd.sim import InvariantSignal

from ibex_bluesky_core import run_engine
from ibex_bluesky_core.callbacks.fitting import FitMethod, LiveFit
from ibex_bluesky_core.callbacks.fitting.fitting_utils import Linear
from ibex_bluesky_core.callbacks.fitting.livefit_logger import LiveFitLogger


# Taken from bluesky bluesky\tests\test_callbacks.py
@pytest.fixture(scope="function")
def hw(tmp_path: str):
    from ophyd.sim import hw

    return hw(str(tmp_path))


def test_after_fitting_callback_writes_to_file_successfully_no_y_uncertainity(
    RE: run_engine.RunEngine, hw
):
    invariant = InvariantSignal(func=lambda: 0.5, name="invariant", labels={"detectors"})

    filepath = Path("C:\\") / "instrument" / "var" / "logs"
    postfix = "fit1"
    m = mock_open()

    lf = LiveFit(Linear.fit(), y="invariant", x="motor", update_every=50)
    lfl = LiveFitLogger(lf, y="invariant", x="motor", output_dir=filepath, postfix=postfix)

    with patch("ibex_bluesky_core.callbacks.fitting.livefit_logger.open", m):
        result = RE(scan([invariant], hw.motor, -1, 1, 3), [lf, lfl])  # type: ignore
        # "InvariantSignal" is incompatible with protocol "Readable"

    assert m.call_args_list[0].args == (filepath / f"{result.run_start_uids[0]}{postfix}.csv", "w")  # type: ignore

    handle = m()
    args = []

    # Check that it starts writing to the file in the expected way
    for i in handle.write.call_args_list:
        args.append(i.args[0])

    assert "x,y,modelled y\r\n" in args


def test_after_fitting_callback_writes_to_file_successfully_with_y_uncertainity(
    RE: run_engine.RunEngine, hw
):
    invariant = InvariantSignal(func=lambda: 0.5, name="invariant", labels={"detectors"})
    uncertainty = InvariantSignal(func=lambda: 1.0, name="uncertainty", labels={"detectors"})

    filepath = Path("C:\\") / "instrument" / "var" / "logs"
    postfix = "fit1"
    m = mock_open()

    lf = LiveFit(Linear.fit(), y="invariant", x="motor", update_every=50)
    lfl = LiveFitLogger(
        lf, y="invariant", x="motor", yerr="uncertainty", output_dir=filepath, postfix=postfix
    )

    with patch("ibex_bluesky_core.callbacks.fitting.livefit_logger.open", m):
        result = RE(scan([invariant, uncertainty], hw.motor, -1, 1, 3), [lf, lfl])  # type: ignore
        # "InvariantSignal" is incompatible with protocol "Readable"

    assert m.call_args_list[0].args == (filepath / f"{result.run_start_uids[0]}{postfix}.csv", "w")  # type: ignore

    handle = m()
    args = []

    # Check that it starts writing to the file in the expected way
    for i in handle.write.call_args_list:
        args.append(i.args[0])

    assert "x,y,y uncertainty,modelled y\r\n" in args


def test_file_not_written_if_no_fitting_result(RE: run_engine.RunEngine, hw):
    invariant = InvariantSignal(func=lambda: 0.5, name="invariant", labels={"detectors"})

    filepath = Path("C:\\") / "instrument" / "var" / "logs"
    postfix = "fit1"
    m = mock_open()

    model = Linear.model()
    model.fit = MagicMock()
    model.fit.return_value = None
    method = FitMethod(model=model, guess=Linear.guess())
    lf = LiveFit(method, y="invariant", x="motor")
    lfl = LiveFitLogger(lf, y="invariant", x="motor", output_dir=filepath, postfix=postfix)

    with patch("ibex_bluesky_core.callbacks.fitting.livefit_logger.open", m):
        RE(scan([invariant], hw.motor, -1, 1, 3), [lf, lfl])  # type: ignore
        # "InvariantSignal" is incompatible with protocol "Readable"

    assert not m.called

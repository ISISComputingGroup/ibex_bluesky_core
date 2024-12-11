# pyright: reportMissingParameterType=false
import os
from pathlib import Path
from unittest.mock import MagicMock, mock_open, patch

import pytest
from bluesky.plans import scan
from ophyd_async.core import soft_signal_rw

from ibex_bluesky_core import run_engine
from ibex_bluesky_core.callbacks.fitting import FitMethod, LiveFit
from ibex_bluesky_core.callbacks.fitting.fitting_utils import Linear
from ibex_bluesky_core.callbacks.fitting.livefit_logger import LiveFitLogger


def test_after_fitting_callback_writes_to_file_successfully_no_y_uncertainity(
    RE: run_engine.RunEngine,
):
    invariant = soft_signal_rw(float, 0.5, name="invariant")
    mot = soft_signal_rw(float, name="motor")

    filepath = Path("C:\\") / "instrument" / "var" / "logs"
    postfix = "fit1"
    m = mock_open()

    lf = LiveFit(Linear.fit(), y="invariant", x="motor", update_every=50)
    lfl = LiveFitLogger(lf, y="invariant", x="motor", output_dir=filepath, postfix=postfix)

    with patch("ibex_bluesky_core.callbacks.fitting.livefit_logger.open", m):
        result = RE(scan([invariant], mot, -1, 1, 3), [lf, lfl])

    assert m.call_args_list[0].args == (filepath / f"{result.run_start_uids[0]}{postfix}.csv", "w")  # type: ignore

    handle = m()
    rows = [i.args[0] for i in handle.write.call_args_list]

    # Check that it starts writing to the file in the expected way

    assert f"    Model({Linear.__name__}  [{Linear.equation}])" + os.linesep in rows
    assert "x,y,modelled y\r\n" in rows


def test_after_fitting_callback_writes_to_file_successfully_with_y_uncertainity(
    RE: run_engine.RunEngine,
):
    uncertainty = soft_signal_rw(float, 1.0, name="uncertainty")
    invariant = soft_signal_rw(float, 0.5, name="invariant")
    mot = soft_signal_rw(float, name="motor")

    filepath = Path("C:\\") / "instrument" / "var" / "logs"
    postfix = "fit1"
    m = mock_open()

    lf = LiveFit(Linear.fit(), y="invariant", x="motor", update_every=50)
    lfl = LiveFitLogger(
        lf, y="invariant", x="motor", output_dir=filepath, postfix=postfix, yerr="uncertainty"
    )

    with patch("ibex_bluesky_core.callbacks.fitting.livefit_logger.open", m):
        result = RE(scan([invariant, uncertainty], mot, -1, 1, 3), [lf, lfl])

    assert m.call_args_list[0].args == (filepath / f"{result.run_start_uids[0]}{postfix}.csv", "w")  # type: ignore

    handle = m()
    rows = [i.args[0] for i in handle.write.call_args_list]

    # Check that it starts writing to the file in the expected way

    assert f"    Model({Linear.__name__}  [{Linear.equation}])" + os.linesep in rows
    assert "x,y,y uncertainty,modelled y\r\n" in rows


def test_file_not_written_if_no_fitting_result(RE: run_engine.RunEngine):
    invariant = soft_signal_rw(float, 0.5, name="invariant")
    mot = soft_signal_rw(float, name="motor")

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
        RE(scan([invariant], mot, -1, 1, 3), [lf, lfl])

    assert not m.called


def test_error_thrown_if_no_x_data_in_event(RE: run_engine.RunEngine):
    filepath = Path("C:\\") / "instrument" / "var" / "logs"
    postfix = "fit1"

    lf = LiveFit(Linear.fit(), y="invariant", x="motor", update_every=50)
    lfl = LiveFitLogger(lf, y="invariant", x="motor", output_dir=filepath, postfix=postfix)

    with pytest.raises(IOError, match="motor is not in event document."):
        lfl.event(
            {
                "data": {  # type: ignore
                    "invariant": 2,
                }
            }
        )


def test_error_thrown_if_no_y_data_in_event(RE: run_engine.RunEngine):
    filepath = Path("C:\\") / "instrument" / "var" / "logs"
    postfix = "fit1"

    lf = LiveFit(Linear.fit(), y="invariant", x="motor", update_every=50)
    lfl = LiveFitLogger(lf, y="invariant", x="motor", output_dir=filepath, postfix=postfix)

    with pytest.raises(IOError, match="invariant is not in event document."):
        lfl.event(
            {
                "data": {  # type: ignore
                    "motor": 2,
                }
            }
        )


def test_error_thrown_if_no_y_err_data_in_event(RE: run_engine.RunEngine):
    filepath = Path("C:\\") / "instrument" / "var" / "logs"
    postfix = "fit1"

    lf = LiveFit(Linear.fit(), y="invariant", x="motor", update_every=50)
    lfl = LiveFitLogger(
        lf, y="invariant", x="motor", output_dir=filepath, postfix=postfix, yerr="yerr"
    )

    with pytest.raises(IOError, match="yerr is not in event document."):
        lfl.event(
            {
                "data": {  # type: ignore
                    "motor": 2,
                    "invariant": 2,
                }
            }
        )

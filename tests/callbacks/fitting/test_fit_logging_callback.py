from pathlib import Path
from unittest.mock import MagicMock, mock_open, patch
from bluesky.plans import scan
import packaging
import pytest

from ibex_bluesky_core.callbacks.fitting import FitMethod, LiveFit
from ibex_bluesky_core.callbacks.fitting.fitting_utils import Linear
from ibex_bluesky_core.callbacks.fitting.livefit_logger import LiveFitLogger

import ophyd
from ophyd.sim import InvariantSignal

# Taken from bluesky bluesky\tests\test_callbacks.py
@pytest.fixture(scope="function")
def hw(tmp_path):

    from ophyd.sim import hw

    # ophyd 1.4.0 added support for customizing the directory used by simulated
    # hardware that generates files
    if packaging.version.Version(ophyd.__version__) >= packaging.version.Version("1.4.0"):
        return hw(str(tmp_path))
    else:
        return hw()


def test_after_fitting_callback_writes_to_file_successfully_no_y_uncertainity(RE, hw):

    invariant = InvariantSignal(func=lambda: 0.5, name="invariant", labels={"detectors"})

    filepath = Path("C:\\") / "instrument" / "var" / "logs"
    postfix = "fit1"
    m = mock_open()

    lf = LiveFit(Linear.fit(), y="invariant", x="motor", update_every=50)
    lfl = LiveFitLogger(lf, y="invariant", x="motor", output_dir=filepath, postfix=postfix)

    with patch("ibex_bluesky_core.callbacks.fitting.livefit_logger.open", m):
        result = RE(scan([invariant], hw.motor, -1, 1, 3), [lf, lfl])

    assert m.call_args_list[0].args == (filepath / f"{result.run_start_uids[0]}{postfix}.csv", "w")

    handle = m()
    args = []

    # Check that it starts writing to the file in the expected way
    for i in handle.write.call_args_list:
        args.append(i.args[0])

    assert "x,y,modelled y\r\n" in args


def test_after_fitting_callback_writes_to_file_successfully_with_y_uncertainity(RE, hw):

    invariant = InvariantSignal(func=lambda: 0.5, name="invariant", labels={"detectors"})
    uncertainty = InvariantSignal(func=lambda: 1.0, name="uncertainty", labels={"detectors"})

    filepath = Path("C:\\") / "instrument" / "var" / "logs"
    postfix = "fit1"
    m = mock_open()

    lf = LiveFit(Linear.fit(), y="invariant", x="motor", update_every=50)
    lfl = LiveFitLogger(lf, y="invariant", x="motor", yerr="uncertainty", output_dir=filepath, postfix=postfix)

    with patch("ibex_bluesky_core.callbacks.fitting.livefit_logger.open", m):
        result = RE(scan([invariant, uncertainty], hw.motor, -1, 1, 3), [lf, lfl])

    assert m.call_args_list[0].args == (filepath / f"{result.run_start_uids[0]}{postfix}.csv", "w")

    handle = m()
    args = []

    # Check that it starts writing to the file in the expected way
    for i in handle.write.call_args_list:
        args.append(i.args[0])

    assert "x,y,y uncertainty,modelled y\r\n" in args


def test_file_not_written_if_no_fitting_result(RE, hw):

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

        RE(scan([invariant], hw.motor, -1, 1, 3), [lf, lfl])

    assert not m.called

from unittest.mock import MagicMock, patch

import numpy as np
import pytest
from _pytest.fixtures import FixtureRequest
from bluesky.callbacks import LiveFitPlot
from event_model import Event
from lmfit import Parameter
from matplotlib.axes import Axes

from ibex_bluesky_core.callbacks import ChainedLiveFit
from ibex_bluesky_core.fitting import FitMethod, Linear


@pytest.fixture
def method() -> FitMethod:
    return Linear().fit()


@pytest.fixture
def y_vars() -> list[str]:
    return ["y1", "y2"]


@pytest.fixture
def x_var() -> str:
    return "x"


@pytest.fixture
def yerr_vars() -> list[str]:
    return ["yerr1", "yerr2"]


@pytest.fixture
def mock_axes() -> list[Axes]:
    return [MagicMock(spec=Axes) for _ in range(2)]


@pytest.fixture
def mock_doc() -> dict[str, dict[str, int]]:
    return {
        "data": {
            "y": 1,
            "x": 1,
        }
    }


def test_chained_livefit_initialization(method: FitMethod, y_vars: list[str], x_var: str):
    """Test that ChainedLiveFit properly initializes with minimum required parameters"""
    clf = ChainedLiveFit(method=method, y=y_vars, x=x_var)
    assert len(clf._livefits) == len(y_vars)
    assert not clf._livefitplots


def test_chained_livefit_with_yerr(
    method: FitMethod, y_vars: list[str], x_var: str, yerr_vars: list[str]
):
    """Test that ChainedLiveFit properly handles yerr parameters"""
    clf = ChainedLiveFit(method=method, y=y_vars, x=x_var, yerr=yerr_vars)
    assert len(clf._livefits) == len(y_vars)

    for livefit, yerr in zip(clf._livefits, yerr_vars, strict=False):
        assert livefit.yerr == yerr


def test_chained_livefit_with_plotting(
    method: FitMethod, y_vars: list[str], x_var: str, mock_axes: list[Axes]
):
    """Test that ChainedLiveFit properly sets up plotting when axes are provided"""
    clf = ChainedLiveFit(method=method, y=y_vars, x=x_var, ax=mock_axes)

    assert len(clf._livefitplots) == len(mock_axes)
    assert all(isinstance(plot, LiveFitPlot) for plot in clf._livefitplots)


@pytest.mark.parametrize("doc_typ", ["start", "descriptor", "stop"])
def test_document_processing(
    method: FitMethod,
    y_vars: list[str],
    x_var: str,
    doc_typ: str,
    mock_doc: dict[str, dict[str, int]],
):
    """Test that calling start (etc..) on ChainedLiveFit correctly calls _process_doc"""
    # Does not apply for event as this should not be called unconditionally
    clf = ChainedLiveFit(method=method, y=y_vars, x=x_var)

    with patch.object(clf, "_process_doc") as mock_process:
        getattr(clf, doc_typ)(mock_doc)
        mock_process.assert_called_once_with(mock_doc, doc_typ)


def test_livefit_document_processing(
    method: FitMethod, y_vars: list[str], x_var: str, mock_doc: dict[str, dict[str, int]]
):
    """Test that documents are properly processed for LiveFit"""
    clf = ChainedLiveFit(method=method, y=y_vars, x=x_var)

    doc_typ = "event"

    for i in range(len(y_vars)):
        with patch.object(clf._livefits[i], doc_typ) as mock_process:
            clf._process_doc(mock_doc, doc_typ)  # pyright: ignore
            # Generic document type is not assignable
            mock_process.assert_called_once_with(mock_doc)


def test_livefitplot_document_processing(
    method: FitMethod,
    y_vars: list[str],
    x_var: str,
    mock_axes: list[Axes],
    mock_doc: dict[str, dict[str, int]],
):
    """Test that documents are properly processed for LiveFitPlots"""
    # Test implementation needed for document processing
    clf = ChainedLiveFit(method=method, y=y_vars, x=x_var, ax=mock_axes)

    doc_typ = "event"

    for i in range(len(y_vars)):
        with patch.object(clf._livefitplots[i], doc_typ) as mock_process:
            clf._process_doc(mock_doc, doc_typ)  # pyright: ignore
            # Generic document type is not assignable
            mock_process.assert_called_once_with(mock_doc)


@pytest.mark.parametrize("mock_axes", [None, "mock_axes"])
def test_first_livefit_uses_normal_guess_function(
    method: FitMethod,
    y_vars: list[str],
    x_var: str,
    mock_doc: dict[str, dict[str, int]],
    mock_axes: str | None,
    request: FixtureRequest,
):
    """Test that if using the first LiveFit then it will fit using its own guess function"""
    # Checks that event is called for LiveFit and LiveFitPlot in either case

    ax: list[Axes] | None = None if mock_axes is None else request.getfixturevalue(mock_axes)
    clf = ChainedLiveFit(method=method, y=y_vars, x=x_var, ax=ax)

    with patch.object(clf._livefits[0].method, "guess") as mock_guess:
        with patch.object(clf._livefits[0], "event") as mock_event:
            clf.event(mock_doc)  # pyright: ignore
            # Generic document type is not assignable
            mock_event.assert_called_once()
            assert mock_guess == clf._livefits[0].method.guess


@pytest.mark.parametrize("mock_axes", [None, "mock_axes"])
def test_livefit_param_passing_between_fits(
    method: FitMethod,
    y_vars: list[str],
    x_var: str,
    mock_doc: dict[str, dict[str, int]],
    mock_axes: str | None,
    request: FixtureRequest,
):
    """Test that parameters from first fit are passed correctly to second fit's guess function."""
    # Checks that this works for LiveFit and LiveFitPlot in either case
    ax: list[Axes] | None = None if mock_axes is None else request.getfixturevalue(mock_axes)
    clf = ChainedLiveFit(method=method, y=y_vars, x=x_var, ax=ax)
    callbacks = clf._livefits if mock_axes is None else clf._livefitplots

    # Mock first livefit's result with some parameters
    mock_params = {"param1": Parameter("param1", 1.0), "param2": Parameter("param2", 2.0)}
    mock_result = MagicMock()
    mock_result.params = mock_params

    # Set up the first livefit to return a mocked result
    clf._livefits[0].result = mock_result
    clf._livefits[0].can_fit = MagicMock(return_value=True)
    # Must mock out the first event for LiveFit or LiveFitPlot, otherwise ValueError
    callbacks[0].event = MagicMock(spec=Event)

    # Mock second livefit's guess function to check that it gets the parameters correctly
    def check_livefit_param(clf: ChainedLiveFit, mock_params: dict[str, Parameter]):
        assert clf._livefits[1].method.guess(np.array(0), np.array(0)) == mock_params

    with patch.object(
        callbacks[1], "event", side_effect=lambda _: check_livefit_param(clf, mock_params)
    ):
        clf.event(mock_doc)  # pyright: ignore
        # Generic document type is not assignable

    # Check that second livefit's guess function returns to original state
    assert clf._livefits[1].method.guess == method.guess


def test_livefit_has_no_result_assert(
    method: FitMethod, y_vars: list[str], x_var: str, mock_doc: dict[str, dict[str, int]]
):
    """Test that if LiveFit should be able to fit, but has no result, then throw an assertion"""
    clf = ChainedLiveFit(method=method, y=y_vars, x=x_var)
    clf._livefits[0].can_fit = MagicMock(return_value=True)

    with patch.object(clf._livefits[0], "event"):
        with pytest.raises(RuntimeError, match=r"LiveFit.result was None. Could not update fit."):
            clf.event(mock_doc)  # pyright: ignore
            # Generic document type is not assignable

import numpy as np
import pytest
from unittest.mock import MagicMock, patch
from bluesky.callbacks import LiveFitPlot
from lmfit import Parameter

from ibex_bluesky_core.callbacks import ChainedLiveFit
from ibex_bluesky_core.fitting import Linear
from matplotlib.axes import Axes
from event_model import RunStart, Event, RunStop, EventDescriptor

@pytest.fixture
def method():
    return Linear().fit()

@pytest.fixture
def y_vars():
    return ["y1", "y2"]

@pytest.fixture
def x_var():
    return "x"

@pytest.fixture
def yerr_vars():
    return ["yerr1", "yerr2"]

@pytest.fixture
def mock_axes():
    return [MagicMock(spec=Axes) for _ in range(2)]

@pytest.fixture
def mock_doc():
    return {
        "data": {
            "y": 1,
            "x": 1,
        }
    }

def test_chained_livefit_initialization(method, y_vars, x_var):
    """Test that ChainedLiveFit properly initializes with minimum required parameters"""
    clf = ChainedLiveFit(method=method, y=y_vars, x=x_var)
    assert len(clf._livefits) == len(y_vars)
    assert not clf._livefitplots

def test_chained_livefit_with_yerr(method, y_vars, x_var, yerr_vars):
    """Test that ChainedLiveFit properly handles yerr parameters"""
    clf = ChainedLiveFit(method=method, y=y_vars, x=x_var, yerr=yerr_vars)
    assert len(clf._livefits) == len(y_vars)

    for livefit, yerr in zip(clf._livefits, yerr_vars):
        assert livefit.yerr == yerr

def test_chained_livefit_with_plotting(method, y_vars, x_var, mock_axes):
    """Test that ChainedLiveFit properly sets up plotting when axes are provided"""
    clf = ChainedLiveFit(method=method, y=y_vars, x=x_var, ax=mock_axes)

    assert len(clf._livefitplots) == len(mock_axes)
    assert all(isinstance(plot, LiveFitPlot) for plot in clf._livefitplots)

@pytest.mark.parametrize("doc_typ", [
    "start",
    "descriptor",
    "stop"
])
def test_document_processing(method, y_vars, x_var, doc_typ, mock_doc):
    """Test that calling start (etc..) on ChainedLiveFit calls _process_doc with correct arguments"""
    # Does not apply for event as this should not be called unconditionally
    clf = ChainedLiveFit(method=method, y=y_vars, x=x_var)

    with patch.object(clf, '_process_doc') as mock_process:
        getattr(clf, doc_typ)(mock_doc)
        mock_process.assert_called_once_with(mock_doc, doc_typ)

def test_livefit_document_processing(method, y_vars, x_var, mock_doc):
    """Test that documents are properly processed for LiveFit"""
    clf = ChainedLiveFit(method=method, y=y_vars, x=x_var)

    doc_typ = "event"

    for i in range(len(y_vars)):
        with patch.object(clf._livefits[i], doc_typ) as mock_process:
            clf._process_doc(mock_doc, doc_typ)
            mock_process.assert_called_once_with(mock_doc)

def test_livefitplot_document_processing(method, y_vars, x_var, mock_axes, mock_doc):
    """Test that documents are properly processed for LiveFitPlots"""
    # Test implementation needed for document processing
    clf = ChainedLiveFit(method=method, y=y_vars, x=x_var, ax=mock_axes)

    doc_typ = "event"

    for i in range(len(y_vars)):
        with patch.object(clf._livefitplots[i], doc_typ) as mock_process:
            clf._process_doc(mock_doc, doc_typ)
            mock_process.assert_called_once_with(mock_doc)

@pytest.mark.parametrize("ax", [
    None,
    "mock_axes"
])
def test_first_livefit_uses_normal_guess_function(method, y_vars, x_var, mock_doc, ax, request):
    """Test that if using the first LiveFit then it will fit using its own guess function"""
    # Checks that event is called for LiveFit and LiveFitPlot in either case

    ax = None if ax is None else request.getfixturevalue(ax)
    clf = ChainedLiveFit(method=method, y=y_vars, x=x_var, ax=ax)

    with patch.object(clf._livefits[0].method, "guess") as mock_guess:
        with patch.object(clf._livefits[0], "event") as mock_event:
            clf.event(mock_doc)
            mock_event.assert_called_once()
            assert mock_guess == clf._livefits[0].method.guess

@pytest.mark.parametrize("ax", [
    None,
    "mock_axes"
])
def test_livefit_param_passing_between_fits(method, y_vars, x_var, mock_doc, ax, request):
    """Test that parameters from first fit are passed correctly to second fit's guess function."""
    # Checks that this works for LiveFit and LiveFitPlot in either case
    ax = None if ax is None else request.getfixturevalue(ax)
    clf = ChainedLiveFit(method=method, y=y_vars, x=x_var, ax=ax)
    callbacks = clf._livefits if ax is None else clf._livefitplots

    # Mock first livefit's result with some parameters
    mock_params = {
        'param1': Parameter('param1', 1.0),
        'param2': Parameter('param2', 2.0)
    }
    mock_result = MagicMock()
    mock_result.params = mock_params

    # Set up the first livefit to return a mocked result
    clf._livefits[0].result = mock_result
    clf._livefits[0].can_fit = MagicMock(return_value=True)
    # Must mock out the first event for LiveFit or LiveFitPlot, otherwise ValueError
    callbacks[0].event = MagicMock(spec=Event)

    # Mock second livefit's guess function to check that it gets the parameters correctly
    def check_livefit_param(clf, mock_params):
       assert clf._livefits[1].method.guess(0,0) == mock_params

    with patch.object(callbacks[1], "event", side_effect=lambda _: check_livefit_param(clf, mock_params)):
        clf.event(mock_doc)

    # Check that second livefit's guess function returns to original state
    assert clf._livefits[1].method.guess == method.guess

def test_livefit_has_no_result_assert(method, y_vars, x_var, mock_doc):
    """Test that if LiveFit should be able to fit, but does not have a result, then throw an assertion"""
    clf = ChainedLiveFit(method=method, y=y_vars, x=x_var)
    clf._livefits[0].can_fit = MagicMock(return_value=True)

    with patch.object(clf._livefits[0], "event"):
        with pytest.raises(RuntimeError, match='LiveFit.result was None. Could not update fit.'):
            clf.event(mock_doc)

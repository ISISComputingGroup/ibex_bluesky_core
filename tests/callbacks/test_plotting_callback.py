from typing import Any
from unittest.mock import MagicMock, patch

from ibex_bluesky_core.callbacks.plotting import LivePlot


def test_ibex_plot_callback_calls_show_on_start():
    # Testing matplotlib is a bit horrible.
    # The best we can do realistically is check that any arguments get passed through to
    # the underlying functions properly.

    lp = LivePlot(y=MagicMock(), x=MagicMock())

    with (
        patch("ibex_bluesky_core.callbacks.plotting.plt.show") as mock_plt_show,
        patch("ibex_bluesky_core.callbacks.plotting._DefaultLivePlot.start") as mock_start,
        patch("ibex_bluesky_core.callbacks.plotting._DefaultLivePlot.event") as mock_event,
        patch("ibex_bluesky_core.callbacks.plotting.matplotlib.get_backend") as mock_get_backend,
    ):
        mock_get_backend.return_value = "simulated_genie_python_matplotlib_backed"
        sentinel: Any = object()
        lp.start(sentinel)
        mock_start.assert_called_once_with(sentinel)
        mock_plt_show.assert_called_once()

        lp.event(sentinel)
        mock_event.assert_called_once_with(sentinel)
        assert mock_plt_show.call_count == 2


def test_show_plot_only_shows_if_backend_is_genie():
    lp = LivePlot(y=MagicMock(), x=MagicMock())

    with (
        patch("ibex_bluesky_core.callbacks.plotting.plt.show") as mock_plt_show,
        patch("ibex_bluesky_core.callbacks.plotting.matplotlib.get_backend") as mock_get_backend,
    ):
        mock_get_backend.return_value = "qtagg"
        lp._show_plot()
        mock_plt_show.assert_not_called()

        mock_get_backend.return_value = "simulated_genie_python_backend"
        lp._show_plot()
        mock_plt_show.assert_called_once()

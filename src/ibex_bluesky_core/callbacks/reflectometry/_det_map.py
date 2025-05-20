"""Reflectometry-specific callbacks for DAE mapping.

These callbacks form part of a joint height/angle scanning workflow on
reflectometers, where a single scan is interpreted in two different ways simultaneously:

- Height scan: sums together intensity within each data point, in a way very similar to
  the existing MonitorNormalizer dae reducer.
- Angle scan: sums together intensity across different data points, and then emits new
  events corresponding to total per-pixel intensities at the end of the scan.

The above are implemented as LiveDispatchers, so that they can use the same underlying
scan data, mutate or generate events in the two different ways, and then those new events
used by all of our normal callbacks (e.g. file-writing, fitting, plotting and so on).

For these callbacks, the underlying data is provided by a reducer named
PeriodSpecIntegralsReducer, which simultaneously exposes the integrals of many DAE spectra
at once.

"""

import logging
import math
import threading
import time
from typing import Any

import numpy as np
import numpy.typing as npt
import scipp as sc
from bluesky.callbacks.mpl_plotting import QtAwareCallback
from bluesky.callbacks.stream import LiveDispatcher
from event_model import Event, EventDescriptor, RunStart, RunStop
from matplotlib.axes import Axes

from ibex_bluesky_core.callbacks import show_plot
from ibex_bluesky_core.devices.simpledae import VARIANCE_ADDITION

logger = logging.getLogger(__name__)

__all__ = ["DetMapAngleScanLiveDispatcher", "DetMapHeightScanLiveDispatcher", "LivePColorMesh"]


class DetMapHeightScanLiveDispatcher(LiveDispatcher):
    """LiveDispatcher for reflectometry height scans.

    This sums a 1-D array of detector integrals, and synchronously emits events,
    normalizing by the sum of a 1-D array of monitor integrals.

    In the typical case, the array of monitor integrals will be of size 1 (i.e. a single
    monitor spectrum used for normalization).
    """

    def __init__(self, *, mon_name: str, det_name: str, out_name: str) -> None:
        """Init."""
        super().__init__()
        self._mon_name = mon_name
        self._det_name = det_name
        self._out_name = out_name

    def event(self, doc: Event, **kwargs: dict[str, Any]) -> Event:
        """Process an event."""
        logger.debug("DetMapHeightScanLiveDispatcher processing event uid %s", doc.get("uid"))
        det_data = doc["data"][self._det_name]
        mon_data = doc["data"][self._mon_name]

        det = sc.Variable(dims=["spectrum"], values=det_data, variances=det_data, dtype="float64")
        mon = sc.Variable(dims=["spectrum"], values=mon_data, variances=mon_data, dtype="float64")

        det_sum = det.sum()
        mon_sum = mon.sum()

        # See doc\architectural_decisions\005-variance-addition.md
        # for justification of this addition to variances.
        det_sum.variance += VARIANCE_ADDITION

        if mon_sum.value == 0.0:
            raise ValueError(
                "No monitor counts. Check beamline setup & beam status. "
                "I/I_0 normalization not possible."
            )

        normalized = det_sum / mon_sum

        doc["data"][self._out_name] = normalized.value
        doc["data"][self._out_name + "_err"] = math.sqrt(normalized.variance)
        return super().event(doc)


class DetMapAngleScanLiveDispatcher(LiveDispatcher):
    """LiveDispatcher which accumulates an array of counts data, and emits data at the end.

    For an array with dimension N, N events will be emitted at the end, corresponding
    to all input arrays summed together.
    """

    def __init__(
        self, x_data: npt.NDArray[np.float64], x_name: str, y_in_name: str, y_out_name: str
    ) -> None:
        """Init."""
        super().__init__()
        self.x_data = x_data
        self.x_name = x_name

        self.y_data = np.zeros_like(x_data)
        self.y_in_name: str = y_in_name
        self.y_out_name: str = y_out_name

        self._descriptor_uid: str | None = None

    def descriptor(self, doc: EventDescriptor) -> None:
        """Process a descriptor."""
        self._descriptor_uid = doc["uid"]
        return super().descriptor(doc)

    def event(self, doc: Event, **kwargs: dict[str, Any]) -> Event:
        """Process an event."""
        logger.debug("DetMapAngleScanLiveDispatcher processing event uid %s", doc.get("uid"))

        data = doc["data"][self.y_in_name]
        if data.shape != self.x_data.shape:
            raise ValueError(
                f"Shape of data ({data.shape} does not match x_data.shape ({self.x_data.shape})"
            )

        self.y_data += data
        return doc

    def stop(self, doc: RunStop, _md: dict[str, Any] | None = None) -> None:
        """Process a stop event."""
        if self._descriptor_uid is None:
            # No data to emit... don't do anything.
            return super().stop(doc, _md)

        current_time = time.time()
        for x, y in zip(self.x_data, self.y_data, strict=True):
            logger.debug("DetMapAngleScanLiveDispatcher emitting event with x=%f, y=%f", x, y)
            event = {
                "data": {
                    self.x_name: x,
                    self.y_out_name: y,
                    self.y_out_name + "_err": np.sqrt(y + 0.5),
                },
                "timestamps": {
                    self.x_name: current_time,
                    self.y_out_name: current_time,
                    self.y_out_name + "_err": current_time,
                },
                "descriptor": self._descriptor_uid,
            }
            self.process_event(event)
        return super().stop(doc, _md)


class LivePColorMesh(QtAwareCallback):
    """Live PColorMesh-based Live Heatmap for reflectometry mapping-alignment."""

    def __init__(
        self,
        *,
        y: str,
        x: str,
        x_name: str,
        x_coord: npt.NDArray[np.float64],
        ax: Axes,
        **kwargs: Any,  # noqa: ANN401
    ) -> None:
        """Create a new heatmap."""
        super().__init__(use_teleporter=kwargs.pop("use_teleporter", None))
        self.__setup_lock = threading.Lock()
        self.__setup_event = threading.Event()
        self._data: npt.NDArray[np.float64] | None = None
        self._x: str = x
        self._y: str = y
        self._y_coords: list[float] = []
        self._x_name: str = x_name
        self._x_coords: npt.NDArray[np.float64] = x_coord

        self.ax: Axes = ax
        self.kwargs = kwargs

    def start(self, doc: RunStart) -> RunStart | None:
        """Start a new plot (clear any old data)."""
        # The doc is not used; we just use the signal that a new run began.
        self._data = None
        self._y_coords = []

        return super().start(doc)

    def event(self, doc: Event) -> Event:
        """Unpack data from the event and call self.update()."""
        new_x = doc["data"][self._x]
        new_y = doc["data"][self._y]

        if self._data is None:
            self._data = np.asarray(new_x).reshape((1, len(new_x)))
        else:
            self._data = np.vstack((self._data, np.asarray(new_x)))

        self._y_coords.append(new_y)

        self.update_plot()
        return super().event(doc)

    def update_plot(self) -> None:
        """Redraw the heatmap."""
        assert self._data is not None
        assert self.ax is not None

        self.ax.clear()
        self.ax.set_xlabel(self._x_name)
        self.ax.set_ylabel(self._y)
        self.ax.pcolormesh(
            self._x_coords,
            self._y_coords,
            self._data,
            vmin=float(np.min(self._data)),
            vmax=float(np.max(self._data)),
            **self.kwargs,
        )
        self.ax.figure.canvas.draw_idle()  # type: ignore
        show_plot()

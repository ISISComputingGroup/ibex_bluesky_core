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
import time
from typing import Any

import numpy as np
import numpy.typing as npt
import scipp as sc
from bluesky.callbacks.stream import LiveDispatcher
from event_model import Event, EventDescriptor, RunStop

from ibex_bluesky_core.devices.simpledae import VARIANCE_ADDITION

logger = logging.getLogger(__name__)

__all__ = ["DetMapAngleScanLiveDispatcher", "DetMapHeightScanLiveDispatcher"]


class DetMapHeightScanLiveDispatcher(LiveDispatcher):
    """LiveDispatcher for reflectometry height scans.

    This sums a 1-D array of detector integrals, and synchronously emits events,
    normalizing by the sum of a 1-D array of monitor integrals.

    In the typical case, the array of monitor integrals will be of size 1 (i.e. a single
    monitor spectrum used for normalization).
    """

    def __init__(
        self, *, mon_name: str, det_name: str, out_name: str, flood: sc.Variable | None = None
    ) -> None:
        """Init."""
        super().__init__()
        self._mon_name = mon_name
        self._det_name = det_name
        self._out_name = out_name
        self._flood = flood if flood is not None else sc.scalar(value=1, dtype="float64")

    def event(self, doc: Event, **kwargs: dict[str, Any]) -> Event:
        """Process an event."""
        logger.debug("DetMapHeightScanLiveDispatcher processing event uid %s", doc.get("uid"))
        det_data = doc["data"][self._det_name]
        mon_data = doc["data"][self._mon_name]

        det = sc.Variable(dims=["spectrum"], values=det_data, variances=det_data, dtype="float64")
        mon = sc.Variable(dims=["spectrum"], values=mon_data, variances=mon_data, dtype="float64")

        det /= self._flood

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
        self,
        x_data: npt.NDArray[np.float64],
        x_name: str,
        y_in_name: str,
        y_out_name: str,
        flood: sc.Variable | None = None,
    ) -> None:
        """Init."""
        super().__init__()
        self.x_data = x_data
        self.x_name = x_name

        self.y_data = sc.array(
            dims=["spectrum"],
            values=np.zeros_like(x_data),
            variances=np.zeros_like(x_data),
            dtype="float64",
        )
        self.y_in_name: str = y_in_name
        self.y_out_name: str = y_out_name

        self._descriptor_uid: str | None = None

        self._flood = flood if flood is not None else sc.scalar(value=1, dtype="float64")

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

        scaled_data = (
            sc.array(dims=["spectrum"], values=data, variances=data, dtype="float64") / self._flood
        )
        self.y_data += scaled_data
        return doc

    def stop(self, doc: RunStop, _md: dict[str, Any] | None = None) -> None:
        """Process a stop event."""
        if self._descriptor_uid is None:
            # No data to emit... don't do anything.
            return super().stop(doc, _md)

        current_time = time.time()
        for x, y in zip(self.x_data, self.y_data, strict=True):  # type: ignore
            logger.debug("DetMapAngleScanLiveDispatcher emitting event with x=%f, y=%f", x, y)
            event = {
                "data": {
                    self.x_name: x,
                    self.y_out_name: y.value,
                    self.y_out_name + "_err": np.sqrt(y.variance + 0.5),
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

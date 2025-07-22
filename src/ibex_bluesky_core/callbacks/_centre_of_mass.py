import logging

import numpy as np
from bluesky.callbacks import CollectThenCompute

from ibex_bluesky_core.utils import center_of_mass_of_area_under_curve

logger = logging.getLogger(__name__)

__all__ = ["CentreOfMass"]


class CentreOfMass(CollectThenCompute):
    """Compute centre of mass after a run finishes.

    Calculates the CoM of the 2D region bounded by min(y), min(x), max(x),
    and straight-line segments joining (x, y) data points with their nearest
    neighbours along the x axis.
    """

    def __init__(self, x: str, y: str) -> None:
        """Initialise the callback.

        Args:
            x: Name of independent variable in event data
            y: Name of dependent variable in event data

        """
        super().__init__()
        self.x: str = x
        self.y: str = y
        self._result: float | None = None

    @property
    def result(self) -> float | None:
        """The centre-of-mass calculated by this callback."""
        return self._result

    def compute(self) -> None:
        """Calculate statistics at the end of the run."""
        x_values = []
        y_values = []

        for event in self._events:
            if self.x not in event["data"]:
                raise ValueError(f"{self.x} is not in event document.")

            if self.y not in event["data"]:
                raise ValueError(f"{self.y} is not in event document.")

            x_values.append(event["data"][self.x])
            y_values.append(event["data"][self.y])

        if not x_values:
            return

        x_data = np.array(x_values, dtype=np.float64)
        y_data = np.array(y_values, dtype=np.float64)
        (self._result, _) = center_of_mass_of_area_under_curve(x_data, y_data)

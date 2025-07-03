"""For IBEX Bluesky scan fitting."""

import csv
import logging
import os
import warnings
from itertools import zip_longest
from pathlib import Path

import lmfit
import numpy as np
from bluesky.callbacks import CallbackBase, LiveFitPlot
from bluesky.callbacks import LiveFit as _DefaultLiveFit
from bluesky.callbacks.core import CollectThenCompute, make_class_safe
from event_model import Event, EventDescriptor, RunStart, RunStop
from lmfit import Parameter
from matplotlib.axes import Axes
from numpy import typing as npt

from ibex_bluesky_core.callbacks._utils import (
    DATA,
    UID,
    _get_rb_num,
    format_time,
    get_default_output_path,
    get_instrument,
)
from ibex_bluesky_core.fitting import FitMethod
from ibex_bluesky_core.utils import center_of_mass_of_area_under_curve

logger = logging.getLogger(__name__)

__all__ = ["CentreOfMass", "ChainedLiveFit", "LiveFit", "LiveFitLogger"]


@make_class_safe(logger=logger)  # pyright: ignore (pyright doesn't understand this decorator)
class LiveFit(_DefaultLiveFit):
    """LiveFit, customized for IBEX."""

    def __init__(
        self,
        method: FitMethod,
        y: str,
        x: str,
        *,
        update_every: int | None = 1,
        yerr: str | None = None,
    ) -> None:
        """Call Bluesky LiveFit with assumption that there is only one independant variable.

        Args:
            method (FitMethod): The FitMethod (Model & Guess) to use when fitting.
            y (str): The name of the dependant variable.
            x (str): The name of the independant variable.
            update_every (int, optional): How often, in points, to update the fit.
            yerr (str or None, optional): Name of field in the Event document
                that provides standard deviation for each Y value. None meaning
                do not use uncertainties in fit.

        """
        self.method = method
        self.yerr = yerr
        self.weight_data = []

        super().__init__(
            model=method.model,
            y=y,
            independent_vars={"x": x},
            update_every=update_every,  # type: ignore
        )

    def event(self, doc: Event) -> None:
        """When an event is received, update caches."""
        weight = None
        if self.yerr is not None:
            try:
                weight = 1 / doc["data"][self.yerr]
            except ZeroDivisionError:
                warnings.warn(
                    "standard deviation for y is 0, therefore applying weight of 0 on fit",
                    stacklevel=1,
                )
                weight = 0.0

        self.update_weight(weight)
        super().event(doc)

    def update_weight(self, weight: float | None = 0.0) -> None:
        """Update uncertainties cache."""
        if self.yerr is not None:
            self.weight_data.append(weight)

    def can_fit(self) -> bool:
        """Check if enough data points have been collected to fit."""
        n = len(self.model.param_names)
        return len(self.ydata) >= n

    def update_fit(self) -> None:
        """Use the guess function with the most recent x and y values after every update."""
        if not self.can_fit():
            warnings.warn(
                f"""LiveFitPlot cannot update fit until there are at least
                {len(self.model.param_names)} data points""",
                stacklevel=1,
            )
        else:
            logger.debug("updating guess for %s ", self.method)
            self.init_guess = self.method.guess(
                np.array(next(iter(self.independent_vars_data.values()))),
                np.array(self.ydata),
                # Calls the guess function on the set of data already collected in the run
            )

            logger.info("new guess for %s: %s", self.method, self.init_guess)

            kwargs = {}
            kwargs.update(self.independent_vars_data)
            kwargs.update(self.init_guess)
            self.result = self.model.fit(
                self.ydata, weights=None if self.yerr is None else self.weight_data, **kwargs
            )


class LiveFitLogger(CallbackBase):
    """Generates files as part of a scan that describe the fit(s) which have been performed."""

    def __init__(
        self,
        livefit: LiveFit,
        y: str,
        x: str,
        postfix: str,
        output_dir: str | os.PathLike[str] | None,
        yerr: str | None = None,
    ) -> None:
        """Initialise LiveFitLogger callback.

        Args:
            livefit (LiveFit): A reference to LiveFit callback to collect fit info from.
            y (str): The name of the signal pointing to y counts data.
            x (str): The name of the signal pointing to x counts data.
            output_dir (str): A path to where the fitting file should be stored.
            postfix (str): A small string that should be placed at the end of the
                filename to disambiguate multiple fits and avoid overwriting.
            yerr (str): The name of the signal pointing to y count uncertainties data.

        """
        super().__init__()

        self.livefit = livefit
        self.postfix = postfix
        self.output_dir = Path(output_dir or get_default_output_path())
        self.current_start_document: str | None = None

        self.x = x
        self.y = y
        self.yerr = yerr

        self.x_data = []
        self.y_data = []
        self.yerr_data = []

    def start(self, doc: RunStart) -> None:
        """Create the output directory if it doesn't already exist then setting the filename.

        Args:
            doc (RunStart): The start bluesky document.

        """
        title_format_datetime = format_time(doc)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.current_start_document = doc[UID]
        file = f"{get_instrument()}_{self.x}_{self.y}_{title_format_datetime}Z{self.postfix}.txt"

        rb_num = _get_rb_num(doc)

        self.filename = self.output_dir / f"{rb_num}" / file

    def event(self, doc: Event) -> Event:
        """Start collecting, y, x, and yerr data.

        Args:
            doc: (Event): An event document.

        """
        event_data = doc[DATA]

        if self.x not in event_data:
            raise OSError(f"{self.x} is not in event document.")

        if self.y not in event_data:
            raise OSError(f"{self.y} is not in event document.")

        self.x_data.append(event_data[self.x])
        self.y_data.append(event_data[self.y])

        if self.yerr is not None:
            if self.yerr not in event_data:
                raise OSError(f"{self.yerr} is not in event document.")
            self.yerr_data.append(event_data[self.yerr])

        return super().event(doc)

    def stop(self, doc: RunStop) -> None:
        """Write to the fitting file.

        Args:
            doc (RunStop): The stop bluesky document.

        """
        if self.livefit.result is None:
            logger.error("LiveFit.result was None. Could not write to file.")
            return

        # Evaluate the model function for each x point
        kwargs = {"x": np.array(self.x_data)}
        kwargs.update(self.livefit.result.values)
        self.y_fit_data = self.livefit.result.model.eval(**kwargs)

        self.stats = self.livefit.result.fit_report().split("\n")

        # make sure the parent directory exists, create it if not
        os.makedirs(self.filename.parent, exist_ok=True)

        # Writing to csv file
        with open(self.filename, "w", newline="", encoding="utf-8") as csvfile:
            # Writing the data
            self.csvwriter = csv.writer(csvfile)

            csvfile.writelines([row + os.linesep for row in self.stats])

            csvfile.write(os.linesep)  # Space out file
            csvfile.write(os.linesep)

            if self.yerr is None:
                self.write_fields_table()
            else:
                self.write_fields_table_uncertainty()

            logger.info("Fitting information successfully written to: %s", self.filename.resolve())

    def write_fields_table(self) -> None:
        """Write collected run info to the fitting file."""
        row = ["x", "y", "modelled y"]
        self.csvwriter.writerow(row)

        rows = zip(self.x_data, self.y_data, self.y_fit_data, strict=True)
        self.csvwriter.writerows(rows)

    def write_fields_table_uncertainty(self) -> None:
        """Write collected run info to the fitting file with uncertainties."""
        row = ["x", "y", "y uncertainty", "modelled y"]
        self.csvwriter.writerow(row)

        rows = zip(self.x_data, self.y_data, self.yerr_data, self.y_fit_data, strict=True)
        self.csvwriter.writerows(rows)


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
        return self._result

    def compute(self) -> None:
        """Calculate statistics at the end of the run."""
        x_values = []
        y_values = []

        for event in self._events:
            if self.x not in event["data"]:
                raise OSError(f"{self.x} is not in event document.")

            if self.y not in event["data"]:
                raise OSError(f"{self.y} is not in event document.")

            x_values.append(event["data"][self.x])
            y_values.append(event["data"][self.y])

        if not x_values:
            return

        x_data = np.array(x_values, dtype=np.float64)
        y_data = np.array(y_values, dtype=np.float64)
        (self._result, _) = center_of_mass_of_area_under_curve(x_data, y_data)


class ChainedLiveFit(CallbackBase):
    """Processes multiple LiveFits, each fit's results inform the next, with optional plotting.

    This callback handles a sequence of LiveFit instances where the parameters from each
    completed fit serve as the initial guess for the subsequent fit. Optional plotting
    is built in using LivePlotFits. Note that you should not subscribe to the LiveFit/LiveFitPlot
    callbacks directly, but rather subscribe just this callback.
    """

    def __init__(
        self,
        method: FitMethod,
        y: list[str],
        x: str,
        *,
        yerr: list[str] | None = None,
        ax: list[Axes] | None = None,
    ) -> None:
        """Initialise ChainedLiveFit with multiple LiveFits.

        Args:
            method: FitMethod instance for fitting
            y: List of y-axis variable names
            x: x-axis variable name
            yerr: Optional list of error values corresponding to y variables
            ax: A list of axes to plot fits on to. Creates LiveFitPlot instances.

        """
        super().__init__()

        if yerr and len(y) != len(yerr):
            raise ValueError("yerr must be the same length as y")

        if ax and len(y) != len(ax):
            raise ValueError("ax must be the same length as y")

        self._livefits = [
            LiveFit(method=method, y=y_name, x=x, yerr=yerr_name)
            for y_name, yerr_name in zip_longest(y, yerr or [])
        ]  # if yerrs then create a LiveFit with a yerr else create a LiveFit without a yerr

        self._livefitplots = [
            LiveFitPlot(livefit=livefit, ax=axis)
            for livefit, axis in zip(self._livefits, ax or [], strict=False)
        ]  # if ax then create a LiveFitPlot with ax else do not create any LiveFitPlots

    def _process_doc(
        self, doc: RunStart | Event | RunStop | EventDescriptor, method_name: str
    ) -> None:
        """Process a document for either LivePlots or LiveFits.

        Args:
            doc: document to process
            method_name: Name of the method to call ('start', 'descriptor', 'event', or 'stop')

        """
        callbacks = self._livefitplots or self._livefits
        for callback in callbacks:
            assert hasattr(callback, method_name)
            getattr(callback, method_name)(doc)

    def start(self, doc: RunStart) -> None:
        """Process start document for all callbacks.

        Args:
            doc: RunStart document

        """
        self._process_doc(doc, "start")

    def descriptor(self, doc: EventDescriptor) -> None:
        """Process descriptor document for all callbacks.

        Args:
            doc: EventDescriptor document.

        """
        self._process_doc(doc, "descriptor")

    def event(self, doc: Event) -> Event:
        """Process event document for all callbacks.

        Args:
            doc: Event document

        """
        init_guess = {}

        for livefit in self._livefits:
            rem_guess = livefit.method.guess
            try:
                if init_guess:
                    # Use previous fit results as initial guess for next fit
                    def guess_func(
                        a: npt.NDArray[np.float64], b: npt.NDArray[np.float64]
                    ) -> dict[str, lmfit.Parameter]:
                        nonlocal init_guess
                        return {
                            name: Parameter(name, value.value)
                            for name, value in init_guess.items()  # noqa: B023
                        }  # ruff doesn't understand nonlocal

                    # Using value.value means that parameter uncertainty
                    # is not carried over between fits
                    livefit.method.guess = guess_func

                if self._livefitplots:
                    self._livefitplots[self._livefits.index(livefit)].event(doc)
                else:
                    livefit.event(doc)

            finally:
                livefit.method.guess = rem_guess

                if livefit.can_fit():
                    if livefit.result is None:
                        raise RuntimeError("LiveFit.result was None. Could not update fit.")

                    init_guess = livefit.result.params

        return doc

    def stop(self, doc: RunStop) -> None:
        """Process stop document and update fitting parameters.

        Args:
            doc: RunStop document

        """
        self._process_doc(doc, "stop")

    @property
    def live_fits(self) -> list[LiveFit]:
        """Return a list of the livefits."""
        return self._livefits

    @property
    def live_fit_plots(self) -> list[LiveFitPlot]:
        """Return a list of the livefitplots."""
        return self._livefitplots

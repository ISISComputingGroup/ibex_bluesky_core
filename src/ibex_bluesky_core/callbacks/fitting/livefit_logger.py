"""Creates a readable .csv file of Bluesky fitting metrics."""

import csv
from pathlib import Path
from typing import Optional

import numpy as np
from bluesky.callbacks import CallbackBase
from event_model.documents.event import Event
from event_model.documents.run_start import RunStart
from event_model.documents.run_stop import RunStop

from ibex_bluesky_core.callbacks.fitting import LiveFit
from ibex_bluesky_core.logger import logger

UID = "uid"
DATA = "data"


class LiveFitLogger(CallbackBase):
    """Generates files as part of a scan that describe the fit(s) which have been performed."""

    def __init__(
        self,
        livefit: LiveFit,
        y: str,
        x: str,
        output_dir: Path,
        postfix: str | None = None,
        yerr: str | None = None,
    ) -> None:
        """Initialise LiveFitLogger callback.

        Args:
            livefit (LiveFit): A reference to LiveFit callback to collect fit info from.
            y (str): The name of the signal pointing to y counts data.
            x (str): The name of the signal pointing to x counts data.
            output_dir (str): A path to where the fitting file should be stored.
            postfix (str): A small string that should be placed at the end of the
                filename to prevent overwriting.
            yerr (str): The name of the signal pointing to y count uncertainties data.

        """
        super().__init__()
        self.livefit = livefit
        self.postfix = "" if postfix is None else postfix
        self.output_dir = output_dir
        self.current_start_document: Optional[str] = None

        self.x = x
        self.y = y
        self.yerr = yerr

        assert self.x != ""
        assert self.y != ""
        assert self.yerr != ""

        self.x_data = np.array([])
        self.y_data = np.array([])
        self.yerr_data = np.array([])

    def start(self, doc: RunStart) -> None:
        """Create the output directory if it doesn't already exist then setting the filename.

        Args:
            doc (RunStart): The start bluesky document.

        """
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.current_start_document = doc[UID]
        self.filename = self.output_dir / f"{self.current_start_document}{self.postfix}.csv"

    def event(self, doc: Event) -> Event:
        """Start collecting, y, x and yerr data.

        Args:
            doc: (Event): An event document.

        """
        event_data = doc[DATA]

        assert self.x in event_data
        assert self.y in event_data

        self.x_data = np.append(self.x_data, [event_data[self.x]])
        self.y_data = np.append(self.y_data, [event_data[self.y]])

        if self.yerr is not None:
            assert self.yerr in event_data
            np.append(self.yerr_data, [event_data[self.yerr]])

        return super().event(doc)

    def stop(self, doc: RunStop) -> None:
        """Write to the fitting file.

        Args:
            doc (RunStop): The stop bluesky document.

        """
        if self.livefit.result is None:
            logger.blueskylogger.error("LiveFit.result was None. Could not write to file.")
            return

        # Evaluate the model function at equally-spaced points.
        kwargs = {"x": self.x_data}
        kwargs.update(self.livefit.result.values)
        self.y_fit_data = self.livefit.result.model.eval(**kwargs)

        self.stats = str(self.livefit.result.fit_report()).split("\n")

        # Writing to csv file
        with open(self.filename, "w", newline="") as csvfile:
            # Writing the data
            self.csvwriter = csv.writer(csvfile)

            for row in self.stats:
                self.csvwriter.writerow([row])

            self.csvwriter.writerow([])
            self.csvwriter.writerow([])

            self.write_fields_table()

            csvfile.close()
            logger.blueskylogger.info(
                f"Fitting information successfully written to {self.filename}"
            )

    def write_fields_table(self) -> None:
        """Write collected run info to the fitting file."""
        row = ["x", "y", "modelled y"]
        self.csvwriter.writerow(row)

        for i in range(0, self.x_data.size):
            self.csvwriter.writerow([self.x_data[i], self.y_data[i], self.y_fit_data[i]])

    def write_fields_table_uncertainty(self) -> None:
        """Write collected run info to the fitting file with uncertainties."""
        row = ["x", "y", "y uncertainty", "modelled y"]
        self.csvwriter.writerow(row)

        for i in range(0, self.x_data.size):
            self.csvwriter.writerow(
                [self.x_data[i], self.y_data[i], self.yerr_data[i], self.y_fit_data[i]]
            )

"""Creates a readable text file, with comma separated values of Bluesky fitting metrics."""

import csv
import logging
import os
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

import numpy as np
from bluesky.callbacks import CallbackBase
from event_model.documents.event import Event
from event_model.documents.run_start import RunStart
from event_model.documents.run_stop import RunStop

from ibex_bluesky_core.callbacks._utils import (
    DATA,
    RB,
    TIME,
    UID,
    UNKNOWN_RB,
    get_default_output_path,
    get_instrument,
)
from ibex_bluesky_core.callbacks.fitting import LiveFit

logger = logging.getLogger(__name__)


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
        datetime_obj = datetime.fromtimestamp(doc[TIME])
        title_format_datetime = datetime_obj.astimezone(ZoneInfo("UTC")).strftime(
            "%Y-%m-%d_%H-%M-%S"
        )
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.current_start_document = doc[UID]
        file = f"{get_instrument()}_{self.x}_{self.y}_{title_format_datetime}Z{self.postfix}.txt"
        rb_num = doc.get(RB, UNKNOWN_RB)
        if rb_num == UNKNOWN_RB:
            logger.warning('No RB number found, will save to "%s"', UNKNOWN_RB)
        self.filename = self.output_dir / f"{rb_num}" / file

    def event(self, doc: Event) -> Event:
        """Start collecting, y, x and yerr data.

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

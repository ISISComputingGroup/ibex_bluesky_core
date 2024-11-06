import csv
from pathlib import Path
from typing import Optional
from bluesky.callbacks import CallbackBase
from event_model.documents.run_stop import RunStop
from event_model.documents.run_start import RunStart
from ibex_bluesky_core.logger import logger
import numpy as np

from ibex_bluesky_core.callbacks.fitting import LiveFit

UID = "uid"

class LiveFitLogger(CallbackBase):
    """Generates files as part of a scan that describe the fit(s) which have been performed."""
    
    def __init__(self, livefit: LiveFit, output_dir: Path, postfix: str | None = None) -> None:
        """Initialises LiveFitLogger callback.
        
        Args:
            livefit (LiveFit): A reference to LiveFit callback to collect fit info from.
            output_dir (str): A path to where the fitting file should be stored.
            postfix (str): A small string that should be placed at the end of the file name to prevent overwriting.
        """

        super().__init__()
        self.livefit = livefit
        self.postfix = postfix
        (self.__x_key,) = livefit.independent_vars.keys()
        self.output_dir = output_dir
        self.current_start_document: Optional[str] = None
    
    def start(self, doc: RunStart) -> None:
        """Create the output directory if it doesn't already exist then setting the filename.

        Args:
            doc (RunStart): The start bluesky document.
        """
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.current_start_document = doc[UID]
        self.filename = self.output_dir / f"{self.current_start_document}{self.postfix}.csv"

    def stop(self, doc: RunStop) -> None:
        """Writes to the fitting file.
        
        Args:
            doc (RunStop): The stop bluesky document.
        """
        self.x_data = np.array(next(iter(self.livefit.independent_vars_data.values())))
        self.y_data = np.array(self.livefit.ydata)

        self.xmin = np.min(self.x_data)
        self.xmax = np.max(self.x_data)
        self.num_points = self.y_data.size
        
        if self.livefit.result is None:
            logger.blueskylogger.error("LiveFit.result was None. Could not write to file.")
            return

        # Evaluate the model function at equally-spaced points.
        x_points = np.linspace(self.xmin, self.xmax, self.num_points)
        kwargs = {self.__x_key: x_points}
        kwargs.update(self.livefit.result.values)
        self.y_fit_data = self.livefit.result.model.eval(**kwargs)

        self.stats = str(self.livefit.result.fit_report()).split("\n")

        # Writing to csv file
        try:
            with open(self.filename, 'w', newline='') as csvfile:
                csvwriter = csv.writer(csvfile)
                csvwriter.writerow([self.__x_key, self.livefit.y, "Model"])

                # Writing the data
                for i in range(0, self.num_points):
                    csvwriter.writerow([self.x_data[i], self.y_data[i], self.y_fit_data[i]])

                csvwriter.writerow([])
                csvwriter.writerow([])

                for row in self.stats:
                    csvwriter.writerow([row])

                logger.blueskylogger.info(f"Fitting information successfully written to {self.filename}")

        except Exception as e:
            logger.blueskylogger.error(f"Could not write fitting information to {self.filename}\n{e}")
    
        # unit test
        # docs
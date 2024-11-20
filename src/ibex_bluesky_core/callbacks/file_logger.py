"""Creates a readable .txt file of Bluesky runengine dataset."""

import csv
import logging
from datetime import datetime
from pathlib import Path
from typing import Optional

from bluesky.callbacks import CallbackBase
from event_model.documents.event import Event
from event_model.documents.event_descriptor import EventDescriptor
from event_model.documents.run_start import RunStart
from event_model.documents.run_stop import RunStop
from zoneinfo import ZoneInfo

logger = logging.getLogger(__name__)

TIME = "time"
START_TIME = "start_time"
NAME = "name"
SEQ_NUM = "seq_num"
DATA_KEYS = "data_keys"
DATA = "data"
DESCRIPTOR = "descriptor"
UNITS = "units"
UID = "uid"
PRECISION = "precision"


class HumanReadableFileCallback(CallbackBase):
    """Outputs bluesky runs to human-readable output files in the specified directory path."""

    def __init__(self, output_dir: Path, fields: list[str]) -> None:
        """Output human-readable output files of bluesky runs.

        If fields are given, just output those, otherwise output all hinted signals.
        """
        super().__init__()
        self.fields: list[str] = fields
        self.output_dir: Path = output_dir
        self.current_start_document: Optional[str] = None
        self.descriptors: dict[str, EventDescriptor] = {}
        self.filename: Optional[Path] = None

    def start(self, doc: RunStart) -> None:
        """Start writing an output file.

        This involves creating the file if it doesn't already exist
        then putting the metadata ie. start time, uid in the header.
        """
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.current_start_document = doc[UID]
        self.filename = self.output_dir / f"{self.current_start_document}.txt"

        logger.info("starting new file %s", self.filename)

        exclude_list = [
            TIME,  # We format this later
        ]
        header_data = {k: v for k, v in doc.items() if k not in exclude_list}

        datetime_obj = datetime.fromtimestamp(doc[TIME])
        formatted_time = datetime_obj.astimezone(ZoneInfo("Europe/London")).strftime(
            "%Y-%m-%d %H:%M:%S"
        )
        header_data[START_TIME] = formatted_time

        with open(self.filename, "a", newline="") as outfile:
            for key, value in header_data.items():
                outfile.write(f"{key}: {value}\n")

        logger.debug("successfully wrote header in %s", self.filename)

    def descriptor(self, doc: EventDescriptor) -> None:
        """Add the descriptor data to descriptors."""
        logger.debug("event descriptor with name=%s", doc.get(NAME))
        if doc.get(NAME) != "primary":
            return

        logger.debug("saving event descriptor with name=%s, id=%s", doc.get(NAME), doc.get(UID))
        descriptor_id = doc[UID]
        self.descriptors[descriptor_id] = doc

    def event(self, doc: Event) -> Event:
        """Append an event's output to the file."""
        if not self.filename:
            logger.error("File has not been started yet - doing nothing")
            return doc

        logger.debug("Appending event document %s", doc.get(UID))

        formatted_event_data = {}
        descriptor_id = doc[DESCRIPTOR]
        event_data = doc[DATA]
        descriptor_data = self.descriptors[descriptor_id][DATA_KEYS]

        for field in self.fields:
            value = event_data[field]
            formatted_event_data[field] = (
                f"{value:.{descriptor_data[field].get(PRECISION)}f}"
                if descriptor_data[field].get(PRECISION) is not None and isinstance(value, float)
                else value
            )

        with open(self.filename, "a", newline="") as outfile:
            file_delimiter = ","
            if doc[SEQ_NUM] == 1:
                # If this is the first event, write out the units before writing event data.
                units_line = file_delimiter.join(
                    f"{field_name}{f'({descriptor_data[field_name].get(UNITS, None)})' if descriptor_data[field_name].get(UNITS, None) else ''}"  # noqa: E501
                    for field_name in self.fields
                )
                outfile.write(f"\n{units_line}\n")
            writer = csv.DictWriter(
                outfile,
                fieldnames=formatted_event_data,
                delimiter=file_delimiter,
                lineterminator="\n",
            )
            writer.writerows([formatted_event_data])
        return doc

    def stop(self, doc: RunStop) -> RunStop | None:
        """Clear descriptors."""
        logger.info("Stopping run, clearing descriptors, filename=%s", self.filename)
        self.descriptors.clear()
        return super().stop(doc)

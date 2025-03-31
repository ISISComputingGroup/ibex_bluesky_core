"""Creates a readable .txt file of Bluesky runengine dataset."""

import csv
import logging
import os
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

from bluesky.callbacks import CallbackBase
from event_model.documents.event import Event
from event_model.documents.event_descriptor import EventDescriptor
from event_model.documents.run_start import RunStart
from event_model.documents.run_stop import RunStop

from ibex_bluesky_core.callbacks import get_default_output_path
from ibex_bluesky_core.callbacks._utils import (
    DATA,
    DATA_KEYS,
    DESCRIPTOR,
    MOTORS,
    NAME,
    PRECISION,
    RB,
    SEQ_NUM,
    START_TIME,
    TIME,
    UID,
    UNITS,
    UNKNOWN_RB,
    get_instrument,
)

logger = logging.getLogger(__name__)


class HumanReadableFileCallback(CallbackBase):
    """Outputs bluesky runs to human-readable output files in the specified directory path."""

    def __init__(self, fields: list[str], *, output_dir: Path | None, postfix: str = "") -> None:
        """Output human-readable output files of bluesky runs.

        If fields are given, just output those, otherwise output all hinted signals.

        Args:
            fields: a list of field names to include in output files
            output_dir: filepath into which to write output files
            postfix: optional postfix to append to output file names

        """
        super().__init__()
        self.fields: list[str] = fields
        self.output_dir: Path = output_dir or get_default_output_path()
        self.current_start_document: str | None = None
        self.descriptors: dict[str, EventDescriptor] = {}
        self.filename: Path | None = None
        self.postfix: str = postfix

    def start(self, doc: RunStart) -> None:
        """Start writing an output file.

        This involves creating the file if it doesn't already exist
        then putting the metadata ie. start time, uid in the header.
        """
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.current_start_document = doc[UID]

        datetime_obj = datetime.fromtimestamp(doc[TIME])
        title_format_datetime = datetime_obj.astimezone(ZoneInfo("UTC")).strftime(
            "%Y-%m-%d_%H-%M-%S"
        )
        rb_num = doc.get(RB, UNKNOWN_RB)

        # motors is a tuple, we need to convert to a list to join the two below
        motors = list(doc.get(MOTORS, []))

        self.filename = (
            self.output_dir
            / f"{rb_num}"
            / f"{get_instrument()}{'_' + '_'.join(motors) if motors else ''}_"
            f"{title_format_datetime}Z{self.postfix}.txt"
        )
        if rb_num == UNKNOWN_RB:
            logger.warning('No RB number found, saving to "%s"', UNKNOWN_RB)
        assert self.filename is not None
        logger.info("starting new file %s", self.filename)

        exclude_list = [
            TIME,  # We format this later
        ]
        header_data = {k: v for k, v in doc.items() if k not in exclude_list}

        formatted_time = datetime_obj.astimezone(ZoneInfo("UTC")).strftime("%Y-%m-%d %H:%M:%S")
        header_data[START_TIME] = formatted_time

        # make sure the parent directory exists, create it if not
        os.makedirs(self.filename.parent, exist_ok=True)

        with open(self.filename, "a", newline="\n", encoding="utf-8") as outfile:
            outfile.writelines([f"{key}: {value}\n" for key, value in header_data.items()])

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

        with open(self.filename, "a", newline="", encoding="utf-8") as outfile:
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

"""Creates a readable .txt file of Bluesky runengine dataset."""

import csv
from datetime import datetime
from pathlib import Path
from typing import Optional

from bluesky.callbacks import CallbackBase
from event_model.documents.event import Event
from event_model.documents.event_descriptor import EventDescriptor
from event_model.documents.run_start import RunStart
from event_model.documents.run_stop import RunStop
from zoneinfo import ZoneInfo

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

        exclude_list = [
            TIME,
            "plan_name",
            "plan_type",
            "scan_id",
            "versions",
            "plan_pattern",
            "plan_pattern_module",
            "plan_pattern_args",
        ]
        header_data = {k: v for k, v in doc.items() if k not in exclude_list}

        datetime_obj = datetime.fromtimestamp(doc[TIME])
        formatted_time = datetime_obj.astimezone(ZoneInfo("Europe/London")).strftime(
            "%Y-%m-%d %H:%M:%S"
        )
        header_data[START_TIME] = formatted_time

        with open(self.filename, "a") as outfile:
            for key, value in header_data.items():
                outfile.write(f"{key}: {value}\n")

    def descriptor(self, doc: EventDescriptor) -> None:
        """Add the descriptor data to descriptors."""
        if NAME not in doc or not doc[NAME] or doc[NAME] != "primary":
            return

        descriptor_id = doc[UID]
        self.descriptors[descriptor_id] = doc

    def event(self, doc: Event) -> Event:
        """Append an event's output to the file."""
        if not self.filename:
            print("File has not been started yet - doing nothing")
            return doc
        formatted_event_data = {}
        descriptor_id = doc[DESCRIPTOR]
        event_data = doc[DATA]
        descriptor_data = self.descriptors[descriptor_id][DATA_KEYS]

        for field in self.fields:
            value = event_data[field]
            formatted_event_data[field] = (
                f"{value:.{descriptor_data[field].get(PRECISION)}f}"
                if descriptor_data[field].get(PRECISION, None) is not None
                and isinstance(value, float)
                else value
            )

        with open(self.filename, "a", newline="") as outfile:
            if doc[SEQ_NUM] == 1:
                # If this is the first event, write out the units before writing event data.
                units_line = "\t".join(
                    f"{field_name}{f'({descriptor_data[field_name].get(UNITS, None)})' if descriptor_data[field_name].get(UNITS, None) else ''}"  # noqa: E501
                    for field_name in self.fields
                )
                outfile.write(f"\n{units_line}\n")
            writer = csv.DictWriter(outfile, fieldnames=formatted_event_data, delimiter="\t")
            writer.writerows([formatted_event_data])
        return doc

    def stop(self, doc: RunStop) -> RunStop | None:
        """Clear descriptors."""
        self.descriptors.clear()
        return super().stop(doc)

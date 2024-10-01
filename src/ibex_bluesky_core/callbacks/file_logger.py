"""Creates a readable .txt file of Bluesky runengine dataset"""

import csv
from datetime import datetime
from collections import OrderedDict
from typing import Optional
from pathlib import Path
from bluesky.callbacks import CallbackBase
from event_model.documents.event import Event
from event_model.documents.event_descriptor import EventDescriptor
from event_model.documents.run_start import RunStart
from event_model.documents.run_stop import RunStop


class HumanReadableOutputFileLoggingCallback(CallbackBase):
    """Outputs bluesky runs to human-readable output files in the specified directory path."""

    def __init__(self, fields: list[str], output_dir: Path) -> None:
        """Initialise current_start_document and filename"""
        super().__init__()
        self.fields: list[str] = fields
        self.output_dir: Path = output_dir
        self.current_start_document: Optional[str] = None
        self.descriptors: dict[str, EventDescriptor] = {}
        self.filename: Optional[str] = None

    def start(self, doc: RunStart) -> None:
        """Start writing an output file. This involves creating the file if it doesn't already exist
        then putting the metadata ie. start time, uid in the header."""
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.current_start_document = doc["uid"]
        self.filename = self.output_dir / f"{self.current_start_document}.txt"

        assert self.filename is not None, "Could not create filename."
        assert self.current_start_document is not None, "Saw a non-start document before a start."

        exclude_list = ["time", "plan_name", "plan_type", "scan_id", "versions"]
        header_data = {k: v for k, v in doc.items() if k not in exclude_list}

        datetime_obj = datetime.fromtimestamp(doc["time"])
        formatted_time = datetime_obj.strftime("%Y-%m-%d %H:%M:%S")
        header_data["start_time"] = formatted_time

        with open(self.filename, "a") as outfile:
            for key, value in header_data.items():
                outfile.write(f"{key}: {value}\n")

    def descriptor(self, doc: EventDescriptor) -> None:
        if doc["name"] != "primary":
            return

        descriptor_id = doc["uid"]
        self.descriptors[descriptor_id] = doc

    def event(self, doc: Event) -> None:
        """Append an event's output to the file"""
        formatted_event_data = {}
        descriptor_id = doc["descriptor"]
        event_data = doc["data"]
        descriptor_data = self.descriptors[descriptor_id]["data_keys"]

        for data_key, data_value in event_data.items():
            if data_key in self.fields:
                formatted_event_data[data_key] = (
                    f"{data_value:.{descriptor_data[data_key]['precision']}f}"
                    if "precision" in descriptor_data[data_key] and isinstance(data_value, float)
                    else data_value
                )

        with open(self.filename, "a", newline="") as outfile:
            if doc["seq_num"] == 1:
                # If this is the first event, write out the units before writing event data
                units_dict = OrderedDict(
                    {
                        key: value.get("units", "n/a")
                        for key, value in descriptor_data.items()
                        if key in self.fields
                    }
                )
                units_line = "  ".join(f"{key} ({value})" for key, value in (units_dict.items()))
                outfile.write(f"\n{units_line}\n")
            writer = csv.DictWriter(outfile, fieldnames=formatted_event_data, delimiter="\t")
            writer.writerows([formatted_event_data])

    def stop(self, doc: RunStop) -> None:
        self.descriptors.clear()
        return super().stop(doc)

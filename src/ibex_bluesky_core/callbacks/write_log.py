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
from bluesky.callbacks.core import get_obj_fields

#save_path = Path("C:\\") / "instrument" / "var" / "logs" / "bluesky" / "output_files"

class OutputLoggingCallback(CallbackBase):
    """Description"""

    def __init__(self, fields: str, path: str) -> None:
        """Initialise current_start_document and filename"""
        super().__init__()
        self.fields: str = get_obj_fields(fields)
        self.save_path: str = path
        self.current_start_document: Optional[str] = None
        self.descriptors: dict[str, str]= {}
        self.filename: Optional[str] = None

    def start(self, doc: RunStart) -> None:
        def file_creation():
            self.save_path.mkdir(parents=True, exist_ok=True)
            self.current_start_document = doc["uid"]
            self.filename = f"{self.save_path}\{self.current_start_document}.txt"
        
            assert self.filename is not None, "Could not create filename."
            assert self.current_start_document is not None, "Saw a non-start document before a start."

        def start_data_str():
            datetime_obj = datetime.fromtimestamp(doc["time"])
            formatted_time = datetime_obj.strftime('%Y-%m-%d %H:%M:%S')
            doc.update({"time": formatted_time})

            start_data = ["scan_id", "time"]
            start_data_reordered = {key: doc[key] for key in start_data if key in doc}

            for key in doc: 
                if key not in start_data_reordered:
                    start_data_reordered[key] = doc[key]
            
            start_data_write(start_data_reordered)

        def start_data_write(start_data_reordered: str):
            with open(self.filename, "a") as outfile:
                for key, value in start_data_reordered.items():
                    outfile.write('%s: %s\n' % (key,value))

        file_creation()
        start_data_str()

    def descriptor(self, doc: EventDescriptor) -> None:
        def descriptor_data_str():
            if doc['name'] != 'primary':
                return
            
            descriptor_id = doc['uid']
            self.descriptors[descriptor_id] = doc
        
        descriptor_data_str()

    def event(self, doc: Event) -> None:
        def event_data_str():
            formatted_event_data = {}
            descriptor_id = doc["descriptor"]
            event_data = doc["data"]
            required_columns = self.fields
            precision = self.descriptors
            descriptor_data = precision[descriptor_id]['data_keys']
            
            precision_dict = {key: value.get('precision', 'n/a') for key, value in descriptor_data.items() if key in required_columns}
            units_dict = OrderedDict({key: value.get('units', 'n/a') for key, value in descriptor_data.items() if key in required_columns})
            units_line = '  '.join(f'{key} ({value})' for key, value in (units_dict.items()))

            for key in precision_dict.keys():
                if key in event_data and isinstance(event_data[key], float):
                    if isinstance(precision_dict[key], int):
                        formatted_value = f"{event_data[key]:.{precision_dict[key]}f}"
                        formatted_event_data[key] = formatted_value
                    else: 
                        formatted_event_data[key] = event_data[key]

            event_data_write(units_line, formatted_event_data)

        def event_data_write(units_line: str, formatted_event_data: str):
            with open(self.filename, "a", newline='') as outfile:
                if doc["seq_num"] == 1:
                    outfile.write(f"\n{units_line}\n")
                writer = csv.DictWriter(outfile, fieldnames=formatted_event_data, delimiter='\t')
                writer.writerows([formatted_event_data])

        event_data_str()
            
    def stop(self, doc: RunStop) -> None:
        self.descriptors.clear()
        return super().stop(doc)
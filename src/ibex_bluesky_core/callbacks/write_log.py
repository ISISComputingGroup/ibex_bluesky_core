"""Creates a readable .txt file of Bluesky runengine dataset"""

import csv
from datetime import datetime
from collections import OrderedDict
from pathlib import Path
from bluesky.callbacks import CallbackBase
from event_model.documents.event import Event
from event_model.documents.event_descriptor import EventDescriptor
from event_model.documents.run_start import RunStart
from event_model.documents.run_stop import RunStop

save_path = Path("C:\\") / "instrument" / "var" / "logs" / "bluesky" / "output_files"

class OutputLoggingCallback(CallbackBase):
    """Description"""

    def __init__(self) -> None:
        """Initialise current_start_document and filename"""
        super().__init__()        
        self.current_start_document = None
        self.descriptors = {}
        self.filename = None

    def start(self, doc: RunStart) -> None:
        save_path.mkdir(parents=True, exist_ok=True)

        self.current_start_document = doc["uid"] #or would the user prefer scan_id as the name of the log?
        self.filename = save_path / f"{self.current_start_document}.txt"
        
        assert self.filename is not None, "Could not create filename."
        assert self.current_start_document is not None, "Saw a non-start document before a start."

        datetime_obj = datetime.fromtimestamp(doc["time"])
        formatted_time = datetime_obj.strftime('%Y-%m-%d %H:%M:%S')
        doc.update({"time": formatted_time})

        start_data = ["scan_id", "time"]
        start_data_reordered = {key: doc[key] for key in start_data if key in doc}

        for key in doc: 
            if key not in start_data_reordered:
                start_data_reordered[key] = doc[key]
    
        with open(self.filename, "a") as outfile:
            for key, value in start_data_reordered.items():
                outfile.write('%s: %s\n' % (key,value))

    def descriptor(self, doc: EventDescriptor) -> None:
        if doc['name'] != 'primary':
            return
        
        descriptor_id = doc['uid']
        self.descriptors[descriptor_id] = doc

    def event(self, doc: Event) -> None:
        formatted_event_data = {}
        descriptor_id = doc["descriptor"]
        event_data = doc["data"]
        precision = self.descriptors
        descriptor_data = precision[descriptor_id]['data_keys']
        
        precision_dict = {key: value.get('precision', 'n/a') for key, value in descriptor_data.items()}
        units_dict = OrderedDict({key: value.get('units', 'n/a') for key, value in descriptor_data.items()})
        units_line = '  '.join(f'{key} ({value})' for key, value in (units_dict.items()))

        for key in precision_dict.keys():
            if key in event_data and isinstance(event_data[key], float):
                if isinstance(precision_dict[key], int):
                    formatted_value = f"{event_data[key]:.{precision_dict[key]}f}"
                    formatted_event_data[key] = formatted_value
                else: 
                    formatted_event_data[key] = event_data[key]

        with open(self.filename, "a", newline='') as outfile:
            if doc["seq_num"] == 1:
                outfile.write(f"\n{units_line}\n")
            writer = csv.DictWriter(outfile, fieldnames=formatted_event_data, delimiter='\t')
            writer.writerows([formatted_event_data])
        
    def stop(self, doc: RunStop) -> None:
        self.descriptors.clear()
        return super().stop(doc)
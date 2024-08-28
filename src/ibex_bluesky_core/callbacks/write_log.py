"""Creates a readable .txt file of Bluesky runengine dataset"""

from pathlib import Path
import csv
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
        self.current_start_document = None
        self.filename = None

    def start(self, doc: RunStart) -> None:
        save_path.mkdir(parents=True, exist_ok=True)

        self.current_start_document = doc["uid"] #or would the user prefer scan_id as the name of the log?
        self.filename = save_path / f"{self.current_start_document}.txt"
        
        assert self.filename is not None, "Could not create filename."
        assert self.current_start_document is not None, "Saw a non-start document before a start."
        
        start_data = ["scan_id", "time"]

        start_data_reordered = {key: doc[key] for key in start_data if key in doc}

        for key in doc: 
            if key not in start_data_reordered:
                start_data_reordered[key] = doc[key]
    
        with open(self.filename, "a") as outfile:
            for key, value in start_data_reordered.items():
                outfile.write('%s: %s\n' % (key,value))

    def descriptor(self, doc: EventDescriptor) -> None:
        return super().descriptor(doc)
    
    def event(self, doc: Event) -> Event:
        event_data = doc["data"]
        event_data_reordered = {"seq_num": doc["seq_num"], **event_data}
        event_data_list = [event_data_reordered]
        event_data_fieldnames= event_data_reordered.keys()

        with open(self.filename, "a", newline='') as outfile:
            writer = csv.DictWriter(outfile, fieldnames=event_data_fieldnames, delimiter='\t')
            if doc["seq_num"] == 1:
                writer.writeheader()
            writer.writerows(event_data_list)
    
    def stop(self, doc: RunStop) -> None:
        return super().stop(doc)
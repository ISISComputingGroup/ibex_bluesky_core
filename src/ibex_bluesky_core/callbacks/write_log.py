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

    def start(self, doc: RunStart) -> RunStart | None:
        save_path.mkdir(parents=True, exist_ok=True)

        self.current_start_document = doc["uid"] #or would the user prefer scan_id as the name of the log?
        self.filename = save_path / f"{self.current_start_document}.csv"
        
        assert self.filename is not None, "Could not create filename."
        assert self.current_start_document is not None, "Saw a non-start document before a start."
        
        start_field_names = ["scan_id", "start_time"]
        start_data = [{"scan_id": doc["scan_id"], "start_time": doc["time"]}]
        """with open(self.filename, "a") as outfile:
            for key, value in start_write.items():
                outfile.write('%s %s\n' % (key,value))"""

        #this part should be for the data below, from events
        with open(self.filename, "a") as outfile:
            writer = csv.DictWriter(outfile, fieldnames=start_field_names)
            writer.writeheader()
            writer.writerows(start_data)

        return super().start(doc)

    def descriptor(self, doc: EventDescriptor) -> EventDescriptor | None:
        return super().descriptor(doc)
    
    def event(self, doc: Event) -> Event:

        event_write = {"run_number: ": doc["seq_num"]}

        event_data_write = doc["data"]

        with open(self.filename, "a") as outfile:
            for key, value in event_write.items():
                outfile.write('%s %s\n' % (key,value))

            for key,value in event_data_write.items():
                outfile.write('%s %s\n' % (key,value))

        return super().event(doc)
    
    def stop(self, doc: RunStop) -> RunStop | None:
        return super().stop(doc)

    """if name == "event":
            event_write = {"run_number: ": document["seq_num"],} 
            event_data_write = document["data"]
            #output_dict.update(event_write)
            #output_dict.update(event_data_write)"""
    
        
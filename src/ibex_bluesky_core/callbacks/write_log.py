"""Creates a readable .txt file of Bluesky runengine dataset"""

from pathlib import Path

save_path = Path("C:\\") / "instrument" / "var" / "logs" / "bluesky" / "output_files"

class OutputLoggingCallback:
    """Description"""

    def __init__(self) -> None:
        """Initialise current_start_document and filename"""
        self.current_start_document = None
        self.filename = None
    
    def __call__(self, name: str, document: dict) -> None:
        """Description"""
        """
        Args:
            name: The type of Bluesky document (start, event, stop)
            document: The contents of the document as a dictionary

        """

        #output_dict = {}
        start_write = {}
        event_write = {}
        event_data_write = {}

        if name == "start":
            save_path.mkdir(parents=True, exist_ok=True)

            self.current_start_document = document["uid"] #or would the user prefer scan_id as the name of the log?
            self.filename = save_path / f"{self.current_start_document}.txt"
        
        assert self.filename is not None, "Could not create filename."
        assert self.current_start_document is not None, "Saw a non-start document before a start."

        if name == "start":
            start_write = {"scan_id: ": document["scan_id"],
                            "time: ": document["time"],}
                            #"rb_number: ": document["uid"]
            #output_dict.update(start_write)
        
        """if name == "descriptor":
            pass"""

        if name == "event":
            event_write = {"run_number: ": document["seq_num"],} 
            event_data_write = document["data"]
            #output_dict.update(event_write)
            #output_dict.update(event_data_write)

        """if name == "stop":
            pass"""
        
        with open(self.filename, "a") as outfile:
            for key, value in start_write.items():
                outfile.write('%s %s\n' % (key,value))

            for key, value in event_write.items():
                outfile.write('%s   \n%s    ' % (key,value))

            for key, value in event_data_write.items():
                outfile.write('%s   \n%s    ' % (key,value))
        